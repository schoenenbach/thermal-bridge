"""
Declarative Geometry Loader
Parses YAML scenario files to construct a SketchGeometry.
"""

import yaml
import os
import re
from typing import Dict, Any, List, Union
from geometry import SketchGeometry, MaterialID, RefinementZone
from config import (
    MAT_WALL, MAT_INSULATION, MAT_REVEAL_INSULATION, MAT_FRAME_EQ, MAT_GLASS_UG11,
    MAT_SPACER_SWISS_ULTIMATE, MAT_SPACER_STAINLESS, MAT_SPACER_ALUMINUM, MAT_STYRODUR,
    MAT_ALUMINUM, MAT_CAVITY_ISO, MAT_EPDM,
    TEMP_INT, TEMP_EXT, RSI_WALL, RSE, RSI_CORNER
)
import elements
from scenario_schema import validate_scenario

class DeclarativeGeometry(SketchGeometry):
    """
    Geometry defined by a YAML configuration file.
    Supports parametric definitions via variables and both 
    polygon-based (raw) and element-based (macro) construction.
    """
    
    def __init__(self, yaml_content: Union[str, Dict[str, Any]]):
        super().__init__()
        
        if isinstance(yaml_content, str):
            self.data = yaml.safe_load(yaml_content)
        else:
            self.data = yaml_content
            
        self.vars = self.data.get('variables', {})
        self._resolve_variables()
        self._validate_schema()
        
        # 1. Setup Canvas
        self._setup_canvas()
        
        # 2. Define Points
        self._define_points()
        
        # 3. Build Elements
        self._build_elements()
        
    def _resolve_variables(self):
        """Recursively replace ${var} in self.data."""
        # Simple string substitution for now. 
        # For numeric values, we might need eval or strict type casting.
        
        def replace_val(val):
            if isinstance(val, str):
                # Regex to find ${var}
                pattern = r"\$\{(\w+)\}"
                matches = re.finditer(pattern, val)
                
                new_val = val
                for match in matches:
                    var_name = match.group(1)
                    if var_name in self.vars:
                        # If the whole string is just the variable, replace with typed value
                        if match.group(0) == val:
                            return self.vars[var_name]
                        else:
                            new_val = new_val.replace(match.group(0), str(self.vars[var_name]))
                    else:
                        print(f"[WARNING] Variable '{var_name}' not found.")
                
                # Try converting to number if simple number string
                try:
                    if "." in new_val:
                        return float(new_val)
                    return int(new_val)
                except ValueError:
                    return new_val
                    
            elif isinstance(val, dict):
                return {k: replace_val(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [replace_val(v) for v in val]
            return val

        self.data = replace_val(self.data)
        
    def _validate_schema(self):
        """Validate scenario data against schema."""
        errors = validate_scenario(self.data)
        
        if errors:
            scenario_name = self.data.get('name', 'Unknown')
            print(f"[WARNING] Schema validation issues in '{scenario_name}':")
            for err in errors:
                print(f"  - {err}")
        
        # Legacy check for 'shapes' key (not used in current scenarios)
        if 'elements' not in self.data and 'shapes' not in self.data:
            print("[INFO] No 'elements' or 'shapes' found in YAML.")
            
    def _setup_canvas(self):
        cv = self.data.get('canvas', {})
        bounds = cv.get('bounds', [0, 100, 0, 100])
        grid = cv.get('grid', 10.0)
        
        self.set_canvas(
            x_min=bounds[0], x_max=bounds[1],
            y_min=bounds[2], y_max=bounds[3],
            grid_mm=grid
        )
        
    def _define_points(self):
        points = self.data.get('points', {})
        for name, coords in points.items():
            if len(coords) == 2:
                self.add_point(name, float(coords[0]), float(coords[1]))
            else:
                print(f"[ERROR] Point {name} has invalid coords: {coords}")

    def _resolve_material(self, mat_val):
        """Resolve material ID/Lambda from string or int."""
        # Map of string names to (ID, Lambda)
        MAT_MAP = {
            "WALL": (MaterialID.WALL, MAT_WALL),
            "INSULATION": (MaterialID.INSULATION, MAT_INSULATION),
            "REVEAL_INS": (MaterialID.REVEAL_INS, MAT_REVEAL_INSULATION),
            "STYRODUR": (MaterialID.STYRODUR, MAT_STYRODUR),
            "CONCRETE": (MaterialID.CONCRETE, 1.15),
            "WOOD": (MaterialID.WOOD, 0.12),
            "FRAME": (MaterialID.FRAME, MAT_FRAME_EQ),
            "GLASS": (MaterialID.GLASS, MAT_GLASS_UG11),
            "ALUMINUM": (MaterialID.ALUMINUM, MAT_ALUMINUM),
            "AIR_INT": (MaterialID.AIR_INT, 0.025),
            "AIR_EXT": (MaterialID.AIR_EXT, 0.025),
            "CAVITY": (MaterialID.CAVITY, MAT_CAVITY_ISO)
        }
        
        if isinstance(mat_val, str):
            mat_upper = mat_val.upper()
            if mat_upper in MAT_MAP:
                return MAT_MAP[mat_upper]
            else:
                print(f"[WARNING] Unknown material name '{mat_val}', defaulting to WALL")
                return (MaterialID.WALL, MAT_WALL)
        
        # If explicit ID provided (rare in YAML)
        return (int(mat_val), 0.025)

    def _build_elements(self):
        # Support both 'elements' (macros) and 'shapes' (polygons) keys mixed?
        # Let's assume a unified list under 'elements'
        el_list = self.data.get('elements', [])
        
        for el in el_list:
            el_type = el.get('type', 'rect')
            
            # --- Common Params ---
            mat_raw = el.get('material', 'WALL')
            mat_id, mat_lambda = self._resolve_material(mat_raw)
            # Override lambda if explicit
            if 'lambda' in el:
                mat_lambda = float(el['lambda'])
            
            name = el.get('name', f"{el_type}_{el_list.index(el)}")
            p = el.get('params', {})
            # Merge top-level keys into params for convenience if not in params dict
            for k,v in el.items():
                if k not in ['type', 'params', 'material', 'lambda', 'name', 'points']:
                    p[k] = v

            # --- Type Handlers ---
            
            if el_type == 'polygon':
                # Reference existing points by name
                pt_names = el.get('points', [])
                if pt_names:
                    self.add_shape(pt_names, mat_id, mat_lambda, name)
                else:
                    print(f"[ERROR] Polygon {name} has no points defined.")
            
            elif el_type == 'rect':
                x = float(p.get('x', 0))
                y = float(p.get('y', 0))
                w = float(p.get('width', 0))
                h = float(p.get('height', 0))
                elements.add_rect(self, name, x, y, w, h, mat_id, mat_lambda)
                
            elif el_type == 'wall':
                elements.add_wall(self, p.get('x'), p.get('y'), p.get('width'), p.get('height'), mat_lambda)
                
            elif el_type == 'insulation':
                elements.add_insulation(self, p.get('x'), p.get('y'), p.get('width'), p.get('height'), mat_lambda, name, mat_id)
                
            elif el_type == 'insulation_tapered':
                elements.add_insulation_tapered(
                    self, 
                    x_base=p.get('x_base'), 
                    y_bottom=p.get('y_bottom'), 
                    y_top=p.get('y_top'),
                    thick_main=p.get('thick_main'),
                    thick_taper=p.get('thick_taper'),
                    taper_start_y=p.get('taper_start_y'),
                    lambda_val=mat_lambda,
                    name=name,
                    material_id=mat_id
                )
             
            # ... Add other macros as needed (rebate, window definition, etc.)
            
            elif el_type == 'window_detail':
                # Complex macro
                elements.add_window_detail(
                    self,
                    x_frame_start=p.get('x_frame_start'),
                    y_frame_start=p.get('y_frame_start'),
                    frame_depth=p.get('frame_depth'),
                    frame_width=p.get('frame_width'),
                    sash_depth=p.get('sash_depth'),
                    sash_width=p.get('sash_width'),
                    sash_overlap=p.get('sash_overlap'),
                    sash_recess=p.get('sash_recess'),
                    glass_thickness=p.get('glass_thickness'),
                    y_top=p.get('y_top'),
                    mat_frame_lambda=MAT_FRAME_EQ,
                    mat_glass_lambda=MAT_GLASS_UG11,
                    name=name
                )
            
    def get_refinement_zones(self) -> List[RefinementZone]:
        zones_data = self.data.get('refinement_zones', [])
        zones = []
        for z in zones_data:
            zones.append(RefinementZone(
                x_min=float(z.get('x_min', 0)),
                x_max=float(z.get('x_max', 0)),
                y_min=float(z.get('y_min', 0)),
                y_max=float(z.get('y_max', 0)),
                target_dx=float(z.get('target_dx', 1.0)),
                target_dy=float(z.get('target_dy', z.get('target_dx', 1.0))),
                priority=int(z.get('priority', 0))
            ))
        
        # Add default hardcoded zones if none provided? No, declarative should be explicit.
        # But if we are running specific legacy scenarios ported to YAML, we might want to manually include them in YAML.
        return zones

    def get_boundary_conditions(self) -> dict:
        # Check if YAML has explicit BCs
        if 'boundary_conditions' in self.data:
            return self.data['boundary_conditions']
            
        # Fallback for Window Scenarios (Standard)
        return super().get_boundary_conditions()

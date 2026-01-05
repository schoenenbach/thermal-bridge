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
        """
        Resolve variables recursively with expressions support.
        Handles:
        - Simple substitution: ${var} -> value
        - String interpolation: prefix_${var} -> prefix_value
        - Math expressions: ${a} + ${b} -> result
        - Dependencies: a=${b}, b=10 -> a=10
        """
        import math

        # 1. Resolve 'variables' block first (handling dependencies)
        # We limit iterations to prevent infinite loops (circular deps)
        max_iterations = 10
        
        # Prepare safe eval scope
        safe_scope = {"__builtins__": None, "math": math, "abs": abs, "min": min, "max": max}
        
        for _ in range(max_iterations):
            changes_count = 0
            
            # Create a snapshot of current variables for substitution
            current_vars = self.vars.copy()
            
            for key, val in self.vars.items():
                if isinstance(val, str) and "${" in val:
                    # Attempt to resolve this string
                    resolved = self._substitute_and_eval(val, current_vars, safe_scope)
                    if resolved != val:
                        self.vars[key] = resolved
                        changes_count += 1
            
            if changes_count == 0:
                break
        
        # 2. Resolve the rest of data using the fully resolved variables
        self.data = self._recursive_resolve(self.data, self.vars, safe_scope)

    def _substitute_and_eval(self, val_str: str, context: Dict[str, Any], scope: Dict[str, Any]) -> Any:
        """Helper to substitute ${var} and evaluate expressions."""
        if not isinstance(val_str, str):
            return val_str
            
        pattern = r"\$\{(\w+)\}"
        
        # 1. Substitution
        # We need to handle cases where properties are numbers but inserted into strings
        
        matches = list(re.finditer(pattern, val_str))
        if not matches:
            return val_str
            
        # Optimization: If string is EXACTLY "${var}", return the var value directly (preserving type)
        if len(matches) == 1 and matches[0].group(0) == val_str:
            var_name = matches[0].group(1)
            return context.get(var_name, val_str)

        new_val = val_str
        for match in matches:
            var_name = match.group(1)
            if var_name in context:
                val = context[var_name]
                # CRITICAL Fix: Do not substitute if the dependency itself is not resolved yet.
                # This prevents "expanding" formulas which leads to order-of-ops errors.
                if isinstance(val, str) and "${" in val:
                    continue
                    
                # Replace with string representation for regex substitution
                new_val = new_val.replace(match.group(0), str(val))
            else:
                # print(f"[WARNING] Variable '{var_name}' not found.")
                pass
                
        # 2. Evaluation (if it looks like math)
        # Simple heuristic: if it contains math operators and no letters (except e for scientific notation, or known math funcs)
        # This is tricky. Let's just try to eval it. if it fails, return string.
        
        # Only try eval if there are no remaining ${...} (unresolved vars)
        if "${" not in new_val:
            try:
                # Simple check to avoid evaling things like "Wall_50" that result in syntax errors safely,
                # but "10 + 20" works.
                # However, python's eval allows "Wall_50" to be a variable name lookup, which fails in restricted scope.
                # We want to support math.
                result = eval(new_val, scope)
                return result
            except (SyntaxError, NameError, TypeError):
                # Fallback: it's just a string, e.g. "Name_Suffix"
                return new_val
        
        return new_val

    def _recursive_resolve(self, data: Any, context: Dict[str, Any], scope: Dict[str, Any]) -> Any:
        """"Recursively traverse data structure and resolve strings."""
        if isinstance(data, dict):
            return {k: self._recursive_resolve(v, context, scope) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._recursive_resolve(v, context, scope) for v in data]
        elif isinstance(data, str) and "${" in data:
            return self._substitute_and_eval(data, context, scope)
        else:
            return data
        
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
        # 1. Try Registry
        from library.material_registry import MaterialRegistry
        registry = MaterialRegistry.get()
        
        if isinstance(mat_val, str):
            # Try exact match in registry
            prop = registry.get_by_id(mat_val)
            if prop:
                # We need to decide what ID to pass to solver.
                # The registry manages solver_id mapping.
                return (prop.solver_id, prop.lambda_val)
            
            # 2. Legacy Map (Backward Compatibility)
            mat_upper = mat_val.upper()
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
        
        for i, el in enumerate(el_list):
            el_type = el.get('type', 'rect')
            
            # --- Common Params ---
            mat_raw = el.get('material', 'WALL')
            mat_id, mat_lambda = self._resolve_material(mat_raw)
            # Override lambda if explicit
            if 'lambda' in el:
                mat_lambda = float(el['lambda'])
            
            name = el.get('name', f"{el_type}_{i}")
            p = el.get('params', {}).copy()
            # Merge top-level keys into params for convenience if not in params dict
            for k,v in el.items():
                if k not in ['type', 'params', 'material', 'lambda', 'name', 'points']:
                    p[k] = v

            # Add resolved common props to params
            p['name'] = name
            p['material_id'] = mat_id
            p['lambda_val'] = mat_lambda

            # --- Type Handlers ---
            
            if el_type == 'polygon':
                # Polygon is special, handled natively in SketchGeometry usually, but let's see
                # Reference existing points by name
                pt_names = el.get('points', [])
                if pt_names:
                    self.add_shape(pt_names, mat_id, mat_lambda, name)
                else:
                    print(f"[ERROR] Polygon {name} has no points defined.")
            
            else:
                # Use Factory for everything else
                # Note: Factory expects sketch as first arg
                try:
                    elements.Factory.create(el_type, self, **p).build()
                except Exception as e:
                    print(f"[ERROR] Failed to build element '{name}' of type '{el_type}': {e}")
            
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

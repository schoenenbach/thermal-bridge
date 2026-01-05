"""
Declarative Geometry Loader
Parses YAML scenario files to construct a SketchGeometry.
"""

import yaml
from typing import Dict, Any, List, Union
from backend.core.geometry import SketchGeometry, MaterialID, RefinementZone
from backend.core import elements
from backend.core.scenario_schema import Scenario, MaterialDef
from library.material_registry import MaterialRegistry
import re

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
        
        # --- Validate with Pydantic ---
        try:
            self.model = Scenario(**self.data)
        except Exception as e:
            print(f"[FATAL] Schema Validation Failed for scenario '{self.data.get('name', 'Unknown')}':")
            print(e)
            raise e
            
        # 1. Register Local Materials
        self._register_materials()
        
        # 2. Setup Canvas
        self._setup_canvas()
        
        # 3. Define Points
        self._define_points()
        
        # 4. Build Elements (Recursive for components)
        self._build_elements()
        
    def _resolve_variables(self):
        """
        Resolve variables recursively with expressions support.
        Handles:
        - Simple substitution: ${var} -> value
        - String interpolation: prefix_${var} -> prefix_value
        - Math expressions: ${a} + ${b} -> result
        """
        import math
        max_iterations = 10
        safe_scope = {"__builtins__": None, "math": math, "abs": abs, "min": min, "max": max}
        
        for _ in range(max_iterations):
            changes_count = 0
            current_vars = self.vars.copy()
            
            for key, val in self.vars.items():
                if isinstance(val, str) and "${" in val:
                    resolved = self._substitute_and_eval(val, current_vars, safe_scope)
                    if resolved != val:
                        self.vars[key] = resolved
                        changes_count += 1
            if changes_count == 0: break
        
        self.data = self._recursive_resolve(self.data, self.vars, safe_scope)

    def _substitute_and_eval(self, val_str: str, context: Dict[str, Any], scope: Dict[str, Any]) -> Any:
        if not isinstance(val_str, str): return val_str
        pattern = r"\$\{(\w+)\}"
        matches = list(re.finditer(pattern, val_str))
        if not matches: return val_str
            
        if len(matches) == 1 and matches[0].group(0) == val_str:
            return context.get(matches[0].group(1), val_str)

        new_val = val_str
        for match in matches:
            var_name = match.group(1)
            if var_name in context:
                val = context[var_name]
                if isinstance(val, str) and "${" in val: continue
                new_val = new_val.replace(match.group(0), str(val))
                
        if "${" not in new_val:
            try:
                return eval(new_val, scope)
            except (SyntaxError, NameError, TypeError):
                return new_val
        return new_val

    def _recursive_resolve(self, data: Any, context: Dict[str, Any], scope: Dict[str, Any]) -> Any:
        if isinstance(data, dict):
            return {k: self._recursive_resolve(v, context, scope) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._recursive_resolve(v, context, scope) for v in data]
        elif isinstance(data, str) and "${" in data:
            return self._substitute_and_eval(data, context, scope)
        else:
            return data
            
    def _register_materials(self):
        """Register local materials from YAML to the registry."""
        registry = MaterialRegistry.get()
        
        # Reserved IDs for core materials (Must match geometry.MaterialID)
        # Reserved IDs for core materials (Must match geometry.MaterialID)
        RESERVED_IDS = {
            "AIR_EXT": MaterialID.AIR_EXT,
            "AIR_INT": MaterialID.AIR_INT,
            "WALL": MaterialID.WALL,
            "INSULATION": MaterialID.INSULATION,
            "REVEAL_INS": MaterialID.REVEAL_INS,
            "FRAME": MaterialID.FRAME,
            "GLASS": MaterialID.GLASS,
            "SPACER": MaterialID.SPACER,
            "CAVITY": MaterialID.CAVITY,
            "STYRODUR": MaterialID.STYRODUR,
            "CONCRETE": MaterialID.CONCRETE,
            "WOOD": MaterialID.WOOD,
            "ALUMINUM": MaterialID.ALUMINUM
        }
        
        for mat in self.model.materials:
            mat_dict = {
                "id": mat.id,
                "name": mat.id, 
                "lambda": mat.lambda_val,
                "color": mat.color,
                "description": mat.description or ""
            }
            
            # Priority 1: Explicit solver_id from YAML
            if mat.solver_id is not None:
                mat_dict["id_numeric"] = mat.solver_id
            
            # Priority 2: Reserved Name check
            elif mat.id in RESERVED_IDS:
                mat_dict["id_numeric"] = RESERVED_IDS[mat.id]
                
            registry._register_material(mat_dict)

    def _setup_canvas(self):
        self.set_canvas(
            x_min=self.model.canvas.x_min,
            x_max=self.model.canvas.x_max,
            y_min=self.model.canvas.y_min,
            y_max=self.model.canvas.y_max,
            grid_mm=self.model.canvas.grid
        )
        
    def _define_points(self):
        for name, coords in self.model.points.items():
            self.add_point(name, float(coords[0]), float(coords[1]))

    def _resolve_material(self, mat_val: Union[str, int]) -> tuple[int, float]:
        """Resolve material ID/Lambda from string or int."""
        from library.material_registry import MaterialRegistry
        registry = MaterialRegistry.get()
        
        # 1. Direct Integer (Legacy or Solver ID)
        if isinstance(mat_val, int):
            return (mat_val, 0.025) # Default lambda? Or lookup?
            
        # 2. String Lookup
        prop = registry.get_by_id(mat_val)
        if prop:
            return (prop.solver_id, prop.lambda_val)
            
        # 3. Fallback (Global Defaults / Legacy Map)
        # We keep the legacy map for backward compatibility with 'WALL' etc not defined in YAML
        from backend.core.config import (
            MAT_WALL, MAT_INSULATION, MAT_REVEAL_INSULATION, MAT_FRAME_EQ, MAT_GLASS_UG11,
            MAT_STYRODUR, MAT_ALUMINUM, MAT_CAVITY_ISO
        )
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

        
        # Case-insensitive lookup for legacy map
        mat_upper = str(mat_val).upper()
        if mat_upper in MAT_MAP:
            return MAT_MAP[mat_upper]
            
        print(f"[WARNING] Unknown material '{mat_val}', defaulting to WALL")
        return (MaterialID.WALL, MAT_WALL)

    def _build_elements(self):
        for el_dict in self.model.elements:
            self._instantiate_element(el_dict)
            
    def _instantiate_element(self, el_dict: Dict[str, Any], offset_x: float = 0, offset_y: float = 0):
        # 1. Check if it's a Component Definition
        el_type = el_dict.get('type')
        if el_type in self.model.definitions:
            self._instantiate_component(el_type, el_dict.get('params', {}), offset_x, offset_y)
            return

        # 2. Regular Element Construction
        # Prepare Params
        p = el_dict.get('params', {}).copy()
        
        # Merge top-level keys into params (legacy support + convenience)
        for k,v in el_dict.items():
            if k not in ['type', 'params', 'material', 'lambda', 'name', 'points']:
                p[k] = v
        
        # Apply Offsets (for recursive components)
        if offset_x != 0 or offset_y != 0:
            if 'x' in p: p['x'] = float(p['x']) + offset_x
            if 'y' in p: p['y'] = float(p['y']) + offset_y
            if 'x_base' in p: p['x_base'] = float(p['x_base']) + offset_x
            # Add more coord shifts if needed (e.g. polygon points? complex)
            
        # Common Props
        name = el_dict.get('name', f"{el_type}")
        mat_raw = el_dict.get('material', 'WALL')
        
        mat_id, mat_lambda = self._resolve_material(mat_raw)
        if 'lambda' in el_dict and el_dict['lambda'] is not None:
            mat_lambda = float(el_dict['lambda'])
            
        p['name'] = name
        p['material_id'] = mat_id
        p['lambda_val'] = mat_lambda
        
        # Special Types
        if el_type == 'polygon':
            pt_names = el_dict.get('points', [])
            if pt_names:
                self.add_shape(pt_names, mat_id, mat_lambda, name)
            return
            
        # Factory
        try:
            elements.Factory.create(el_type, self, **p).build()
        except Exception as e:
            print(f"[ERROR] Build failed for '{name}' ({el_type}): {e}")

    def _instantiate_component(self, comp_name: str, params: Dict[str, Any], off_x: float, off_y: float):
        definition = self.model.definitions[comp_name]
        
        # TODO: Parameter substitution within component definition?
        # The variables logic handled top-level substitution.
        # But if a component has params like {x: "$x_base"}, we need to substitute using the *call time* params.
        # This is essentially a micro-scope resolution.
        
        # For simplicity, let's assume component geometry is defined relative to 0,0 
        # or uses explicit offset logic. 
        # But wait, usually components need parameter passing.
        
        # Let's perform a mini-substitution on the definition's elements using `params`
        import math
        scope = {"__builtins__": None, "math": math}
        
        # We need to deep copy the definition elements to avoid mutating the template
        import copy
        def_elements = copy.deepcopy(definition.elements)
        
        # Resolve 'params' inside the definition elements using the provided 'params'
        # Convert Pydantic models to dicts for our resolver
        # Actually `definition.elements` are `ElementBase` models.
        
        context = params.copy() # The values passed from caller
        
        # Add basic offsets to context if helpful? No, keep pure.
        
        for sub_el in def_elements:
            # sub_el is ElementBase
            sub_dict = sub_el.model_dump()
            
            # Resolve Only Params? Or everything?
            resolved_sub = self._recursive_resolve(sub_dict, context, scope)
            
            # Instantiate (recursive)
            # We pass off_x/off_y to shift the result
            self._instantiate_element(resolved_sub, offset_x=off_x, offset_y=off_y)

    def get_boundary_conditions(self) -> dict:
        # Convert Pydantic BC model to dict format expected by Solver
        return self.model.boundary_conditions.model_dump()

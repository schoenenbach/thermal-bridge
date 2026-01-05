"""
Geometry Builder Helper
Converts Streamlit Canvas JSON to Declarative Scenario Dictionary.
"""

from typing import Dict, Any, List, Tuple, Optional
from backend.core.geometry import MaterialID
from backend.core import elements as el_lib


def get_element_bbox(scenario_data: Dict[str, Any], element_index: int) -> Optional[Tuple[float, float, float, float]]:
    """
    Extract bounding box (x, y, width, height) for an element after resolving variables.
    
    Returns None if element cannot provide a bbox (e.g., unknown type or missing params).
    """
    elements = scenario_data.get('elements', [])
    if element_index < 0 or element_index >= len(elements):
        return None
    
    el = elements[element_index]
    variables = scenario_data.get('variables', {})
    
    def resolve(val):
        if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
            k = val[2:-1]
            return variables.get(k, val)
        return val
    
    el_type = el.get('type', '')
    params = el.get('params', {})
    
    # Handle rect/wall types with x, y, width, height
    if el_type in ('rect', 'wall', 'air', 'venetian_blind'):
        try:
            x = float(resolve(params.get('x', el.get('x', 0))))
            y = float(resolve(params.get('y', el.get('y', 0))))
            w = float(resolve(params.get('width', el.get('width', 0))))
            h = float(resolve(params.get('height', el.get('height', 0))))
            return (x, y, w, h)
        except (ValueError, TypeError):
            return None
    
    # Handle insulation_tapered
    elif el_type == 'insulation_tapered':
        try:
            x_base = float(resolve(params.get('x_base', 0)))
            y_bottom = float(resolve(params.get('y_bottom', 0)))
            y_top = float(resolve(params.get('y_top', 0)))
            thick_main = float(resolve(params.get('thick_main', 0)))
            return (x_base, y_bottom, thick_main, y_top - y_bottom)
        except (ValueError, TypeError):
            return None
    
    # Handle window_detail
    elif el_type == 'window_detail':
        try:
            x = float(resolve(params.get('x_frame_start', 0)))
            y = float(resolve(params.get('y_frame_start', 0)))
            frame_depth = float(resolve(params.get('frame_depth', 70)))
            y_top = float(resolve(params.get('y_top', y + 100)))
            return (x, y, frame_depth + 50, y_top - y)  # Approximate width
        except (ValueError, TypeError):
            return None
    
    # Handle polygon - compute bounding box from points
    elif el_type == 'polygon':
        try:
            point_names = el.get('points', [])
            points_def = scenario_data.get('points', {})
            
            xs, ys = [], []
            for pname in point_names:
                if pname in points_def:
                    coords = points_def[pname]
                    xs.append(float(resolve(coords[0])))
                    ys.append(float(resolve(coords[1])))
            
            if xs and ys:
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)
                return (x_min, y_min, x_max - x_min, y_max - y_min)
        except (ValueError, TypeError):
            return None
    
    return None

# Material Color Mapping (Hex -> Material Name)
COLOR_MAP = {
    "#808080": "WALL",        # Gray
    "#FFA500": "INSULATION",  # Orange
    "#A9A9A9": "CONCRETE",    # Dark Gray
    "#8B4513": "WOOD",        # Brown
    "#87CEEB": "GLASS",       # Sky Blue
    "#F5F5F5": "FRAME",       # White Smoke
    "#0000FF": "ALUMINUM",    # Blue
    "#E0F7FA": "AIR_EXT",     # Light Cyan (Visible Air)
    "#FFEBEE": "AIR_INT",     # Light Pink (Internal Air)
}

# Reverse Color Map (Material Name -> Hex)
MATERIAL_TO_COLOR = {v: k for k, v in COLOR_MAP.items()}

# Special handling for missing/custom
MATERIAL_TO_COLOR["CAVITY"] = "#FFFFFF" # White
MATERIAL_TO_COLOR["FRAME_EQ"] = "#F5F5F5" # Frame

DEFAULT_MATERIAL = "WALL"

class MockSketchRobust:
    def __init__(self, scale_mm_per_px: float, canvas_height_px: int):
        self.scale_mm_per_px = scale_mm_per_px
        self.scale_px_per_mm = 1.0 / scale_mm_per_px
        self.canvas_height_px = canvas_height_px
        self.points = {}
        self.objects = []
        
    def add_point(self, name, x, y):
        self.points[name] = (x, y)
        
    def add_shape(self, point_names: List[str], material_id: int, lambda_val: float, name: str):
        if not point_names:
            return

        # Resolve coordinates
        coords = []
        for pname in point_names:
            if pname in self.points:
                coords.append(self.points[pname])
                
        if not coords:
            return
            
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        width_mm = max_x - min_x
        height_mm = max_y - min_y
        
        # Transform to Canvas Coords
        # We assume SimLayoutHeight corresponds to canvas_height_px * scale_mm_per_px
        layout_height_mm = self.canvas_height_px * self.scale_mm_per_px
        
        x_px = min_x * self.scale_px_per_mm
        y_px = (layout_height_mm - max_y) * self.scale_px_per_mm
        w_px = width_mm * self.scale_px_per_mm
        h_px = height_mm * self.scale_px_per_mm
        
        # Material to Color
        fill = "#CCCCCC"
        if material_id == 2: fill = "#808080" # Wall
        elif material_id == 3: fill = "#FFA500" # Insulation
        elif material_id == 5: fill = "#F5F5F5" # Frame
        elif material_id == 6: fill = "#87CEEB" # Glass
        elif material_id == 8: fill = "#0000FF" # Aluminum
        elif material_id == 0: fill = "#E0F7FA" # Air Ext
        elif material_id == 1: fill = "#FFEBEE" # Air Int
        elif material_id == 9: fill = "#E0F7FA" # OLD_ID? No, Geometry.MaterialID says 0=EXT, 1=INT.
        # Check defaults if 9 was used for something else. Styrodur is 9 in geometry.py.
        # Let's align with geometry.py
        elif material_id == MaterialID.STYRODUR: fill = "#DDA0DD" # Plum
        
        # Base Object Dict
        obj = {
            "type": "rect", # Default
            "version": "4.4.0",
            "originX": "left",
            "originY": "top",
            "fill": fill,
            "stroke": "#000000",
            "strokeWidth": 1,
            "selectable": True,
            "hasControls": True,
            "angle": 0,
            "sim_name": name
        }
        
        # Check alignment for Rect vs Polygon
        # Rect if 4 points and axis-aligned
        x_unique = sorted(list(set(xs)))
        y_unique = sorted(list(set(ys)))
        
        if len(coords) == 4 and len(x_unique) == 2 and len(y_unique) == 2:
            # Axis-aligned rectangle
            obj.update({
                "type": "rect",
                "left": x_px,
                "top": y_px,
                "width": w_px,
                "height": h_px
            })
            self.objects.append(obj)
        else:
            # Polygon
            # Convert to absolute px coords for points
            poly_points = []
            for (mx, my) in coords:
                px = mx * self.scale_px_per_mm
                py = (layout_height_mm - my) * self.scale_px_per_mm
                poly_points.append({'x': px, 'y': py})
                
            # Compute bounds of poly_points to set left/top correctly
            pxs = [p['x'] for p in poly_points]
            pys = [p['y'] for p in poly_points]
            min_px, min_py = min(pxs), min(pys)
            w_p = max(pxs) - min(pxs)
            h_p = max(pys) - min(pys)
            
            # Normalize points relative to top-left
            norm_points = [{'x': p['x'] - min_px, 'y': p['y'] - min_py} for p in poly_points]
            
            obj.update({
                "type": "polygon",
                "left": min_px,
                "top": min_py,
                "width": w_p,
                "height": h_p,
                "points": norm_points
            })
            self.objects.append(obj)

def scenario_to_canvas(scenario_data: Dict[str, Any], 
                       canvas_width_px: int = 600, 
                       canvas_height_px: int = 400) -> Dict[str, Any]:
    """
    Generate Canvas JSON from Declarative Scenario.
    """
    
    # 1. Determine Scale
    bounds = scenario_data.get('canvas', {}).get('bounds', [0, 1000, 0, 1000])
    scen_w = bounds[1] - bounds[0]
    scen_h = bounds[3] - bounds[2]
    
    scale_x = canvas_width_px / scen_w if scen_w > 0 else 1.0
    scale_y = canvas_height_px / scen_h if scen_h > 0 else 1.0
    scale_px_per_mm = min(scale_x, scale_y)
    scale_mm_per_px = 1.0 / scale_px_per_mm
    
    # Mock Sketch
    sketch = MockSketchRobust(scale_mm_per_px, canvas_height_px)
    
    # Process Elements
    element_defs = scenario_data.get('elements', [])
    obj_to_el_map = {} # obj_idx -> el_idx
    
    # Variables Helper
    variables = scenario_data.get('variables', {})
    def resolve(val):
        if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
            k = val[2:-1]
            if k in variables: 
                return variables[k]
        return val

    def resolve_dict(d):
        new_d = {}
        for k, v in d.items():
            if isinstance(v, str):
                new_d[k] = resolve(v)
            elif isinstance(v, dict):
                new_d[k] = resolve_dict(v)
            else:
                new_d[k] = v
        return new_d

    for el_idx, el_def in enumerate(element_defs):
        params = resolve_dict(el_def.get('params', {}))
        if 'name' in el_def: params['name'] = el_def['name']
        if 'points' in el_def: params['points'] = el_def['points']
        
        # Map Material to ID
        mat_id = 2 # Default WALL
        if 'material' in el_def:
            mn = el_def['material']
            if mn == 'INSULATION': mat_id = 3
            elif mn == 'FRAME': mat_id = 5
            elif mn == 'GLASS': mat_id = 6
            elif mn == 'ALUMINUM': mat_id = 8
            elif mn == 'AIR_EXT': mat_id = 0 # MaterialID.AIR_EXT
            elif mn == 'AIR_INT': mat_id = 1 # MaterialID.AIR_INT
            elif mn == 'STYRODUR': mat_id = 9
            
            # Update params with ID if needed by Factory
            params['material_id'] = mat_id
            
        el_type = el_def.get('type')
        start_obj_count = len(sketch.objects)
        
        try:
            # Handle Polygon Points
            if el_type == 'polygon':
                scen_points = scenario_data.get('points', {})
                for pname, coords in scen_points.items():
                    sketch.add_point(pname, float(coords[0]), float(coords[1]))
            
            element_inst = el_lib.Factory.create(el_type, sketch, **params)
            element_inst.build()
            
        except Exception as e:
            # print(f"Error building element {el_idx}: {e}")
            pass
            
        end_obj_count = len(sketch.objects)
        
        # Link objects to element
        for i in range(start_obj_count, end_obj_count):
            obj_to_el_map[i] = el_idx
            # Also map sim_name to element index
            if i < len(sketch.objects):
                obj_name = sketch.objects[i].get('sim_name')
                if obj_name:
                    obj_to_el_map[obj_name] = el_idx

    return {
        "version": "4.4.0",
        "objects": sketch.objects,
        "background": "#eeeeee",
        "metadata": {
            "scale_mm_per_px": scale_mm_per_px,
            "obj_map": obj_to_el_map
        }
    }

def _process_objects_to_scenario(objects: List[Dict], scale: float, height_px: int) -> Tuple[List[Dict], Dict[str, List[float]]]:
    elements = []
    points_def = {}
    
    for i, obj in enumerate(objects):
        otype = obj.get("type")
        
        # Resolve Material
        fill = obj.get("fill", "").upper()
        mat = DEFAULT_MATERIAL
        if fill in COLOR_MAP:
            mat = COLOR_MAP[fill]
        else:
            for k, v in COLOR_MAP.items():
                if k.upper() == fill:
                    mat = v
                    break
        
        name = obj.get("sim_name", f"{otype}_{i}")
        
        if otype == "rect":
            x_px = obj.get("left", 0)
            y_px = obj.get("top", 0)
            w_px = obj.get("width", 0)
            h_px = obj.get("height", 0)
            
            # Simple transform (Canvas Top-Left -> Sim Bottom-Left)
            x_mm = x_px * scale
            w_mm = w_px * scale
            h_mm = h_px * scale
            y_mm = (height_px - (y_px + h_px)) * scale
            
            el = {
                "type": "rect",
                "name": name,
                "material": mat,
                "params": {
                    "x": round(x_mm, 2),
                    "y": round(y_mm, 2),
                    "width": round(w_mm, 2),
                    "height": round(h_mm, 2)
                }
            }
            elements.append(el)
            
        elif otype == "polygon":
            # Extract points
            poly_pts = obj.get("points", [])
            left = obj.get("left", 0)
            top = obj.get("top", 0)
            
            # Absolute pixels -> Sim Coords
            point_names = []
            for j, p in enumerate(poly_pts):
                abs_x = left + p['x']
                abs_y = top + p['y']
                
                mx = abs_x * scale
                my = (height_px - abs_y) * scale
                
                pname = f"{name}_P{j}"
                points_def[pname] = [round(mx, 2), round(my, 2)]
                point_names.append(pname)
            
            el = {
                "type": "polygon",
                "name": name,
                "material": mat,
                "points": point_names
            }
            elements.append(el)
            
    return elements, points_def

def objects_to_elements(objects: List[Dict], scale: float, height_px: int) -> List[Dict]:
    """Legacy wrapper."""
    els, _ = _process_objects_to_scenario(objects, scale, height_px)
    return els

def generate_scenario(canvas_data: Dict[str, Any], 
                      canvas_width_px: int = 600, 
                      canvas_height_px: int = 400, 
                      scale_mm_per_px: float = 10.0,
                      base_scenario: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Main entry point.
    """
    
    elements, new_points = _process_objects_to_scenario(
        canvas_data.get("objects", []), 
        scale_mm_per_px, 
        canvas_height_px
    )
    
    # Calculate bounds
    width_mm = canvas_width_px * scale_mm_per_px
    height_mm = canvas_height_px * scale_mm_per_px
    
    # Start with base if provided
    scenario = base_scenario.copy() if base_scenario else {}
    
    # Merge/Overwrite specifics
    scenario["name"] = f"{scenario.get('name', 'Canvas Export')} (Edited)"
    
    # Canvas
    if 'canvas' not in scenario:
        scenario['canvas'] = {}
    scenario['canvas']['bounds'] = [0, width_mm, 0, height_mm]
    scenario['canvas']['grid'] = 10.0
    
    # BCs - Preserve if exists, else Default
    if 'boundary_conditions' not in scenario:
        scenario['boundary_conditions'] = {
            "T_int": 20.0,
            "T_ext": -5.0,
            "h_int": 7.69,
            "h_ext": 25.0
        }
        
    # Elements - Overwrite
    scenario['elements'] = elements
    
    # Points - Merge
    if 'points' not in scenario:
        scenario['points'] = {}
    scenario['points'].update(new_points)
    
    return scenario

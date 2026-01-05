"""
Geometry Builder Helper
Converts Streamlit Canvas JSON to Declarative Scenario Dictionary.
"""

from typing import Dict, Any, List

# Material Color Mapping (Hex -> Material Name)
COLOR_MAP = {
    "#808080": "WALL",        # Gray
    "#FFA500": "INSULATION",  # Orange
    "#A9A9A9": "CONCRETE",    # Dark Gray
    "#8B4513": "WOOD",        # Brown
    "#87CEEB": "GLASS",       # Sky Blue
    "#F5F5F5": "FRAME",       # White Smoke
    "#0000FF": "ALUMINUM",    # Blue
    "#FFFFFF": "AIR_EXT",     # White (or transparent)
}

DEFAULT_MATERIAL = "WALL"

def canvas_to_scenario(canvas_data: Dict[str, Any], 
                       canvas_width_mm: float = 1000.0) -> Dict[str, Any]:
    """
    Convert canvas state to scenario dictionary.
    
    Args:
        canvas_data: JSON output from st_drawable_canvas
        canvas_width_mm: The physical width represented by the canvas in mm.
    
    Returns:
        Dict representing the scenario.
    """
    objects = canvas_data.get("objects", [])
    
    # 1. Determine Scale and Canvas Dimensions
    # We rely on the canvas_data to tell us the pixel dimensions if possible,
    # but st_drawable_canvas often just gives objects. 
    # We assume standard canvas size or derive from max extent?
    # Better: The user (caller) should know the pixel width of the canvas used.
    # But st_drawable_canvas state doesn't natively include the canvas dims itself in the 'objects' payload usually.
    # However, 'properties' sometimes exists.
    # Let's assume the canvas was 600px wide (default) if not found.
    # Actually, we can just treat the coordinates as relative if we don't have absolute px.
    # Let's try to infer or require it. For now, we assume a logical coordinate element.
    # FIX: Let's assume 1 pixel = (canvas_width_mm / canvas_width_px) mm.
    # Since we can't easily know the canvas width px from here without passing it,
    # let's assume the user matches the input.
    # Ideally, we just treat the input values as raw units if the user sets 1px = 1mm.
    # But typically canvas is small (pixels).
    
    # Heuristic: Find max extent in X to fallback? No.
    # Let's assume a fixed scale for MVP: 1 pixel = 10 mm.
    # Or passed as argument? 
    # Let's make it a parameter 'scale_mm_per_px' instead of total width.
    pass

def objects_to_elements(objects: List[Dict], scale: float, height_px: int) -> List[Dict]:
    elements = []
    
    for i, obj in enumerate(objects):
        otype = obj.get("type")
        if otype != "rect":
            continue # Only rects for now
            
        # Canvas Coords (Top-Left 0,0)
        x_px = obj.get("left", 0)
        y_px = obj.get("top", 0)
        w_px = obj.get("width", 0)
        h_px = obj.get("height", 0)
        fill = obj.get("fill", "").upper()
        
        # Resolve Material
        # Handle 3-char hex colors and specific cases if needed
        # Robust mapping
        mat = DEFAULT_MATERIAL
        # Try exact match
        if fill in COLOR_MAP:
            mat = COLOR_MAP[fill]
        else:
            # Try to find closest? Or just default.
            # Maybe check keys ignoring case
            for k, v in COLOR_MAP.items():
                if k.upper() == fill:
                    mat = v
                    break
        
        # Coordinate Transformation
        # Sim Coords (Bottom-Left 0,0)
        # y_sim = H - (y_px + h_px)
        
        x_mm = x_px * scale
        w_mm = w_px * scale
        h_mm = h_px * scale
        y_mm = (height_px - (y_px + h_px)) * scale
        
        el = {
            "type": "rect",
            "name": f"Rect_{i}",
            "material": mat,
            "x": round(x_mm, 2),
            "y": round(y_mm, 2),
            "width": round(w_mm, 2),
            "height": round(h_mm, 2)
        }
        elements.append(el)
        
    return elements

def generate_scenario(canvas_data: Dict[str, Any], 
                      canvas_width_px: int = 600, 
                      canvas_height_px: int = 400, 
                      scale_mm_per_px: float = 10.0) -> Dict[str, Any]:
    """
    Main entry point.
    """
    
    elements = objects_to_elements(
        canvas_data.get("objects", []), 
        scale_mm_per_px, 
        canvas_height_px
    )
    
    # Calculate bounds
    width_mm = canvas_width_px * scale_mm_per_px
    height_mm = canvas_height_px * scale_mm_per_px
    
    scenario = {
        "name": "Canvas Export",
        "canvas": {
            "bounds": [0, width_mm, 0, height_mm],
            "grid": 10.0
        },
        "boundary_conditions": {
            "T_int": 20.0,
            "T_ext": -5.0,
            "h_int": 7.69, # Standard
            "h_ext": 25.0
        },
        "elements": elements
    }
    
    return scenario

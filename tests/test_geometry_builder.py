
import pytest
from geometry_builder import canvas_to_scenario, generate_scenario, objects_to_elements

def test_objects_to_elements_conversion():
    # Setup mock canvas data
    # Canvas Size: 600x400 px
    # Scale: 10 mm/px -> 6000x4000 mm
    
    scale = 10.0
    height_px = 400
    
    objects = [
        {
            "type": "rect",
            "left": 10,
            "top": 10,
            "width": 100,
            "height": 50,
            "fill": "#808080" # WALL
        },
        {
            "type": "rect", 
            "left": 200,
            "top": 300, 
            "width": 50,
            "height": 50,
            "fill": "#FFA500" # INSULATION
        }
    ]
    
    elements = objects_to_elements(objects, scale, height_px)
    
    assert len(elements) == 2
    
    # Check Element 1 (Wall)
    # y_sim = (400 - (10 + 50)) * 10 = (340) * 10 = 3400
    el1 = elements[0]
    assert el1['type'] == 'rect'
    assert el1['material'] == 'WALL'
    assert el1['x'] == 10 * 10
    assert el1['y'] == 3400.0
    assert el1['width'] == 100 * 10
    assert el1['height'] == 50 * 10
    
    # Check Element 2 (Insulation)
    # y_sim = (400 - (300 + 50)) * 10 = 50 * 10 = 500
    el2 = elements[1]
    assert el2['material'] == 'INSULATION'
    assert el2['y'] == 500.0

def test_generate_scenario_structure():
    canvas_data = {
        "objects": [
            {"type": "rect", "left": 0, "top": 0, "width": 10, "height": 10, "fill": "#808080"}
        ]
    }
    
    scen = generate_scenario(canvas_data, canvas_width_px=100, canvas_height_px=100, scale_mm_per_px=1.0)
    
    assert "name" in scen
    assert "canvas" in scen
    assert scen["canvas"]["bounds"] == [0, 100.0, 0, 100.0]
    assert "elements" in scen
    assert len(scen["elements"]) == 1
    assert scen["elements"][0]["y"] == 90.0 # 100 - (0+10)


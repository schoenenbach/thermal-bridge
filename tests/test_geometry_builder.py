
import pytest
from geometry_builder import scenario_to_canvas, MockSketchRobust

def test_mock_sketch_robust():
    sketch = MockSketchRobust(scale_mm_per_px=10.0, canvas_height_px=400)
    
    # Simulate drawing a rect (as elements.RectElement does)
    sketch.add_point("A", 100, 100)
    sketch.add_point("B", 200, 100)
    sketch.add_point("C", 200, 200)
    sketch.add_point("D", 100, 200)
    
    sketch.add_shape(["A", "B", "C", "D"], material_id=2, lambda_val=0.5, name="TestRect")
    
    assert len(sketch.objects) == 1
    obj = sketch.objects[0]
    assert obj['type'] == 'rect'
    
    # Scale: 10mm/px -> 0.1 px/mm
    # Sim H = 400 * 10 = 4000mm
    # Rect Y=100. Top in Sim. 
    # Canvas Y = (LayoutH - MaxY) * scale
    # LayoutH = 4000
    # MaxY = 200
    # Y_px = (4000 - 200) * 0.1 = 3800 * 0.1 = 380.0
    
    assert obj['top'] == 380.0
    assert obj['left'] == 100 * 0.1 # 10.0
    assert obj['width'] == 100 * 0.1 # 10.0
    assert obj['height'] == 100 * 0.1 # 10.0

def test_scenario_to_canvas_basic():
    scenario = {
        "canvas": {"bounds": [0, 500, 0, 500]},
        "elements": [
            {
                "type": "rect",
                "params": {"x": 0, "y": 0, "width": 100, "height": 100, "name": "R1"}
            }
        ]
    }
    
    canvas_data = scenario_to_canvas(scenario, canvas_width_px=500, canvas_height_px=500)
    
    assert len(canvas_data['objects']) == 1
    obj = canvas_data['objects'][0]
    # 500mm / 500px = 1mm/px
    # LayoutH = 500
    # Rect Y=0..100 -> MaxY=100
    # Top = 500 - 100 = 400
    assert obj['top'] == 400
    assert obj['left'] == 0
    assert obj['width'] == 100
    assert obj['height'] == 100
    
def test_scenario_to_canvas_variables():
    scenario = {
        "canvas": {"bounds": [0, 500, 0, 500]},
        "variables": {"w": 150.0},
        "elements": [
            {
                "type": "rect",
                "params": {"x": 0, "y": 0, "width": "${w}", "height": 100}
            }
        ]
    }
    canvas_data = scenario_to_canvas(scenario, canvas_width_px=500, canvas_height_px=500)
    obj = canvas_data['objects'][0]
    assert obj['width'] == 150.0

    # Verify Metadata
    assert 'metadata' in canvas_data
    obj_map = canvas_data['metadata']['obj_map']
    # Check index mapping
    assert obj_map[0] == 0
    # Check name mapping (assuming default name "rect_0" or "R1")
    assert obj_map["R1"] == 0

def test_scenario_to_canvas_variables():
    scenario = {
        "canvas": {"bounds": [0, 500, 0, 500]},
        "variables": {"w": 150.0},
        "elements": [
            {
                "type": "rect",
                "params": {"x": 0, "y": 0, "width": "${w}", "height": 100}
            }
        ]
    }
    canvas_data = scenario_to_canvas(scenario, canvas_width_px=500, canvas_height_px=500)
    obj = canvas_data['objects'][0]
    assert obj['width'] == 150.0

def test_scenario_with_window_detail():
    # Test complex element producing multiple objects
    scenario = {
        "canvas": {"bounds": [0, 1000, 0, 1000]},
        "elements": [
             {
                 "type": "window_detail",
                 "name": "Win1",
                 "params": {
                     "x_frame_start": 0, "y_frame_start": 0,
                     "frame_depth": 70, "frame_width": 70,
                     "sash_depth": 70, "sash_width": 70,
                     "sash_overlap": 20, "sash_recess": 20,
                     "glass_thickness": 24, "y_top": 500
                 }
             }
        ]
    }
    canvas_data = scenario_to_canvas(scenario, canvas_width_px=1000, canvas_height_px=1000)
    
    # WindowDetail produces 3 objects: Fixed, Sash, Glass
    assert len(canvas_data['objects']) == 3
    
    obj_map = canvas_data['metadata']['obj_map']
    
    # All 3 objects should map to element index 0
    assert obj_map[0] == 0
    assert obj_map[1] == 0
    assert obj_map[2] == 0
    
    # Check name mapping
    assert obj_map["Win1_Fixed"] == 0
    assert obj_map["Win1_Sash"] == 0
    assert obj_map["Win1_Glass"] == 0

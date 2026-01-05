
import pytest
from backend.core.geometry_builder import scenario_to_canvas, generate_scenario
from backend.core.config import MAT_WALL


def test_roundtrip_polygon_corruption():
    # Scenario with a Polygon
    scenario = {
        "name": "PolyTest",
        "canvas": {"bounds": [0, 100, 0, 100]},
        "boundary_conditions": {"T_int": 99.0},
        "points": {"P0": [10, 10], "P1": [50, 10], "P2": [30, 40]},
        "elements": [
            {
                "type": "polygon",
                "name": "TestPoly",
                "material": "WALL",
                "points": ["P0", "P1", "P2"]
            }
        ]
    }
    
    # 1. Provide MockSketch with points (via scenario_to_canvas which logic was added to)
    canvas_json = scenario_to_canvas(scenario, canvas_width_px=100, canvas_height_px=100)
    
    # Check if object is polygon
    assert len(canvas_json['objects']) == 1
    obj = canvas_json['objects'][0]
    assert obj['type'] == 'polygon'
    assert len(obj['points']) == 3
    
    # 2. Roundtrip back
    new_scenario = generate_scenario(canvas_json, base_scenario=scenario)
    
    # Check if element type is polygon
    assert len(new_scenario['elements']) == 1
    el = new_scenario['elements'][0]
    assert el['type'] == 'polygon'
    assert len(el['points']) == 3 

def test_roundtrip_metadata_loss():
    base_scenario = {
        "name": "Base",
        "boundary_conditions": {"T_int": 99.0, "mytag": "preserved"},
        "elements": []
    }
    
    # Canvas representation (empty)
    canvas_json = {"objects": []}
    
    # Roundtrip WITH base
    new_scenario = generate_scenario(canvas_json, base_scenario=base_scenario)
    
    # Check if BCs are preserved
    assert new_scenario['boundary_conditions']['T_int'] == 99.0 
    assert new_scenario['boundary_conditions'].get('mytag') == "preserved"

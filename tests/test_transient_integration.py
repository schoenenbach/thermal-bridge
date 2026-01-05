import pytest
import os
import sys
import glob

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.simulation_engine import solve_scenario
from backend.core.geometry import MaterialID

def test_transient_dispatch():
    """
    Test that solve_scenario correctly dispatches to transient solver
    when 'transient: enabled: true' is present in config.
    """
    # Create a minimal config
    cfg = {
        "name": "test_transient_dispatch",
        "canvas": {
            "bounds": [0, 100, 0, 100],
            "grid": 10.0
        },
        "elements": [
            {"type": "rect", "material": MaterialID.WALL, "params": {"x":0, "y":0, "width":100, "height":100}}
        ],
        "transient": {
            "enabled": True,
            "duration_hours": 0.01, # Short duration (36s)
            "dt_seconds": 12.0,
            "save_interval_steps": 1
        },
        "measurements": {
            "point_probes": [
                {"name": "EndTemp", "x": 50, "y": 50}
            ]
        }
    }
    
    scenario_def = {
        "name": "Test Transient",
        "file_suffix": "test",
        "cfg": cfg
    }
    
    # Clean up previous runs
    for f in glob.glob("result_test_transient_dispatch*"):
        try:
            os.remove(f)
        except:
            pass
            
    # Run solver
    result = solve_scenario(scenario_def, use_adaptive_mesh=False)
    
    # Check result structure
    assert "measurements" in result
    assert "final_temp" in result
    assert "EndTemp" in result["measurements"]
    
    # Check if files were created
    # We expect result_test_transient_dispatch.gif and result_test_transient_dispatch_final.png
    assert os.path.exists("result_test_transient_dispatch.gif")
    assert os.path.exists("result_test_transient_dispatch_final.png")
    
    # Cleanup
    for f in glob.glob("result_test_transient_dispatch*"):
        try:
            os.remove(f)
        except:
            pass

if __name__ == "__main__":
    test_transient_dispatch()
    print("Integration Test Passed")

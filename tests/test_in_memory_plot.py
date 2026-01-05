import sys
import os
import pytest
import numpy as np
from io import BytesIO

# Add project root to path
sys.path.append(os.getcwd())

from backend.core.solver import plot_geometry, plot_temperature_map
from backend.core.mold_analysis import plot_mold_risk_map
from backend.core.simulation_engine import solve_scenario
from backend.core.declarative_geometry import DeclarativeGeometry

def test_plot_geometry_buffer():
    grid_map = np.zeros((100, 100), dtype=int)
    buf = plot_geometry(grid_map, 100, 100, filename=None)
    assert isinstance(buf, BytesIO)
    buf.seek(0)
    content = buf.read()
    assert len(content) > 0
    assert content.startswith(b'\x89PNG') # PNG signature

def test_plot_temperature_map_buffer():
    temp_grid = np.random.rand(100, 100) * 20.0
    buf = plot_temperature_map(temp_grid, 100, 100, filename=None, title="Test")
    assert isinstance(buf, BytesIO)
    buf.seek(0)
    assert buf.read().startswith(b'\x89PNG')

def test_plot_mold_risk_buffer():
    rh_grid = np.random.rand(100, 100)
    buf = plot_mold_risk_map(rh_grid, 100, 100, filename=None)
    assert isinstance(buf, BytesIO)
    buf.seek(0)
    assert buf.read().startswith(b'\x89PNG')

def test_solve_scenario_return_plot():
    # minimalist scenario matching one of the iso cases or simple custom
    scenario_def = {
        "name": "Test Scenario",
        "file_suffix": "test",
        "cfg": {
            "name": "Test",
            "canvas": {"bounds": [0, 500, 0, 500], "grid": 50},
            "elements": [
                {"type": "rect", "material": 2, "params": {"x": 0, "y": 0, "width": 500, "height": 500}}
            ],
            "variables": {"wall_thick": 360}
        }
    }
    
    # Run simulation
    results = solve_scenario(scenario_def, use_adaptive_mesh=False, return_plot_data=True)
    
    assert "plot_buffer" in results
    assert results["plot_buffer"] is not None
    assert isinstance(results["plot_buffer"], BytesIO)
    
    # Check no file was created
    assert not os.path.exists("result_Test Scenario.png")

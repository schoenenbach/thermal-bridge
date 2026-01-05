import pytest
import numpy as np
from backend.core.declarative_geometry import DeclarativeGeometry
from backend.core.mesh import UniformMesh
from backend.core.geometry import build_material_grid
from backend.core.solver import calculate_conductances_uniform, solve, calculate_thermal_results

def test_full_simulation_pipeline(solver_lib):
    """Run a minimal full simulation integration test."""
    # Simple geometry: 20x20 canvas, single material block
    data = {
        "name": "TestIntegration",
        "canvas": {"bounds": [0, 20, 0, 20], "grid": 2.0},
        "elements": [
            {
                "type": "rect", "name": "block",
                "material": 100, "lambda": 1.0,
                "params": {"x": 0, "y": 0, "width": 20, "height": 20}
            }
        ]
    }
    
    geom = DeclarativeGeometry(data)
    mesh = UniformMesh(geom, grid_size_mm=2.0)
    mesh.generate()
    
    grid_map, cond = build_material_grid(geom, mesh.xc, mesh.yc)
    Gh, Gv = calculate_conductances_uniform(cond)
    
    # Simple top-bottom gradient BC
    ny, nx = mesh.ny, mesh.nx
    mask = np.zeros((ny, nx), dtype=int)
    values = np.zeros((ny, nx))
    
    mask[0,:] = 1; values[0,:] = 0.0   # Bottom 0
    mask[-1,:] = 1; values[-1,:] = 20.0 # Top 20
    
    temp = np.zeros((ny, nx))
    temp[mask==1] = values[mask==1]
    
    # Solve
    temp = solve(temp, Gh, Gv, mask, values, max_iter=1000, verbose=False)
    
    # Check result
    # Middle row should be ~10.0 (Linear gradient 0->20)
    # Discrete mesh center might vary slightly (11.11 calculated previously due to cell center positions)
    mid_idx = ny // 2
    avg_mid = np.mean(temp[mid_idx, :])
    assert 9.0 < avg_mid < 12.0
    
    # Calculate thermal metrics (psi/fRsi placeholders)
    # Using dummy air mask (all interior?)
    mask_int = np.zeros((ny, nx), dtype=bool) 
    # Just check function runs without error
    results = calculate_thermal_results(
        temp, Gh, Gv, grid_map, mask_int, dx_m=0.002, rsi=0.13
    )
    
    assert "L2D" in results
    assert "fRsi" in results
    assert "MinT" in results

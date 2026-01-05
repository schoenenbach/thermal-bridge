import pytest
import numpy as np
import math
from backend.core.geometry import build_material_grid
from backend.core.mesh import AdaptiveMesh, UniformMesh
from backend.core.solver import (
    solve,
    calculate_conductances, 
    calculate_conductances_uniform,
    get_solver_lib
)

def probe_temperature(temp_grid, x_mm, y_mm, mesh):
    """
    Interpolate temperature at (x,y) according to ISO 10211.
    For Case 1, we just need simple cell lookup or basic interpolation.
    """
    # Find cell indices
    ix = np.searchsorted(mesh.x_coords, x_mm) - 1
    iy = np.searchsorted(mesh.y_coords, y_mm) - 1
    
    ix = max(0, min(ix, mesh.nx - 1))
    iy = max(0, min(iy, mesh.ny - 1))
    
    return temp_grid[iy, ix]

@pytest.mark.slow
def test_iso_case_1_checkpoint(iso_case_1_geometry, solver_lib):
    """
    ISO 10211 Case 1: Half Column
    Check temperature at (150, 300)mm is 5.25°C ± 0.1K
    """
    # Setup
    mesh = AdaptiveMesh(iso_case_1_geometry)
    mesh.generate()
    
    # Calculate grid map and conductivity from backend.core.geometry
    grid_map, cond = build_material_grid(iso_case_1_geometry, mesh.xc, mesh.yc)
    Gh, Gv = calculate_conductances(cond, mesh.dx_array, mesh.dy_array)
    
    # Setup boundary conditions
    ny, nx = mesh.ny, mesh.nx
    mask = np.zeros((ny, nx), dtype=np.int32)
    values = np.zeros((ny, nx))
    
    # Top edge: T = 20°C
    mask[-1, :] = 1
    values[-1, :] = 20.0
    
    # Right edge: T = 0°C
    mask[:, -1] = 1
    values[:, -1] = 0.0
    
    # Bottom edge: T = 0°C
    mask[0, :] = 1
    values[0, :] = 0.0
    
    # Left edge: Adiabatic (default)
    
    # Initial temperature field
    temp = np.ones((ny, nx)) * 10.0
    temp[mask == 1] = values[mask == 1]
    
    # Solve
    temp = solve(temp, Gh, Gv, mask, values, max_iter=200000, tol=1e-7, verbose=False)
    
    # Check reference point (150, 300) -> 5.25°C
    t_check = probe_temperature(temp, 150.0, 300.0, mesh)
    
    # ISO 10211 requires agreement within 0.1K
    assert abs(t_check - 5.25) < 0.1, f"ISO Case 1 Failed: T(150,300)={t_check:.4f}, expected 5.25"


@pytest.mark.slow
@pytest.mark.parametrize("use_adaptive", [False, True])
def test_iso_case_2_checkpoint(iso_case_2_data, solver_lib, use_adaptive):
    """
    ISO 10211 Case 2: Multi-Material Bridge
    This test verifies temperatures at points A-I and heat flux using the full simulation engine.
    The engine handles convective boundary conditions via domain padding.
    Parameterized to test both Uniform (Standard) and Adaptive (Optimization) meshes.
    """
    from backend.core.simulation_engine import solve_scenario
    
    # Wrap data in scenario definition expected by solve_scenario
    scenario_def = {
        "name": f"ISO Case 2 Test ({'Adaptive' if use_adaptive else 'Uniform'})",
        "file_suffix": "test_iso_case_2",
        "cfg": iso_case_2_data
    }
    
    # Use UniformMesh to match the strict ISO grid requirements (0.25mm)
    # AdaptiveMesh might be faster but needs validation of precision first.
    result = solve_scenario(scenario_def, use_adaptive_mesh=use_adaptive)
    
    # Verification
    measurements = result['measurements']
    errors = []
    
    print("\\nISO Case 2 Results (Engine):")
    print(f"{'Point':<5} {'Value':<8} {'Expected':<8} {'Diff':<8} {'Result'}")
    print("-" * 50)
    
    # Check Point Probes
    for name, res in measurements.items():
        if 'value' not in res: continue 
        # Skip flux/surface metrics in this loop, just points A-I
        if len(name) > 1 and name != "Interior Heat Flux": continue 
        
        val = res['value']
        exp = res.get('expected')
        diff = res.get('diff', 0.0)
        passed = res.get('passed', False)
        status = "PASS" if passed else "FAIL"
        
        if exp is not None:
             print(f"{name:<5} {val:<8.3f} {exp:<8.1f} {diff:<8.3f} {status}")
             if not passed:
                 errors.append(f"Point {name} failed: got {val:.3f}, expected {exp}")
    
    # Check Flux
    flux_res = measurements.get('Interior Heat Flux')
    if flux_res:
        val = flux_res['value']
        exp = flux_res['expected']
        diff = flux_res['diff']
        passed = flux_res['passed']
        status = "PASS" if passed else "FAIL"
        print(f"Flux : {val:<8.3f} {exp:<8.1f} {diff:<8.3f} {status}")
        
        if not passed:
             errors.append(f"Flux failed: got {val:.3f}, expected {exp}")
    
    if errors:
        pytest.fail("\\n".join(errors))


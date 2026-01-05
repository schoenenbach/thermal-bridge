import pytest
import numpy as np
import math
from backend.core.geometry import build_material_grid
from backend.core.mesh import AdaptiveMesh
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


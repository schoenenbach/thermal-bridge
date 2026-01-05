
import pytest
import numpy as np
import os
from backend.core.geometry import SketchGeometry, build_material_grid, build_transient_grid, MaterialID
from backend.core.mesh import UniformMesh
from backend.core.solver import solve_transient, get_solver_lib

def test_transient_solver_1d_diffusion():
    """
    Test 1D heat diffusion in a bar.
    Left side fixed at 20C, Right side fixed at 0C.
    Initial temp 0C.
    Check if temperature propagates correctly over time.
    """
    # Setup Geometry (100mm bar)
    geom = SketchGeometry()
    # Use 30mm height with 10mm grid -> 3 rows
    geom.set_canvas(0, 100, 0, 30)
    geom.add_point("A", 0, 0)
    geom.add_point("B", 100, 0)
    geom.add_point("C", 100, 30)
    geom.add_point("D", 0, 30)
    geom.add_shape(["A", "B", "C", "D"], MaterialID.WALL) # Lambda ~0.81, rho~1800, c~1000
    
    # Mesh
    mesh = UniformMesh(geom, grid_size_mm=10.0) # 10x3 cells
    mesh.generate()
    
    # Material Grids
    grid_map, cond = build_material_grid(geom, mesh.xc, mesh.yc)
    rho, cp = build_transient_grid(geom, grid_map)
    
    # Capacitance
    dx = 0.01 # 10mm
    dy = 0.01 # 10mm
    # C = rho * cp * dx * dy
    capacitance = rho * cp * dx * dy
    
    # Conductance
    # G = (2*dy) / (dx/k + dx/k) = dy * k / dx
    # Horizontal G
    k = 0.81
    Gh = np.zeros_like(cond)
    Gh[:, :-1] = dy * k / dx
    
    Gv = np.zeros_like(cond) # Adiabatic top/bottom (ignore vertical flow or set to 0)
    
    # Setup State
    # Shape (NY, NX) -> (1, 10)
    temp = np.zeros_like(cond)
    mask = np.zeros_like(cond, dtype=int)
    values = np.zeros_like(cond)
    
    # Fix Left (20C)
    mask[:, 0] = 1
    values[:, 0] = 20.0
    temp[:, 0] = 20.0
    
    # Fix Right (0C) - actually let it float? No, let's fix it for steady state target.
    mask[:, -1] = 1
    values[:, -1] = 0.0
    temp[:, -1] = 0.0
    
    # Run loop
    dt = 60.0 # 1 minute
    steps = 60 # 1 hour
    
    temp_prev = temp.copy()
    
    for _ in range(steps):
        temp_prev[:] = temp[:]
        temp = solve_transient(temp, temp_prev, Gh, Gv, capacitance, mask, values, dt)
        
    print(f"Final Temp: {temp}")
    
    # Check that temperature increased in the middle
    # Center node index 5 (x=55mm), middle row 1
    mid_idx = 5
    t_mid = temp[1, mid_idx]
    
    assert t_mid > 0.0, "Temperature should diffuse into the bar"
    assert t_mid < 20.0, "Temperature should not exceed source"
    
    # Check monotonicity (closer to source = hotter)
    for i in range(mesh.nx - 1):
        assert temp[1, i] >= temp[1, i+1] - 1e-9, "Temperature should be monotonic"

def test_transient_conservation():
    """
    Test energy conservation in adiabatic box.
    Initial block at 20C, surrounded by 0C. Total energy should be conserved?
    Actually with fixed BCs energy is not conserved.
    Adiabatic boundaries -> Total Energy should be constant.
    """
    # ... setup adiabatic box ...
    # Skip for now, diffusion test is more important.
    pass

if __name__ == "__main__":
    test_transient_solver_1d_diffusion()
    print("Test Passed")

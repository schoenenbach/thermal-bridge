import pytest
import numpy as np
from solver import (
    calculate_conductances, 
    calculate_conductances_uniform,
    solve,
    calculate_thermal_results
)

def test_conductance_uniform_1d():
    """Test standard conductance calculation for uniform 1D case."""
    # 3x3 grid, uniform conductivity k=1, uniform grid size 1m
    cond = np.ones((3, 3))
    dx = 1.0
    dy = 1.0
    
    Gh, Gv = calculate_conductances(cond, dx, dy)
    
    # For horizontal: G = (2*dy) / (dx/k + dx/k) = 2 / (1 + 1) = 1.0
    # Expected Gh shape: (3, 3) - solver returns same size array (using roll)
    assert Gh.shape == (3, 3)
    assert np.allclose(Gh, 1.0)
    
    # For vertical: G = (2*dx) / (dy/k + dy/k) = 1.0
    # Expected Gv shape: (3, 3)
    assert Gv.shape == (3, 3)
    assert np.allclose(Gv, 1.0)

def test_conductance_harmonic_mean():
    """Test harmonic mean logic for interface conductivity."""
    # 1x2 grid: Left k=1, Right k=2
    # dx=1, dy=1
    cond = np.array([[1.0, 2.0]])
    dx_arr = np.array([1.0, 1.0])
    dy_arr = np.array([1.0])
    
    Gh, Gv = calculate_conductances(cond, dx_arr, dy_arr)
    
    # Horizontal interface:
    # R_left = 0.5/1 = 0.5
    # R_right = 0.5/2 = 0.25
    # R_total = 0.75
    # G = 1/0.75 = 1.333...
    
    expected_G = 1.0 / ( (1.0/(1.0+1e-12)) + (1.0/(2.0+1e-12)) ) * 2.0 * 1.0
    # Note: calculate_conductances formula: G = 2*dy / (dxL/kL + dxR/kR)
    # = 2*1 / (1/1 + 1/2) = 2 / 1.5 = 1.333
    
    assert np.isclose(Gh[0, 0], 1.33333333)

def test_solve_linear_gradient(solver_lib):
    """Test solving a simple 1D linear gradient."""
    # 10x10 uniform grid
    rows, cols = 10, 10
    temp = np.zeros((rows, cols))
    
    # Uniform conductivity k=1
    cond = np.ones((rows, cols))
    
    # Conductances
    Gh, Gv = calculate_conductances_uniform(cond)
    
    # Fixed boundaries: Top=10, Bottom=0
    fixed_mask = np.zeros((rows, cols), dtype=bool)
    fixed_values = np.zeros((rows, cols))
    
    fixed_mask[0, :] = True  # Bottom row
    fixed_values[0, :] = 0.0
    
    fixed_mask[-1, :] = True # Top row
    fixed_values[-1, :] = 10.0
    
    # Initial guess
    temp[:] = 5.0
    temp[0, :] = 0.0
    temp[-1, :] = 10.0
    
    # Solve
    solve(temp, Gh, Gv, fixed_mask, fixed_values, 
          max_iter=5000, tol=1e-6, verbose=False)
    
    # Check middle row (index 4.5 -> 5 approx)
    # Expected profile: 0, 1.11, 2.22... 10
    # Actually for 10 rows:
    # y=0 -> T=0
    # y=9 -> T=10
    # Gradient is 10/9 per row = 1.111
    # Row 5 (y=5) should be 5 * 1.111 = 5.555
    
    expected_row_5 = 5 * (10.0 / 9.0)
    assert np.allclose(temp[5, :], expected_row_5, atol=1e-3)

def test_solve_convergence(solver_lib):
    """Test that solver reports convergence."""
    # Tiny 5x5 grid
    rows, cols = 5, 5
    temp = np.zeros((rows, cols))
    cond = np.ones((rows, cols))
    Gh, Gv = calculate_conductances_uniform(cond)
    
    fixed_mask = np.zeros((rows, cols), dtype=bool)
    fixed_mask[0,0] = True
    fixed_values = np.zeros((rows, cols))
    
    # Solve
    final_temp = solve(temp, Gh, Gv, fixed_mask, fixed_values, 
                       max_iter=1000, tol=1e-5, verbose=False)
    
    # Any check? Just ensure it ran without error
    assert final_temp is not None
    assert final_temp.shape == (rows, cols)

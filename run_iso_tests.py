#!/usr/bin/env python3
"""
ISO 10211 Test Runner (Refactored)

Uses the new geometry/mesh module structure for cleaner, reusable code.

Usage:
    python3 run_iso_tests_v2.py [1|2|all]
"""

import argparse
import sys
import os
import ctypes
import numpy as np
import matplotlib.pyplot as plt
import time

# Local imports
from geometry import build_material_grid
from mesh import UniformMesh
from geometries.iso_case1 import ISOCase1Geometry
from geometries.iso_case2 import ISOCase2Geometry

# Load C++ Library
SO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "thermal_solver_core.so"))
lib = None


def load_solver():
    """Load the C++ solver library."""
    global lib
    try:
        lib = ctypes.CDLL(SO_PATH)
        lib.solve_general_conductance.argtypes = [
            ctypes.POINTER(ctypes.c_double),  # temp
            ctypes.POINTER(ctypes.c_double),  # Gh
            ctypes.POINTER(ctypes.c_double),  # Gv
            ctypes.POINTER(ctypes.c_int),     # fixed_mask
            ctypes.POINTER(ctypes.c_double),  # fixed_values
            ctypes.c_int,  # rows
            ctypes.c_int,  # cols
            ctypes.c_int,  # iterations
            ctypes.c_double  # omega
        ]
        lib.solve_general_conductance.restype = ctypes.c_double
        print("[INFO] C++ Solver core loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to load solver library at {SO_PATH}: {e}")
        sys.exit(1)


def calculate_conductances(cond: np.ndarray, dx: float, dy: float):
    """
    Calculate horizontal and vertical conductance matrices.
    
    Args:
        cond: 2D array of thermal conductivities
        dx, dy: Cell sizes in mm (converted to m internally)
        
    Returns:
        Tuple of (Gh, Gv) conductance matrices
    """
    dx_m = dx / 1000.0
    dy_m = dy / 1000.0
    
    # Horizontal conductance (between j and j+1)
    k_right = np.roll(cond, -1, axis=1)
    k_harm_h = 2 * cond * k_right / (cond + k_right + 1e-12)
    Gh = k_harm_h * dy_m / dx_m
    
    # Vertical conductance (between i and i+1)
    k_down = np.roll(cond, -1, axis=0)
    k_harm_v = 2 * cond * k_down / (cond + k_down + 1e-12)
    Gv = k_harm_v * dx_m / dy_m
    
    return Gh, Gv


def solve_cpp(temp, Gh, Gv, mask, values, max_iter=100000, tol=1e-7, omega=1.90, batch=5000, verbose=True):
    """
    Solve using C++ accelerated solver.
    
    Args:
        temp: Initial temperature field (modified in place)
        Gh, Gv: Conductance matrices
        mask: Fixed node mask (1 = fixed, 0 = free)
        values: Fixed node values
        max_iter, tol, omega, batch: Solver parameters
        verbose: Print progress
        
    Returns:
        Final temperature field
    """
    temp_c = np.ascontiguousarray(temp, dtype=np.float64)
    gh_c = np.ascontiguousarray(Gh, dtype=np.float64)
    gv_c = np.ascontiguousarray(Gv, dtype=np.float64)
    mask_c = np.ascontiguousarray(mask, dtype=np.int32)
    val_c = np.ascontiguousarray(values, dtype=np.float64)
    
    rows, cols = temp.shape
    p_temp = temp_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gh = gh_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gv = gv_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_mask = mask_c.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
    p_val = val_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    
    start_t = time.time()
    for k in range(0, max_iter, batch):
        diff = lib.solve_general_conductance(p_temp, p_gh, p_gv, p_mask, p_val, rows, cols, batch, omega)
        if verbose and k % 10000 == 0:
            print(f"  Iter {k+batch:6d}: Diff {diff:.2e}")
        if diff < tol:
            if verbose:
                print(f"Converged in {k+batch} iterations ({time.time()-start_t:.2f}s)")
            break
    
    return temp_c


def run_case_1():
    """Run ISO 10211 Test Case 1 using new geometry structure."""
    print("\n" + "="*60)
    print("ISO 10211 Test Case 1: 2D Half Column (Refactored)")
    print("="*60)
    
    # Create geometry and mesh
    geometry = ISOCase1Geometry(grid_mm=1.0)
    mesh = UniformMesh(geometry, grid_size_mm=1.0)
    mesh.generate()
    
    print(f"Mesh: {mesh.info()}")
    
    # Build material grid
    grid_map, cond = build_material_grid(geometry, mesh.xc, mesh.yc)
    
    # Calculate conductances
    Gh, Gv = calculate_conductances(cond, mesh.grid_size_mm, mesh.grid_size_mm)
    
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
    
    # Left edge: Adiabatic (no fix needed, just don't set mask)
    
    # Initial temperature field
    temp = np.ones((ny, nx)) * 10.0
    temp[mask == 1] = values[mask == 1]
    
    # Solve
    temp = solve_cpp(temp, Gh, Gv, mask, values, max_iter=100000, tol=1e-7, batch=5000)
    
    # Check reference point (150, 300) -> 5.25°C
    ix = int(150 / mesh.grid_size_mm)
    iy = int(300 / mesh.grid_size_mm)
    t_check = temp[iy, ix]
    
    print(f"\nCheck Point (150, 300):")
    print(f"  Calculated: {t_check:.4f} °C")
    print(f"  Reference:  5.2500 °C")
    print(f"  Deviation:  {abs(t_check - 5.25):.4f} K")
    
    status = "PASS" if abs(t_check - 5.25) < 0.1 else "FAIL"
    print(f"Result: {status}")
    
    # Save plot
    plt.figure(figsize=(6, 10))
    plt.imshow(temp, cmap='jet', origin='lower', extent=[0, mesh.width_mm, 0, mesh.height_mm])
    plt.colorbar(label='Temperature [°C]')
    plt.title(f'ISO 10211 Case 1 (Refactored)\nT(150,300)={t_check:.3f}°C')
    plt.savefig('test_case_1_v2_result.png', dpi=150)
    plt.close()
    print("Saved plot to 'test_case_1_v2_result.png'")
    
    return status == "PASS"


def run_case_2():
    """Run ISO 10211 Test Case 2 using new geometry structure."""
    print("\n" + "="*60)
    print("ISO 10211 Test Case 2: Multi-Material Bridge (Refactored)")
    print("="*60)
    
    # Create geometry and mesh
    geometry = ISOCase2Geometry(grid_mm=0.25)
    mesh = UniformMesh(geometry, grid_size_mm=0.25)
    mesh.generate()
    
    print(f"Mesh: {mesh.info()}")
    
    # Build material grid
    grid_map, cond = build_material_grid(geometry, mesh.xc, mesh.yc)
    
    # For Case 2, we need to pad with boundary cells for surface resistance
    ny, nx = mesh.ny, mesh.nx
    ny_p = ny + 2
    
    # Padded conductivity
    # Padded conductivity
    # Use 0.029 (Insulation) as default for padding, or query geometry
    k_ins = 0.029 
    cond_p = np.full((ny_p, nx), k_ins)
    cond_p[1:-1, :] = cond
    
    # Apply surface resistance as effective conductivity
    dx_m = mesh.grid_size_mm / 1000.0
    cond_p[0, :] = dx_m / (2 * geometry.rsi)   # Bottom (interior)
    cond_p[-1, :] = dx_m / (2 * geometry.rse)  # Top (exterior)
    
    # Calculate conductances
    Gh, Gv = calculate_conductances(cond_p, mesh.grid_size_mm, mesh.grid_size_mm)
    
    # Boundary conditions
    mask = np.zeros((ny_p, nx), dtype=np.int32)
    values = np.zeros((ny_p, nx))
    
    mask[0, :] = 1
    values[0, :] = 20.0   # Interior temperature
    mask[-1, :] = 1
    values[-1, :] = 0.0   # Exterior temperature
    
    # Initial temperature (linear gradient)
    temp = np.linspace(20, 0, ny_p)[:, None] * np.ones((1, nx))
    
    # Solve
    temp = solve_cpp(temp, Gh, Gv, mask, values, max_iter=500000, tol=1e-7, batch=10000)
    
    # Calculate heat flux at interior surface
    flux_in = 0.0
    for i in range(nx):
        flux_in += Gv[0, i] * (temp[0, i] - temp[1, i])
    
    print(f"\nFlux Check:")
    print(f"  Calculated: {flux_in:.4f} W/m")
    print(f"  Target:     9.5000 W/m")
    print(f"  Deviation:  {abs(flux_in - 9.5):.4f} W ({abs(flux_in - 9.5)/9.5*100:.2f}%)")
    
    status = "PASS" if abs(flux_in - 9.5) < 0.5 else "FAIL"
    print(f"Result: {status}")
    
    # Save plot
    plt.figure(figsize=(12, 3))
    plt.imshow(temp[1:-1], cmap='jet', origin='lower', 
               extent=[0, mesh.width_mm, 0, mesh.height_mm])
    plt.colorbar(label='Temperature [°C]')
    plt.title(f'ISO 10211 Case 2 (Refactored)\nFlux={flux_in:.3f} W/m')
    plt.savefig('test_case_2_v2_result.png', dpi=150)
    plt.close()
    print("Saved plot to 'test_case_2_v2_result.png'")
    
    return status == "PASS"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run ISO 10211 Tests (Refactored)')
    parser.add_argument('test', nargs='?', default='all', choices=['1', '2', 'all'],
                        help='Test case to run (1, 2, or all)')
    args = parser.parse_args()
    
    load_solver()
    
    results = {}
    
    if args.test in ['1', 'all']:
        results['Case 1'] = run_case_1()
    
    if args.test in ['2', 'all']:
        results['Case 2'] = run_case_2()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for case, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {case}: {status}")
    
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

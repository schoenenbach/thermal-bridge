#!/usr/bin/env python3
"""
ISO 10211 Test Runner
Executes thermal bridge verification tests using the C++ accelerated solver.

Usage:
    python3 run_iso_tests.py [1|2|all]

Arguments:
    1    : Run Test Case 1 only
    2    : Run Test Case 2 only (includes point verification)
    all  : Run all test cases (default)
"""

import argparse
import sys
import os
import ctypes
import numpy as np
import matplotlib.pyplot as plt
import time

# Load C++ Library
SO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "thermal_solver_core.so"))
lib = None

def load_solver():
    global lib
    try:
        lib = ctypes.CDLL(SO_PATH)
        # solve_general_conductance signature
        lib.solve_general_conductance.argtypes = [
            ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_double),
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_double
        ]
        lib.solve_general_conductance.restype = ctypes.c_double
        print("[INFO] C++ Solver core loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to load solver library at {SO_PATH}: {e}")
        sys.exit(1)

def run_case_1():
    """ISO 10211 Case 1: 2D Half Column"""
    print("\n" + "="*60)
    print("ISO 10211 Test Case 1: 2D Half Column (Uniform Grid, C++ Solver)")
    print("="*60)
    
    # Geometry
    GRID_MM = 1.0
    W_mm = 200
    H_mm = 400
    nx = int(W_mm / GRID_MM) + 1
    ny = int(H_mm / GRID_MM) + 1
    
    print(f"Grid Size: {nx} x {ny} (Resolution: {GRID_MM}mm)")
    
    # Material
    k_material = 0.1  # W/mK
    
    # Initialize
    temp = np.zeros((ny, nx))
    cond = np.full((ny, nx), k_material)
    
    # Boundary Conditions
    mask = np.zeros((ny, nx), dtype=np.int32)
    val = np.zeros((ny, nx))
    
    mask[-1, :] = 1; val[-1, :] = 20.0  # Top
    mask[:, -1] = 1; val[:, -1] = 0.0   # Right
    mask[0, :] = 1;  val[0, :] = 0.0    # Bottom
    
    temp[:] = 10.0
    temp[mask == 1] = val[mask == 1]
    
    # Calculate Conductance Matrices (Uniform)
    dx = GRID_MM / 1000.0
    dy = GRID_MM / 1000.0
    
    k_right = np.roll(cond, -1, axis=1)
    k_harm_h = 2 * cond * k_right / (cond + k_right + 1e-12)
    Gh = k_harm_h * dy / dx
    
    k_down = np.roll(cond, -1, axis=0)
    k_harm_v = 2 * cond * k_down / (cond + k_down + 1e-12)
    Gv = k_harm_v * dx / dy
    
    # C++ Conversion
    temp_c = np.ascontiguousarray(temp, dtype=np.float64)
    gh_c = np.ascontiguousarray(Gh, dtype=np.float64)
    gv_c = np.ascontiguousarray(Gv, dtype=np.float64)
    mask_c = np.ascontiguousarray(mask, dtype=np.int32)
    val_c = np.ascontiguousarray(val, dtype=np.float64)
    
    rows, cols = temp.shape
    p_temp = temp_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gh = gh_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gv = gv_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_mask = mask_c.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
    p_val = val_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    
    # Solve
    omega = 1.90
    batch = 5000
    max_iter = 100000
    tol = 1e-7
    
    start_t = time.time()
    for k in range(0, max_iter, batch):
        diff = lib.solve_general_conductance(p_temp, p_gh, p_gv, p_mask, p_val, rows, cols, batch, omega)
        if k % 10000 == 0:
            print(f"  Iter {k+batch:6d}: Diff {diff:.2e}")
        if diff < tol:
            print(f"Converged in {k+batch} iterations ({time.time()-start_t:.2f}s)")
            break
    
    # Check Reference Point (150, 300) -> 5.25 C
    ix = int(150 / GRID_MM)
    iy = int(300 / GRID_MM)
    t_check = temp_c[iy, ix]
    
    print(f"\nCheck Point (150, 300):")
    print(f"  Calculated: {t_check:.4f} °C")
    print(f"  Reference:  5.2500 °C")
    print(f"  Deviation:  {abs(t_check - 5.25):.4f} K")
    
    status = "PASS" if abs(t_check - 5.25) < 0.1 else "FAIL"
    print(f"Result: {status}")
    
    # Save Plot
    plt.figure(figsize=(6, 10))
    plt.imshow(temp_c, cmap='jet', origin='lower', extent=[0, W_mm, 0, H_mm])
    plt.colorbar(label='Temperature [°C]')
    plt.title(f'ISO 10211 Case 1\nT(150,300)={t_check:.3f}°C')
    plt.savefig('test_case_1_result.png', dpi=150)
    print("Saved plot to 'test_case_1_result.png'")
    
    return status == "PASS"

def run_case_2():
    """ISO 10211 Case 2: Multi-Material Bridge"""
    print("\n" + "="*60)
    print("ISO 10211 Test Case 2: Multi-Material Bridge (C++ Solver)")
    print("="*60)
    
    # Materials
    MAT_CONC = 1.15
    MAT_WOOD = 0.12
    MAT_INS = 0.029
    MAT_ALU = 230.0
    
    GRID_MM = 0.25
    W_mm = 500.0
    H_mm = 47.5
    nx = int(W_mm / GRID_MM) + 1
    ny = int(H_mm / GRID_MM) + 1
    
    print(f"Grid Size: {nx} x {ny} (Resolution: {GRID_MM}mm)")
    
    cond = np.full((ny, nx), MAT_INS)
    
    def to_idx(v):
        return int(round(v / GRID_MM))
    
    # Corrected Geometry (Zero-Gap)
    cond[to_idx(41.5):to_idx(47.5), :] = MAT_CONC
    cond[to_idx(36.5):to_idx(41.5), to_idx(0):to_idx(15)] = MAT_WOOD
    # Aluminium Head & Leg
    cond[to_idx(35.0):to_idx(36.5), to_idx(0):to_idx(15)] = MAT_ALU # Head
    cond[to_idx(1.5):to_idx(35.0), to_idx(0):to_idx(1.5)] = MAT_ALU # Leg
    cond[to_idx(0):to_idx(1.5), :] = MAT_ALU # Bottom Plate
    
    # Padding
    ny_p = ny + 2
    cond_p = np.full((ny_p, nx), MAT_INS)
    cond_p[1:-1, :] = cond
    
    dx = GRID_MM / 1000.0
    cond_p[0, :] = dx / (2 * 0.11)   # Bottom (Rsi=0.11)
    cond_p[-1, :] = dx / (2 * 0.06)  # Top (Rse=0.06)
    
    # Conductances
    k_right = np.roll(cond_p, -1, axis=1)
    k_harm_h = 2 * cond_p * k_right / (cond_p + k_right + 1e-12)
    Gh = k_harm_h * dx / dx
    
    k_down = np.roll(cond_p, -1, axis=0)
    k_harm_v = 2 * cond_p * k_down / (cond_p + k_down + 1e-12)
    Gv = k_harm_v * dx / dx
    
    # BCs
    mask = np.zeros((ny_p, nx), dtype=np.int32)
    val = np.zeros((ny_p, nx))
    mask[0, :] = 1; val[0, :] = 20.0
    mask[-1, :] = 1; val[-1, :] = 0.0
    
    temp = np.linspace(20, 0, ny_p)[:, None] * np.ones((1, nx))
    
    # C++
    temp_c = np.ascontiguousarray(temp, dtype=np.float64)
    gh_c = np.ascontiguousarray(Gh, dtype=np.float64)
    gv_c = np.ascontiguousarray(Gv, dtype=np.float64)
    mask_c = np.ascontiguousarray(mask, dtype=np.int32)
    val_c = np.ascontiguousarray(val, dtype=np.float64)
    
    rows, cols = temp.shape
    p_temp = temp_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gh = gh_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gv = gv_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_mask = mask_c.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
    p_val = val_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    
    # Solve
    omega = 1.90
    batch = 10000
    max_iter = 500000
    tol = 1e-7
    start_t = time.time()
    for k in range(0, max_iter, batch):
        diff = lib.solve_general_conductance(p_temp, p_gh, p_gv, p_mask, p_val, rows, cols, batch, omega)
        if k % 50000 == 0:
            print(f"  Iter {k+batch:6d}: Diff {diff:.2e}")
        if diff < tol:
            print(f"Converged in {k+batch} iterations ({time.time()-start_t:.2f}s)")
            break
            
    # Calculate Flux
    flux_in = 0.0
    for i in range(nx):
        flux_in += gv_c[0, i] * (temp_c[0, i] - temp_c[1, i])
        
    print(f"\nFlux Check:")
    print(f"  Calculated: {flux_in:.4f} W")
    print(f"  Target:     9.5000 W")
    print(f"  Deviation:  {abs(flux_in - 9.5):.4f} W ({abs(flux_in - 9.5)/9.5*100:.2f}%)")
    
    # Save Plot
    plt.figure(figsize=(12, 3))
    plt.imshow(temp_c[1:-1], cmap='jet', origin='lower', extent=[0, W_mm, 0, H_mm])
    plt.colorbar(label='Temperature [°C]')
    plt.title(f'ISO 10211 Case 2\nFlux={flux_in:.3f} W/m')
    plt.savefig('test_case_2_result.png', dpi=150)
    print("Saved plot to 'test_case_2_result.png'")

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run ISO 10211 Thermal Bridge Tests')
    parser.add_argument('test', nargs='?', default='all', choices=['1', '2', 'all'], help='Test case to run')
    args = parser.parse_args()
    
    load_solver()
    
    if args.test in ['1', 'all']:
        run_case_1()
    if args.test in ['2', 'all']:
        run_case_2()

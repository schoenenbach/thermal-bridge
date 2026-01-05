#!/usr/bin/env python3
"""
ISO 10211 Test Runner

Uses the unified geometry/mesh/solver module structure for clean, reusable code.

Usage:
    python3 run_iso_tests.py [1|2|all]
"""

import argparse
import sys
import time
import numpy as np

# Local imports
from geometry import build_material_grid
from mesh import UniformMesh
from geometries.iso_case1 import ISOCase1Geometry
from geometries.iso_case2 import ISOCase2Geometry
from solver import (
    get_solver_lib,
    calculate_conductances_uniform,
    solve,
    plot_temperature_map
)


def calculate_conductances(cond, dx_mm, dy_mm):
    """Wrapper for uniform grid conductances with unit scaling."""
    dx_m = dx_mm / 1000.0
    dy_m = dy_mm / 1000.0
    Gh, Gv = calculate_conductances_uniform(cond)
    # Scale by geometric factor for non-unity dx/dy
    return Gh * dy_m / dx_m, Gv * dx_m / dy_m


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
    temp = solve(temp, Gh, Gv, mask, values, max_iter=100000, tol=1e-7, batch_size=5000)
    
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
    plot_temperature_map(
        temp_grid=temp,
        width_mm=mesh.width_mm,
        height_mm=mesh.height_mm,
        filename='test_case_1_v2_result.png',
        title=f'ISO 10211 Case 1 (Refactored)\nT(150,300)={t_check:.3f}°C',
        grid_size_mm=mesh.grid_size_mm
    )
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
    temp = solve(temp, Gh, Gv, mask, values, max_iter=500000, tol=1e-7, batch_size=10000)
    
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
    # Exclude boundary cells for plotting
    plot_temperature_map(
        temp_grid=temp[1:-1],
        width_mm=mesh.width_mm,
        height_mm=mesh.height_mm,
        filename='test_case_2_v2_result.png',
        title=f'ISO 10211 Case 2 (Refactored)\nFlux={flux_in:.3f} W/m',
        grid_size_mm=mesh.grid_size_mm
    )
    print("Saved plot to 'test_case_2_v2_result.png'")
    
    return status == "PASS"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run ISO 10211 Tests (Refactored)')
    parser.add_argument('test', nargs='?', default='all', choices=['1', '2', 'all'],
                        help='Test case to run (1, 2, or all)')
    args = parser.parse_args()
    
    # Initialize solver (lazy loading handled by get_solver_lib)
    get_solver_lib()
    
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

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
from mesh import UniformMesh, AdaptiveMesh
from geometries.iso_case1 import ISOCase1Geometry
from geometries.iso_case2 import ISOCase2Geometry
from solver import (
    get_solver_lib,
    solve,
    plot_temperature_map
)


def calculate_conductances(cond, dx_in, dy_in):
    """Wrapper for conductance calculation using updated solver logic."""
    ny, nx = cond.shape
    
    if np.isscalar(dx_in) or np.ndim(dx_in) == 0:
        dx_array = np.full(nx, float(dx_in))
    else:
        dx_array = np.array(dx_in, dtype=float)
        
    if np.isscalar(dy_in) or np.ndim(dy_in) == 0:
        dy_array = np.full(ny, float(dy_in))
    else:
        dy_array = np.array(dy_in, dtype=float)
    
    # Use the robust general calculator
    from solver import calculate_conductances as calc_general
    return calc_general(cond, dx_array, dy_array)


def run_case_1(use_adaptive=False):
    """Run ISO 10211 Test Case 1 using new geometry structure."""
    print("\n" + "="*60)
    print("ISO 10211 Test Case 1: 2D Half Column (Refactored)")
    if use_adaptive:
        print("Mesh Type: AdaptiveMesh")
    else:
        print("Mesh Type: UniformMesh")
    print("="*60)
    
    # Create geometry and mesh
    geometry = ISOCase1Geometry(grid_mm=1.0)
    
    if use_adaptive:
        mesh = AdaptiveMesh(geometry)
    else:
        mesh = UniformMesh(geometry, grid_size_mm=1.0)
        
    mesh.generate()
    
    print(f"Mesh: {mesh.info()}")
    
    # Build material grid
    grid_map, cond = build_material_grid(geometry, mesh.xc, mesh.yc)
    
    # Calculate conductances
    # Pass 1D arrays to solver
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
    
    # Left edge: Adiabatic
    
    # Initial temperature field
    temp = np.ones((ny, nx)) * 10.0
    temp[mask == 1] = values[mask == 1]
    
    # Solve
    temp = solve(temp, Gh, Gv, mask, values, max_iter=100000, tol=1e-7, batch_size=5000)
    
    # Check reference point (150, 300) -> 5.25°C
    x_target = 150.0
    y_target = 300.0
    
    if use_adaptive:
        # Search for cell index
        # x_coords is face coords. cell i is [x[i], x[i+1]]
        ix = np.searchsorted(mesh.x_coords, x_target, side='right') - 1
        iy = np.searchsorted(mesh.y_coords, y_target, side='right') - 1
        ix = max(0, min(ix, mesh.nx - 1))
        iy = max(0, min(iy, mesh.ny - 1))
    else:
        ix = int(x_target / mesh.grid_size_mm)
        iy = int(y_target / mesh.grid_size_mm)
        
    t_check = temp[iy, ix]
    
    print(f"\nCheck Point (150, 300):")
    print(f"  Calculated: {t_check:.4f} °C")
    print(f"  Reference:  5.2500 °C")
    print(f"  Deviation:  {abs(t_check - 5.25):.4f} K")
    
    status = "PASS" if abs(t_check - 5.25) < 0.1 else "FAIL"
    print(f"Result: {status}")
    
    # Save plot
    grid_sz = mesh.grid_size_mm if not use_adaptive else None
    plot_temperature_map(
        temp_grid=temp,
        width_mm=mesh.width_mm,
        height_mm=mesh.height_mm,
        filename='test_case_1_result.png',
        title=f'ISO 10211 Case 1 ({type(mesh).__name__})\nT(150,300)={t_check:.3f}°C',
        grid_size_mm=grid_sz,
        x_coords=mesh.x_coords if use_adaptive else None,
        y_coords=mesh.y_coords if use_adaptive else None
    )
    print("Saved plot to 'test_case_1_result.png'")
    
    return status == "PASS"


def run_case_2(use_adaptive=False):
    """Run ISO 10211 Test Case 2 using new geometry structure."""
    print("\n" + "="*60)
    print("ISO 10211 Test Case 2: Multi-Material Bridge (Refactored)")
    if use_adaptive:
        print("Mesh Type: AdaptiveMesh")
    else:
        print("Mesh Type: UniformMesh")
    print("="*60)
    
    # Create geometry and mesh
    geometry = ISOCase2Geometry(grid_mm=0.25)
    
    if use_adaptive:
        mesh = AdaptiveMesh(geometry)
    else:
        mesh = UniformMesh(geometry, grid_size_mm=0.25)
        
    mesh.generate()
    
    print(f"Mesh: {mesh.info()}")
    
    # Build material grid
    grid_map, cond = build_material_grid(geometry, mesh.xc, mesh.yc)
    
    # Setup Padded Domain for Surface Resistance (Case 2 specific approach)
    # We add one row top and bottom to represent "Air Nodes".
    # Solver operates on (NY+2, NX).
    
    ny, nx = mesh.ny, mesh.nx
    ny_p = ny + 2
    
    # Padded arrays
    # dx is same for all rows (rectilinear)
    dx_array = mesh.dx_array # size nx
    
    # dy needs padding
    dy_array = mesh.dy_array # size ny
    dy_p = np.zeros(ny_p)
    dy_p[1:-1] = dy_array
    dy_p[0] = 1.0 # arbitrary dummy height for air node
    dy_p[-1] = 1.0 # arbitrary dummy height for air node
    
    # Conductivity padding (internal)
    cond_p = np.zeros((ny_p, nx))
    cond_p[1:-1, :] = cond
    # Rows 0 and -1 are air, k doesn't matter if we overwrite Gv, but set to something safe
    cond_p[0, :] = 0.029
    cond_p[-1, :] = 0.029
    
    # Calculate Base Conductances
    Gh_p, Gv_p = calculate_conductances(cond_p, dx_array, dy_p)
    
    # Explicitly Overwrite Boundary Conductances for Robustness (Adaptive & Uniform)
    # Bottom Boundary (Row 0 -> Row 1): Surface Resistance RSI
    # Row 0 is Air (20C), Row 1 is Interior Surface.
    # Link index 0 in Gv connects row 0 and row 1.
    # G = Area / R = (dx * 1) / RSI
    dx_m = dx_array / 1000.0
    Gv_p[0, :] = dx_m / geometry.rsi
    
    # Top Boundary (Row NY -> Row NY+1): Surface Resistance RSE
    # Row NY is Exterior Surface, Row NY+1 is Air (0C).
    # Link index NY connects row NY and row NY+1.
    # In 0-indexed array of size (NY+2, NX), last row index is NY+1.
    # Gv has size (ny_p, nx). Valid links 0..ny_p-2.
    # We want link connecting index (ny_p-2) and (ny_p-1).
    # That is index ny_p-2.
    Gv_p[ny_p-2, :] = dx_m / geometry.rse
    
    # Disable lateral flow in air layers to prevent short circuits
    Gh_p[0, :] = 0.0
    Gh_p[-1, :] = 0.0
    
    # Boundary Conditions
    mask = np.zeros((ny_p, nx), dtype=np.int32)
    values = np.zeros((ny_p, nx))
    
    mask[0, :] = 1
    values[0, :] = 20.0   # Interior Air
    mask[-1, :] = 1
    values[-1, :] = 0.0   # Exterior Air
    
    # Initial temperature (linear gradient)
    temp = np.linspace(20, 0, ny_p)[:, None] * np.ones((1, nx))
    
    # Solve
    temp = solve(temp, Gh_p, Gv_p, mask, values, max_iter=500000, tol=1e-7, batch_size=10000)
    
    # Calculate heat flux at interior surface (Link 0)
    flux_in = 0.0
    for i in range(nx):
        flux_in += Gv_p[0, i] * (temp[0, i] - temp[1, i])
    
    print(f"\nFlux Check:")
    print(f"  Calculated: {flux_in:.4f} W/m")
    print(f"  Target:     9.5000 W/m")
    print(f"  Deviation:  {abs(flux_in - 9.5):.4f} W ({abs(flux_in - 9.5)/9.5*100:.2f}%)")
    
    status = "PASS" if abs(flux_in - 9.5) < 0.5 else "FAIL"
    print(f"Result: {status}")
    
    # Save plot
    grid_sz = mesh.grid_size_mm if not use_adaptive else None
    plot_temperature_map(
        temp_grid=temp[1:-1], # Exclude padding
        width_mm=mesh.width_mm,
        height_mm=mesh.height_mm,
        filename='test_case_2_result.png',
        title=f'ISO 10211 Case 2 ({type(mesh).__name__})\nFlux={flux_in:.3f} W/m',
        grid_size_mm=grid_sz,
        x_coords=mesh.x_coords if use_adaptive else None,
        y_coords=mesh.y_coords if use_adaptive else None
    )
    print("Saved plot to 'test_case_2_result.png'")
    
    return status == "PASS"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run ISO 10211 Tests (Refactored)')
    parser.add_argument('test', nargs='?', default='all', choices=['1', '2', 'all'],
                        help='Test case to run (1, 2, or all)')
    parser.add_argument('--mesh', default='uniform', choices=['uniform', 'adaptive'],
                        help='Mesh type to use (default: uniform)')
    args = parser.parse_args()
    
    # Initialize solver (lazy loading handled by get_solver_lib)
    get_solver_lib()
    
    use_adaptive = (args.mesh == 'adaptive')
    
    results = {}
    
    if args.test in ['1', 'all']:
        results['Case 1'] = run_case_1(use_adaptive=use_adaptive)
    
    if args.test in ['2', 'all']:
        results['Case 2'] = run_case_2(use_adaptive=use_adaptive)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for case, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {case}: {status}")
    
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

#!/usr/bin/env python3
"""
ISO 10211 Test Runner

Uses the unified geometry/mesh/solver module structure for clean, reusable code.

Usage:
    python3 run_iso_tests.py [1|2|all]
"""

import yaml
import os
import sys
import numpy as np

# Local imports
from geometry import build_material_grid
from mesh import UniformMesh, AdaptiveMesh
from declarative_geometry import DeclarativeGeometry
from solver import (
    get_solver_lib,
    solve,
    plot_temperature_map,
    plot_geometry
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
    print("ISO 10211 Test Case 1: 2D Half Column (YAML)")
    if use_adaptive:
        print("Mesh Type: AdaptiveMesh")
    else:
        print("Mesh Type: UniformMesh")
    print("="*60)
    
    # Load YAML
    fpath = os.path.abspath("scenarios/iso_case_1.yaml")
    with open(fpath, 'r') as f:
        data = yaml.safe_load(f)
    geometry = DeclarativeGeometry(data)
    
    # Extract grid size from geometry
    grid_mm = geometry.get_canvas_config().default_dx_mm
    
    if use_adaptive:
        mesh = AdaptiveMesh(geometry)
    else:
        mesh = UniformMesh(geometry, grid_size_mm=grid_mm)
        
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



def probe_temperature(mesh, temp_padded, cond, x, y):
    """
    Probe temperature at (x, y) according to ISO 10211 rules.
    
    - If point is within a cell, return cell temperature.
    - If point is on a boundary between cells, return weighted average:
      T = (sum(lambda_i * T_i / s_i)) / (sum(lambda_i / s_i))
      where s_i is distance from cell center to point.
      
    Args:
        mesh: The mesh object (uniform or adaptive)
        temp_padded: Temperature array (NY+2, NX) including air layers
        cond: Conductivity array (NY, NX)
        x: x coordinate in mm
        y: y coordinate in mm
        
    Returns:
        float: Calculated temperature
    """
    # Find potential neighbor cells
    # We use searchsorted to find where x/y falls in terms of faces
    
    eps = 1e-5
    
    # Candidates are any cell i where x_coords[i] <= x <= x_coords[i+1]
    # This automatically covers boundaries (equality).
    
    col_candidates = []
    for i in range(mesh.nx):
        if mesh.x_coords[i] <= x + eps and mesh.x_coords[i+1] >= x - eps:
            col_candidates.append(i)
            
    row_candidates = []
    for j in range(mesh.ny):
        if mesh.y_coords[j] <= y + eps and mesh.y_coords[j+1] >= y - eps:
            row_candidates.append(j)
            
    # Collect contributing cells
    weighted_sum = 0.0
    weight_sum = 0.0
    
    found_cells = 0
    
    for i in col_candidates:
        for j in row_candidates:
            # Get cell center
            xc = (mesh.x_coords[i] + mesh.x_coords[i+1]) / 2.0
            yc = (mesh.y_coords[j] + mesh.y_coords[j+1]) / 2.0
            
            # Distance s_i
            s = np.sqrt((x - xc)**2 + (y - yc)**2)
            
            if s < 1e-9:
                return temp_padded[j+1, i] # Direct hit on center (unlikely)
            
            lam = cond[j, i]
            # Use temp from padded array (j maps to j+1)
            t_cell = temp_padded[j+1, i]
            
            w = lam / s
            
            weighted_sum += w * t_cell
            weight_sum += w
            found_cells += 1
            
    if found_cells == 0:
        print(f"WARNING: No cells found for probe at ({x}, {y})")
        return 0.0
        
    return weighted_sum / weight_sum


def run_case_2(use_adaptive=False):
    """Run ISO 10211 Test Case 2 using new geometry structure."""
    print("\n" + "="*60)
    print("ISO 10211 Test Case 2: Multi-Material Bridge (YAML)")
    if use_adaptive:
        print("Mesh Type: AdaptiveMesh")
    else:
        print("Mesh Type: UniformMesh")
    print("="*60)
    
    # Load YAML
    fpath = os.path.abspath("scenarios/iso_case_2.yaml")
    with open(fpath, 'r') as f:
        data = yaml.safe_load(f)
    geometry = DeclarativeGeometry(data)
    
    # Extract RSi/RSe from YAML data
    rsi = 0.11
    rse = 0.06
    try:
        bcs = data.get('boundary_conditions', {})
        conv = bcs.get('convective', {})
        if 'bottom' in conv:
            rsi = float(conv['bottom']['R'])
        if 'top' in conv:
            rse = float(conv['top']['R'])
    except Exception as e:
        print(f"[WARNING] Could not parse RSI/RSE from YAML, using defaults: {e}")
        
    # Extract grid size from geometry
    grid_mm = geometry.get_canvas_config().default_dx_mm
    
    if use_adaptive:
        mesh = AdaptiveMesh(geometry)
    else:
        mesh = UniformMesh(geometry, grid_size_mm=grid_mm)
        
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
    Gv_p[0, :] = dx_m / rsi
    
    # Top Boundary (Row NY -> Row NY+1): Surface Resistance RSE
    # Row NY is Exterior Surface, Row NY+1 is Air (0C).
    # Link index NY connects row NY and row NY+1.
    # In 0-indexed array of size (NY+2, NX), last row index is NY+1.
    # Gv has size (ny_p, nx). Valid links 0..ny_p-2.
    # We want link connecting index (ny_p-2) and (ny_p-1).
    # That is index ny_p-2.
    Gv_p[ny_p-2, :] = dx_m / rse
    
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
    
    flux_passed = abs(flux_in - 9.5) < 0.5
    if not flux_passed:
         print(f"  -> FLUX FAIL (Diff: {abs(flux_in - 9.5):.4f})")
    
    # Checkpoints A-I
    # Coordinates in mm
    checkpoints = [
        ('A', 0.0,   47.5, 7.1),
        ('B', 500.0, 47.5, 0.8),
        ('C', 0.0,   41.5, 7.9),
        ('D', 15.0,  41.5, 6.3),
        ('E', 500.0, 41.5, 0.8),
        ('F', 0.0,   36.5, 16.4),
        ('G', 15.0,  36.5, 16.3),
        ('H', 0.0,   0.0,  16.8),
        ('I', 500.0, 0.0,  18.3),
    ]
    
    print("\nCheckpoint Temperatures:")
    print(f"  {'Point':<5} {'Coords (mm)':<15} {'Calc':<10} {'Ref':<10} {'Diff':<10} {'Status'}")
    print("-" * 75)
    
    points_passed = True
    max_diff = 0.0
    
    for name, x, y, ref in checkpoints:
        t_val = probe_temperature(mesh, temp, cond, x, y)
        diff = abs(t_val - ref)
        max_diff = max(max_diff, diff)
        
        status = "OK" if diff <= 0.1 else "FAIL" 
        if status == "FAIL":
            points_passed = False
            
        print(f"  {name:<5} ({x:>5.1f}, {y:>4.1f})   {t_val:>7.2f} °C  {ref:>7.2f} °C  {diff:>7.2f} K  {status}")
        
    print("-" * 75)
    print(f"Max Deviation: {max_diff:.4f} K")
    
    overall_status = "PASS" if (flux_passed and points_passed) else "FAIL"
    print(f"Result: {overall_status}")
    
    # Save plot
    grid_sz = mesh.grid_size_mm if not use_adaptive else None
    plot_temperature_map(
        temp_grid=temp[1:-1], # Exclude padding
        width_mm=mesh.width_mm,
        height_mm=mesh.height_mm,
        filename='test_case_2_result.png',
        title=f'ISO 10211 Case 2 ({type(mesh).__name__})\nFlux={flux_in:.3f} W/m, MaxDiff={max_diff:.2f}K',
        grid_size_mm=grid_sz,
        x_coords=mesh.x_coords if use_adaptive else None,
        y_coords=mesh.y_coords if use_adaptive else None
    )
    print("Saved plot to 'test_case_2_result.png'")
    
    return overall_status == "PASS"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run ISO 10211 Tests (Refactored)')
    parser.add_argument('test', nargs='?', default='all', choices=['1', '2', 'all'],
                        help='Test case to run (1, 2, or all)')
    parser.add_argument('--mesh', default='adaptive', choices=['uniform', 'adaptive'],
                        help='Mesh type to use (default: adaptive)')
    parser.add_argument('--geometry-only', action='store_true',
                        help='Generate geometry plots only, skip simulation')
    parser.add_argument('--equal-aspect', action='store_true',
                        help='Use equal aspect ratio for geometry plots (shows true proportions)')
    args = parser.parse_args()
    
    use_adaptive = (args.mesh == 'adaptive')
    
    if args.geometry_only:
        # Generate geometry plots only
        print("Generating geometry plots for ISO cases...")
        
        if args.test in ['1', 'all']:
            fpath = os.path.abspath("scenarios/iso_case_1.yaml")
            with open(fpath, 'r') as f:
                data = yaml.safe_load(f)
            geom = DeclarativeGeometry(data)
            mesh = AdaptiveMesh(geom) if use_adaptive else UniformMesh(geom, grid_size_mm=geom.get_canvas_config().default_dx_mm)
            mesh.generate()
            grid_map, _ = build_material_grid(geom, mesh.xc, mesh.yc)
            plot_geometry(grid_map, mesh.width_mm, mesh.height_mm, 
                         filename='geometry_iso_case_1.png',
                         x_coords=mesh.x_coords, y_coords=mesh.y_coords,
                         equal_aspect=args.equal_aspect)
            print("  Saved geometry_iso_case_1.png")
            
        if args.test in ['2', 'all']:
            fpath = os.path.abspath("scenarios/iso_case_2.yaml")
            with open(fpath, 'r') as f:
                data = yaml.safe_load(f)
            geom = DeclarativeGeometry(data)
            mesh = AdaptiveMesh(geom) if use_adaptive else UniformMesh(geom, grid_size_mm=geom.get_canvas_config().default_dx_mm)
            mesh.generate()
            grid_map, _ = build_material_grid(geom, mesh.xc, mesh.yc)
            plot_geometry(grid_map, mesh.width_mm, mesh.height_mm, 
                         filename='geometry_iso_case_2.png',
                         x_coords=mesh.x_coords, y_coords=mesh.y_coords,
                         equal_aspect=args.equal_aspect)
            print("  Saved geometry_iso_case_2.png")
            
        sys.exit(0)
    
    # Initialize solver (lazy loading handled by get_solver_lib)
    get_solver_lib()
    
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

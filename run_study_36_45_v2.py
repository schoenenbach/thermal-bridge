#!/usr/bin/env python3
"""
6-Case Study Script (Refactored)

Uses the new geometry/mesh module structure for cleaner, more maintainable code.
Runs thermal bridge calculations for:
- 2 wall thicknesses: 360mm, 450mm
- 3 insulation scenarios: None, External only, Full (with reveal insulation)

Usage:
    python3 run_study_36_45_v2.py [--geometry-only]
"""

import os
import sys
import argparse
import ctypes
import time
import numpy as np
import matplotlib.pyplot as plt

from config import CalculationConfig, SpacerType, TEMP_INT, TEMP_EXT, RSI_WALL, RSE
from geometry import build_material_grid, MaterialID
from mesh import AdaptiveMesh
from geometries.window_reveal import WindowRevealGeometry

# Load C++ Solver
SO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "thermal_solver_core.so"))
lib = ctypes.CDLL(SO_PATH)
lib.solve_general_conductance.argtypes = [
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_double),
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_double
]
lib.solve_general_conductance.restype = ctypes.c_double


def get_study_configs():
    """Define the 6 study configurations."""
    # Common Parameters
    TAPER_LEN = 150
    INS_MAX = 200
    INS_MIN = 100
    REVEAL_INS = 30
    GRID = 2.5  # mm (matching config default)
    
    configs = []
    
    # Scenario 1: No Insulation
    configs.append({
        "name": "Wall 360mm (No Ins)",
        "wall_desc": "360mm",
        "ins_desc": "None",
        "spacer_desc": "Swiss",
        "cfg": CalculationConfig(
            wall_thickness_mm=360,
            insulation_thick_max_mm=0,
            insulation_thick_min_mm=0,
            reveal_insulation_mm=0,
            taper_length_mm=0,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=True,
            grid_size_mm=GRID,
            spacer_type=SpacerType.SWISS_ULTIMATE
        )
    })
    
    configs.append({
        "name": "Wall 450mm (No Ins)",
        "wall_desc": "450mm",
        "ins_desc": "None",
        "spacer_desc": "Swiss",
        "cfg": CalculationConfig(
            wall_thickness_mm=450,
            insulation_thick_max_mm=0,
            insulation_thick_min_mm=0,
            reveal_insulation_mm=0,
            taper_length_mm=0,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=True,
            grid_size_mm=GRID,
            spacer_type=SpacerType.SWISS_ULTIMATE
        )
    })
    
    # Scenario 2: External Insulation + Taper (No Reveal Ins)
    configs.append({
        "name": "Wall 360mm (No Rev Ins)",
        "wall_desc": "360mm",
        "ins_desc": "200→100 mm",
        "spacer_desc": "Swiss",
        "cfg": CalculationConfig(
            wall_thickness_mm=360,
            insulation_thick_max_mm=INS_MAX,
            insulation_thick_min_mm=INS_MIN,
            reveal_insulation_mm=0,
            taper_length_mm=TAPER_LEN,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=True,
            grid_size_mm=GRID,
            spacer_type=SpacerType.SWISS_ULTIMATE
        )
    })
    
    configs.append({
        "name": "Wall 450mm (No Rev Ins)",
        "wall_desc": "450mm",
        "ins_desc": "200→100 mm",
        "spacer_desc": "Swiss",
        "cfg": CalculationConfig(
            wall_thickness_mm=450,
            insulation_thick_max_mm=INS_MAX,
            insulation_thick_min_mm=INS_MIN,
            reveal_insulation_mm=0,
            taper_length_mm=TAPER_LEN,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=True,
            grid_size_mm=GRID,
            spacer_type=SpacerType.SWISS_ULTIMATE
        )
    })
    
    # Scenario 3: Full Insulation (External + Reveal)
    configs.append({
        "name": "Wall 360mm (Full)",
        "wall_desc": "360mm",
        "ins_desc": "200→100 mm + 30mm reveal",
        "spacer_desc": "Swiss",
        "cfg": CalculationConfig(
            wall_thickness_mm=360,
            insulation_thick_max_mm=INS_MAX,
            insulation_thick_min_mm=INS_MIN,
            reveal_insulation_mm=REVEAL_INS,
            taper_length_mm=TAPER_LEN,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=False,
            grid_size_mm=GRID,
            spacer_type=SpacerType.SWISS_ULTIMATE
        )
    })
    
    configs.append({
        "name": "Wall 450mm (Full)",
        "wall_desc": "450mm",
        "ins_desc": "200→100 mm + 30mm reveal",
        "spacer_desc": "Swiss",
        "cfg": CalculationConfig(
            wall_thickness_mm=450,
            insulation_thick_max_mm=INS_MAX,
            insulation_thick_min_mm=INS_MIN,
            reveal_insulation_mm=REVEAL_INS,
            taper_length_mm=TAPER_LEN,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=False,
            grid_size_mm=GRID,
            spacer_type=SpacerType.SWISS_ULTIMATE
        )
    })
    
    return configs


def assign_exterior_air(grid_map: np.ndarray, cond: np.ndarray):
    """Assign exterior air to cells right of the last solid material."""
    ny, nx = grid_map.shape
    for i in range(ny):
        row = grid_map[i, :]
        solids = np.where(row > 1)[0]
        if solids.size > 0:
            last = solids[-1]
            grid_map[i, last+1:] = MaterialID.AIR_EXT
            cond[i, last+1:] = 0.025


def calculate_conductances_adaptive(cond, dx_array, dy_array):
    """Calculate conductances for non-uniform grid."""
    ny, nx = cond.shape
    dx_m = dx_array / 1000.0
    dy_m = dy_array / 1000.0
    
    # Horizontal
    k_right = np.roll(cond, -1, axis=1)
    k_harm_h = 2 * cond * k_right / (cond + k_right + 1e-12)
    dx_dist_h = np.zeros(nx)
    dx_dist_h[:-1] = (dx_m[:-1] + dx_m[1:]) / 2
    dx_dist_h[-1] = dx_m[-1]
    Gh = k_harm_h * dy_m[:, None] / dx_dist_h[None, :]
    
    # Vertical
    k_down = np.roll(cond, -1, axis=0)
    k_harm_v = 2 * cond * k_down / (cond + k_down + 1e-12)
    dy_dist_v = np.zeros(ny)
    dy_dist_v[:-1] = (dy_m[:-1] + dy_m[1:]) / 2
    dy_dist_v[-1] = dy_m[-1]
    Gv = k_harm_v * dx_m[None, :] / dy_dist_v[:, None]
    
    return Gh, Gv


def solve_thermal(geometry, mesh, rsi_value=0.13, max_iter=20000, tol=1e-5):
    """
    Run thermal solver for given geometry and mesh.
    
    Returns:
        dict with temperature field and calculation results
    """
    # Build material grid
    grid_map, cond = build_material_grid(geometry, mesh.xc, mesh.yc)
    assign_exterior_air(grid_map, cond)
    
    # Apply surface resistance
    mask_int = grid_map == MaterialID.AIR_INT
    mask_ext = grid_map == MaterialID.AIR_EXT
    
    k_eff_int = mesh.dx_array / (2 * rsi_value)
    k_eff_ext = mesh.dx_array / (2 * RSE)
    
    for j in range(mesh.nx):
        cond[mask_int[:, j], j] = k_eff_int[j]
        cond[mask_ext[:, j], j] = k_eff_ext[j]
    
    # Conductances
    Gh, Gv = calculate_conductances_adaptive(cond, mesh.dx_array, mesh.dy_array)
    
    # Boundary conditions
    fixed_mask = (mask_int | mask_ext).astype(np.int32)
    fixed_values = np.zeros_like(cond)
    fixed_values[mask_int] = TEMP_INT
    fixed_values[mask_ext] = TEMP_EXT
    
    # Initial temperature
    temp = np.ones_like(cond) * TEMP_INT
    temp[mask_ext] = TEMP_EXT
    
    # C++ solve
    temp_c = np.ascontiguousarray(temp, dtype=np.float64)
    gh_c = np.ascontiguousarray(Gh, dtype=np.float64)
    gv_c = np.ascontiguousarray(Gv, dtype=np.float64)
    mask_c = np.ascontiguousarray(fixed_mask, dtype=np.int32)
    val_c = np.ascontiguousarray(fixed_values, dtype=np.float64)
    
    rows, cols = temp.shape
    p_temp = temp_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gh = gh_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gv = gv_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_mask = mask_c.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
    p_val = val_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    
    omega = 1.85
    batch = 5000
    
    for k in range(0, max_iter, batch):
        diff = lib.solve_general_conductance(p_temp, p_gh, p_gv, p_mask, p_val, rows, cols, batch, omega)
        if diff < tol:
            break
    
    return {
        'temp': temp_c,
        'grid_map': grid_map,
        'cond': cond,
        'Gh': gh_c,
        'Gv': gv_c,
        'mask_int': mask_int,
        'mask_ext': mask_ext,
        'mesh': mesh,
        'rsi': rsi_value,
    }


def calculate_psi_from_result(result, geometry):
    """Calculate Psi-value and surface temperatures from solver result."""
    temp = result['temp']
    Gh = result['Gh']
    Gv = result['Gv']
    grid_map = result['grid_map']
    mask_int = result['mask_int']
    mesh = result['mesh']
    rsi_value = result['rsi']
    cfg = geometry.cfg
    
    # Heat flux from interior
    mask_solid = grid_map > 1
    
    # Calculate L2D
    flux = 0.0
    ny, nx = temp.shape
    
    # Horizontal flux (interior air -> solid)
    for i in range(ny):
        for j in range(nx - 1):
            if mask_int[i, j] and mask_solid[i, j+1]:
                flux += Gh[i, j] * (temp[i, j] - temp[i, j+1])
    
    # Vertical flux
    for i in range(ny - 1):
        for j in range(nx):
            if mask_int[i, j] and mask_solid[i+1, j]:
                flux += Gv[i, j] * (temp[i, j] - temp[i+1, j])
            if mask_int[i+1, j] and mask_solid[i, j]:
                flux += Gv[i, j] * (temp[i+1, j] - temp[i, j])
    
    delta_t = TEMP_INT - TEMP_EXT
    L2D = flux / delta_t
    
    # Reference 1D values
    from config import MAT_WALL, MAT_INSULATION
    r_wall = 0.13 + (cfg.wall_thickness_mm/1000)/MAT_WALL + RSE
    if cfg.insulation_thick_max_mm > 0:
        r_wall += (cfg.insulation_thick_max_mm/1000)/MAT_INSULATION
    u_wall = 1.0 / r_wall
    
    # Lengths (from geometry canvas)
    canvas = geometry.get_canvas_config()
    y_min, y_max = canvas.y_min_mm, canvas.y_max_mm
    
    # Check if we are using the new centered coordinate system (0 to 1000)
    # or the old one (-500 to 1000)
    # Heuristic: if y_min >= 0, it's likely the new one.
    
    if y_min >= 0:
        # New System: Wall leg is bottom half, Window is top half
        # Corner is at 500 roughly? 
        # Actually we should look for the shift. 
        # geometry.OFF_Y = 500 usually.
        corner_y = getattr(geometry, 'OFF_Y', 500.0)
        
        l_wall = (corner_y - y_min) / 1000.0
        l_total_window = (y_max - corner_y) / 1000.0
    else:
        # Old System: Corner at 0
        l_wall = abs(y_min) / 1000.0
        l_total_window = y_max / 1000.0
        
    l_frame = cfg.frame_width_mm / 1000.0
    l_glass = l_total_window - l_frame
    
    u_frame = 1.3
    u_glass = 1.1
    
    ref_flow = u_wall * l_wall + u_frame * l_frame + u_glass * l_glass
    psi = L2D - ref_flow
    
    # Surface temperatures
    min_temp_all = TEMP_INT
    min_temp_wall = TEMP_INT
    min_temp_frame = TEMP_INT
    min_temp_glass = np.nan
    
    # Find boundary cells (adjacent to interior air)
    padded = np.pad(mask_int, 1)
    m_up = padded[:-2, 1:-1]
    m_dn = padded[2:, 1:-1]
    m_lf = padded[1:-1, :-2]
    m_rt = padded[1:-1, 2:]
    boundary = (m_up | m_dn | m_lf | m_rt) & (~mask_int) & mask_solid
    
    bound_y, bound_x = np.where(boundary)
    if len(bound_y) > 0:
        k_solid = result['cond'][bound_y, bound_x]
        t_cell = temp[bound_y, bound_x]
        mats = grid_map[bound_y, bound_x]
        
        dx_local = mesh.dx_array[bound_x]
        r1 = dx_local / (2 * (k_solid + 1e-12))
        r2 = rsi_value
        t_si = (TEMP_INT * r1 + t_cell * r2) / (r1 + r2)
        
        min_temp_all = np.min(t_si)
        
        mask_wall_mat = np.isin(mats, [MaterialID.WALL, MaterialID.INSULATION, MaterialID.REVEAL_INS])
        if np.any(mask_wall_mat):
            min_temp_wall = np.min(t_si[mask_wall_mat])
        
        mask_frame_mat = mats == MaterialID.FRAME
        if np.any(mask_frame_mat):
            min_temp_frame = np.min(t_si[mask_frame_mat])
        
        mask_glass_mat = mats == MaterialID.GLASS
        if np.any(mask_glass_mat):
            min_temp_glass = np.min(t_si[mask_glass_mat])
    
    fRsi = (min_temp_all - TEMP_EXT) / delta_t
    
    return {
        'Psi': psi,
        'L2D': L2D,
        'fRsi': fRsi,
        'MinT': min_temp_all,
        'MinT_Wall': min_temp_wall,
        'MinT_Frame': min_temp_frame,
        'MinT_Glass': min_temp_glass,
    }


def plot_geometry(mesh, grid_map, filename):
    """Save geometry plot using pcolormesh for adaptive grids."""
    plt.figure(figsize=(12, 10))
    cmap = plt.get_cmap('tab10', 10)
    
    dmax = np.max(grid_map)
    
    # Use pcolormesh for non-uniform grids
    # mesh.x_coords and y_coords are cell edges
    X, Y = np.meshgrid(mesh.x_coords, mesh.y_coords)
    
    plt.pcolormesh(X, Y, grid_map, cmap=cmap, shading='flat',
                   vmin=-0.5, vmax=9.5) # tab10 has 10 colors
                   
    plt.gca().set_aspect('equal')
    
    plt.colorbar(label='Material ID', ticks=range(10))
    
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')
    plt.title(filename.replace('.png', ''))
    plt.savefig(filename, dpi=150)
    plt.close()


def plot_temperature(mesh, temp, filename, title=""):
    """Save temperature plot using pcolormesh."""
    plt.figure(figsize=(12, 10))
    
    X, Y = np.meshgrid(mesh.x_coords, mesh.y_coords)
    
    plt.pcolormesh(X, Y, temp, cmap='jet', shading='flat')
    
    plt.gca().set_aspect('equal')
    plt.colorbar(label='Temperature [°C]')
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')
    plt.title(title if title else filename.replace('.png', ''))
    plt.savefig(filename, dpi=150)
    plt.close()


def run_study(geometry_only=False):
    """Run the 6-case study."""
    configs = get_study_configs()
    results = []
    
    print(f"[INFO] C++ Solver loaded.")
    print(f"\n{'='*60}")
    print(f"6-Case Thermal Bridge Study (Refactored)")
    print(f"Geometry Only: {geometry_only}")
    print(f"{'='*60}\n")
    
    for i, item in enumerate(configs, 1):
        name = item['name']
        cfg = item['cfg']
        safe_name = name.replace(" ", "_").replace("(", "").replace(")", "")
        
        print(f"[{i}/6] {name}")
        
        # Create geometry and mesh
        geometry = WindowRevealGeometry(cfg)
        mesh = AdaptiveMesh(geometry)
        mesh.generate()
        
        print(f"       Mesh: {mesh.nx} x {mesh.ny} cells")
        
        # Build grid for geometry plot
        grid_map, cond = build_material_grid(geometry, mesh.xc, mesh.yc)
        assign_exterior_air(grid_map, cond)
        
        if geometry_only:
            plot_geometry(mesh, grid_map, f"plot_geometry_{safe_name}.png")
            print(f"       → Saved plot_geometry_{safe_name}.png")
            continue
        
        # Pass 1: Psi calculation (Rsi = 0.13)
        print(f"       Solving Psi (Rsi=0.13)...")
        result_psi = solve_thermal(geometry, mesh, rsi_value=0.13)
        res_psi = calculate_psi_from_result(result_psi, geometry)
        
        # Pass 2: fRsi calculation (Rsi = 0.25)
        print(f"       Solving fRsi (Rsi=0.25)...")
        result_frsi = solve_thermal(geometry, mesh, rsi_value=0.25)
        res_frsi = calculate_psi_from_result(result_frsi, geometry)
        
        # Save plots
        plot_geometry(mesh, result_psi['grid_map'], f"plot_geometry_{safe_name}.png")
        plot_temperature(mesh, result_frsi['temp'], f"plot_temp_{safe_name}.png", 
                        f"{name}\nPsi={res_psi['Psi']:.3f}, fRsi={res_frsi['fRsi']:.3f}")
        
        results.append({
            "Case": name,
            "Wall": item['wall_desc'],
            "Insulation": item['ins_desc'],
            "Spacer": item['spacer_desc'],
            "Psi": res_psi['Psi'],
            "fRsi": res_frsi['fRsi'],
            "MinT": res_frsi['MinT'],
            "MinT_Wall": res_frsi['MinT_Wall'],
            "MinT_Frame": res_frsi['MinT_Frame'],
            "MinT_Glass": res_frsi['MinT_Glass']
        })
        
        print(f"       → Psi: {res_psi['Psi']:.3f} W/mK, fRsi: {res_frsi['fRsi']:.3f}")
    
    if not geometry_only:
        # Save results
        with open("results_36_45_v2.md", "w") as f:
            f.write("# Thermal Bridge Calculation Results (Refactored)\n\n")
            f.write("| Case | Wall | Insulation | Psi-Value | fRsi | Min Temp |\n")
            f.write("|---|---|---|---|---|---|\n")
            for r in results:
                f.write(f"| {r['Case']} | {r['Wall']} | {r['Insulation']} | ")
                f.write(f"**{r['Psi']:.3f} W/mK** | {r['fRsi']:.3f} | {r['MinT']:.1f}°C |\n")
        
        print(f"\n{'='*60}")
        print("Results saved to results_36_45_v2.md")
        print(f"{'='*60}")
    else:
        print("\nDone generating geometries.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run 6-case thermal bridge study')
    parser.add_argument('--geometry-only', action='store_true',
                        help='Only generate geometry plots, do not solve')
    args = parser.parse_args()
    
    try:
        run_study(geometry_only=args.geometry_only)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

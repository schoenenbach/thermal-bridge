"""
Simulation Engine for Thermal Bridge Calculations

Provides scenario definitions and solving workflow for window reveal geometries.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from config import CalculationConfig, SpacerType, TEMP_INT, TEMP_EXT, RSI_WALL, RSE, RSI_CORNER, MAT_WALL, MAT_INSULATION
from geometry import build_material_grid, MaterialID
from geometries.window_reveal import WindowRevealGeometry
from mesh import UniformMesh
from solver import get_solver_lib, solve, calculate_conductances_uniform

# --- Scenarios ---
def get_scenarios():
    configs = []
    # Common Parameters
    GRID = 1.0 # 1mm Grid for high accuracy
    
    # 1. 360mm Wall, No Insulation
    configs.append({
        "name": "Scenario 1: Wall 360mm (No Ins)",
        "file_suffix": "scenario_1",
        "cfg": CalculationConfig(
            wall_thickness_mm=360, insulation_thick_max_mm=0, insulation_thick_min_mm=0,
            reveal_insulation_mm=0, taper_length_mm=0, window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50, uninsulated_reveal=True, grid_size_mm=GRID
        )
    })
    
    # 2. 450mm Wall, No Insulation
    configs.append({
        "name": "Scenario 2: Wall 450mm (No Ins)",
        "file_suffix": "scenario_2",
        "cfg": CalculationConfig(
            wall_thickness_mm=450, insulation_thick_max_mm=0, insulation_thick_min_mm=0,
            reveal_insulation_mm=0, taper_length_mm=0, window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50, uninsulated_reveal=True, grid_size_mm=GRID
        )
    })
    
    # 3. 360mm Wall, Ext Ins 200mm, Taper 150mm No Reveal Ins
    configs.append({
        "name": "Scenario 3: Wall 360mm (Ext Ins, No Rev)",
        "file_suffix": "scenario_3",
        "cfg": CalculationConfig(
            wall_thickness_mm=360, insulation_thick_max_mm=200, insulation_thick_min_mm=100,
            reveal_insulation_mm=0, taper_length_mm=150, window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50, uninsulated_reveal=True, grid_size_mm=GRID
        )
    })
    
    # 4. 450mm Wall, Ext Ins 200mm, Taper 150mm No Reveal Ins
    configs.append({
        "name": "Scenario 4: Wall 450mm (Ext Ins, No Rev)",
        "file_suffix": "scenario_4",
        "cfg": CalculationConfig(
            wall_thickness_mm=450, insulation_thick_max_mm=200, insulation_thick_min_mm=100,
            reveal_insulation_mm=0, taper_length_mm=150, window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50, uninsulated_reveal=True, grid_size_mm=GRID
        )
    })
    
    # 5. 360mm Wall, Full Ins (Ext 200mm + Reveal 30mm)
    configs.append({
        "name": "Scenario 5: Wall 360mm (Full Ins)",
        "file_suffix": "scenario_5",
        "cfg": CalculationConfig(
            wall_thickness_mm=360, insulation_thick_max_mm=200, insulation_thick_min_mm=100,
            reveal_insulation_mm=30, taper_length_mm=150, window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50, uninsulated_reveal=False, grid_size_mm=GRID
        )
    })
    
    # 6. 450mm Wall, Full Ins (Ext 200mm + Reveal 30mm)
    configs.append({
        "name": "Scenario 6: Wall 450mm (Full Ins)",
        "file_suffix": "scenario_6",
        "cfg": CalculationConfig(
            wall_thickness_mm=450, insulation_thick_max_mm=200, insulation_thick_min_mm=100,
            reveal_insulation_mm=30, taper_length_mm=150, window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50, uninsulated_reveal=False, grid_size_mm=GRID
        )
    })
    return configs

# --- Solver Core ---
def solve_scenario(scenario_def):
    """Solve a thermal bridge scenario and return results."""
    print(f"\nrunning {scenario_def['name']}...")
    cfg = scenario_def['cfg']
    suffix = scenario_def['file_suffix']
    
    # 1. Geometry & Mesh
    geom = WindowRevealGeometry(cfg)
    mesh = UniformMesh(geom, grid_size_mm=cfg.grid_size_mm)
    mesh.generate()
    
    # 2. Material Grid & Conductivity
    grid_map, cond = build_material_grid(geom, mesh.xc, mesh.yc)
    
    # 3. Boundary Conditions
    mask_int = (grid_map == MaterialID.AIR_INT)
    mask_ext = (grid_map == MaterialID.AIR_EXT)
    
    # K_eff for Surface Resistance
    dx_m = mesh.grid_size_mm / 1000.0
    k_eff_int = dx_m / (2 * RSI_WALL)
    k_eff_ext = dx_m / (2 * RSE)
    
    cond[mask_int] = k_eff_int
    cond[mask_ext] = k_eff_ext
    
    # 4. Conductance Matrices (uniform grid: G = k_harmonic)
    Gh, Gv = calculate_conductances_uniform(cond)
    
    # 5. Solve (Pass 1: Rsi=0.13 for Psi)
    mask = mask_int | mask_ext
    values = np.zeros_like(cond)
    values[mask_int] = TEMP_INT
    values[mask_ext] = TEMP_EXT
    
    temp = np.ones_like(cond) * 10.0
    temp[mask_int] = TEMP_INT
    temp[mask_ext] = TEMP_EXT
    
    temp_res = solve(temp, Gh, Gv, mask, values, max_iter=100000, tol=1e-7, 
                     batch_size=5000, verbose=False)
    
    # 6. Calculate Results - Total Flux L2D
    dt_h = temp_res[:, :-1] - temp_res[:, 1:]
    flow_h = Gh[:, :-1] * dt_h
    m_curr = mask_int[:, :-1]
    m_next = mask_int[:, 1:]
    flux = np.sum(flow_h[m_curr & (~m_next)]) + np.sum(flow_h[(~m_curr) & m_next])
    
    dt_v = temp_res[:-1, :] - temp_res[1:, :]
    flow_v = Gv[:-1, :] * dt_v
    m_curr_v = mask_int[:-1, :]
    m_next_v = mask_int[1:, :]
    flux += np.sum(flow_v[m_curr_v & (~m_next_v)]) + np.sum(flow_v[(~m_curr_v) & m_next_v])
    
    l2d = flux / (TEMP_INT - TEMP_EXT)
    
    # Reference Flow
    l_wall = 0.25
    l_win = 0.25
    l_frame = cfg.frame_width_mm / 1000.0
    l_glass = l_win - l_frame
    
    # Wall U-Value (1D)
    r_wall_1d = RSI_WALL + (cfg.wall_thickness_mm/1000.0)/MAT_WALL + RSE
    if cfg.insulation_thick_max_mm > 0:
        r_wall_1d += (cfg.insulation_thick_max_mm/1000.0)/MAT_INSULATION
    
    u_wall_1d = 1.0 / r_wall_1d
    u_frame = 1.3
    u_glass = 1.1
    
    ref_flow = u_wall_1d * l_wall + u_frame * l_frame + u_glass * l_glass
    psi = l2d - ref_flow
    
    # fRsi Pass (Rsi=0.25)
    k_eff_int_rsi25 = dx_m / (2 * RSI_CORNER)
    cond_frsi = cond.copy()
    cond_frsi[mask_int] = k_eff_int_rsi25
    
    Gh_frsi, Gv_frsi = calculate_conductances_uniform(cond_frsi)
    
    temp_frsi = temp_res.copy()
    temp_frsi = solve(temp_frsi, Gh_frsi, Gv_frsi, mask, values, max_iter=100000, 
                      tol=1e-7, batch_size=5000, verbose=False)
    
    # Minimum surface temperature
    def get_min_surf(t_field, k_field, rsi_used):
        padded = np.pad(mask_int, 1)
        boundary = (padded[:-2, 1:-1] | padded[2:, 1:-1] | 
                    padded[1:-1, :-2] | padded[1:-1, 2:]) & (~mask_int) & (grid_map != MaterialID.AIR_EXT)
        y, x = np.where(boundary)
        if len(y) == 0: 
            return TEMP_INT
        k_solid = k_field[y, x]
        t_node = t_field[y, x]
        r1 = dx_m / (2*k_solid)
        r2 = rsi_used
        t_si = (TEMP_INT * r1 + t_node * r2) / (r1 + r2)
        return np.min(t_si)

    min_temp = get_min_surf(temp_frsi, cond_frsi, RSI_CORNER)
    frsi = (min_temp - TEMP_EXT) / (TEMP_INT - TEMP_EXT)
    
    print(f"  Psi: {psi:.4f} W/mK")
    print(f"  fRsi: {frsi:.4f} (MinT: {min_temp:.2f}C)")
    
    # Plot
    plt.figure(figsize=(10, 10))
    plt.imshow(temp_res, cmap='jet', origin='lower')
    plt.title(f"{scenario_def['name']}\nPsi={psi:.3f}, fRsi={frsi:.3f}, MinT={min_temp:.1f}C")
    plt.colorbar(label='Temp [C]')
    plt.savefig(f"result_{suffix}.png")
    plt.close()
    
    return {
        "name": scenario_def['name'],
        "Psi": psi,
        "fRsi": frsi,
        "MinT": min_temp
    }


def run_all():
    """Run all scenarios and print summary."""
    # Ensure solver is loaded
    get_solver_lib()
    
    scenarios = get_scenarios()
    results = []
    
    for sc in scenarios:
        res = solve_scenario(sc)
        results.append(res)
        
    print("\n--- Final Summary ---")
    print(f"{'Scenario':<40} | {'Psi (W/mK)':<10} | {'fRsi':<10} | {'MinT (C)':<10}")
    print("-" * 80)
    for r in results:
        print(f"{r['name']:<40} | {r['Psi']:<10.4f} | {r['fRsi']:<10.4f} | {r['MinT']:<10.2f}")


if __name__ == "__main__":
    run_all()


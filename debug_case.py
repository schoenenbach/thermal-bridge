import numpy as np
import matplotlib.pyplot as plt
from config import *
from thermal_solver import ThermalSolver, SpacerType

def debug_case_2():
    # Case 2: Renovated (Wall Insulated, NO Reveal Ins, New Spacer)
    cfg = CalculationConfig(
        wall_thickness_mm=360,
        insulation_thick_max_mm=200,
        insulation_thick_min_mm=100,
        reveal_insulation_mm=0,
        taper_length_mm=150,
        window_position_from_exterior_masonry_mm=150,
        masonry_rebate_overlap_mm=50,
        uninsulated_reveal=True,
        grid_size_mm=1.0,
        spacer_type=SpacerType.SWISS_ULTIMATE
    )
    
    solver = ThermalSolver(cfg)
    
    # Check 1: Geometry Plot
    print(f"Grid Size: {solver.nx} x {solver.ny}")
    solver.plot_geometry("debug_geometry_case2.png")
    print("Saved debug_geometry_case2.png")
    
    # Check 2: Check Grid Map Statistics
    unique, counts = np.unique(solver.grid_map, return_counts=True)
    mapping = dict(zip(unique, counts))
    print("Material ID Counts:")
    print(mapping)
    
    # ID_INSULATION is 3. Check if it exists.
    if 3 in mapping:
        print(f"Insulation Nodes: {mapping[3]}")
    else:
        print("ERROR: No Insulation Nodes (ID 3) found!")
        
    # Check 3: Material Properties Map
    # solver.assign_materials() is called in __init__
    # Check conductivity at a point where insulation SHOULD be.
    # Insulation is at x > offset + wall_thickness.
    # Wall thick 360. Offset 50. x > 410.
    # Let's check x=500mm, y=100mm.
    
    x_idx = int(500 / solver.dx / 1000)
    y_idx = int(100 / solver.dx / 1000)
    
    mat_id = solver.grid_map[y_idx, x_idx]
    cond_val = solver.cond[y_idx, x_idx]
    
    print(f"Probe at x=500mm, y=100mm: ID={mat_id}, Cond={cond_val:.4f}")
    print(f"Expected Cond for Insulation: {MAT_INSULATION}")

if __name__ == "__main__":
    debug_case_2()

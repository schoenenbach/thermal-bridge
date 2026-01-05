import numpy as np
import matplotlib.pyplot as plt
from config import *
from thermal_solver import ThermalSolver, SpacerType

def debug_compare():
    print("Comparing Case 1 (No Ins) vs Case 2 (Insulated)...")
    
    # Case 1
    cfg1 = CalculationConfig(
        wall_thickness_mm=360,
        insulation_thick_max_mm=0, # No Ins
        insulation_thick_min_mm=0,
        reveal_insulation_mm=0,
        taper_length_mm=0,
        window_position_from_exterior_masonry_mm=150,
        masonry_rebate_overlap_mm=50,
        uninsulated_reveal=True,
        grid_size_mm=20.0, # Faster for debug
        spacer_type=SpacerType.STAINLESS_STEEL
    )
    
    # Case 2
    cfg2 = CalculationConfig(
        wall_thickness_mm=360,
        insulation_thick_max_mm=200, # Insulated
        insulation_thick_min_mm=100,
        reveal_insulation_mm=0, # Missing arg
        taper_length_mm=150,
        window_position_from_exterior_masonry_mm=150, # Same pos
        masonry_rebate_overlap_mm=50, # Missing arg
        uninsulated_reveal=True,
        grid_size_mm=20.0,
        spacer_type=SpacerType.SWISS_ULTIMATE # Changed Spacer too (as per main.py)
    )
    
    s1 = ThermalSolver(cfg1)
    s1.solve()
    
    s2 = ThermalSolver(cfg2)
    s2.solve()
    
    # Align grids?
    # cfg2 has insulation, so width is larger.
    # Dimensions: s1.nx < s2.nx
    print(f"Grid 1: {s1.nx}x{s1.ny}")
    print(f"Grid 2: {s2.nx}x{s2.ny}")
    
    # Compare overlapping region (Masonry + Window)
    # Both start at offset_x.
    # Masonry width is fixed.
    
    min_nx = min(s1.nx, s2.nx)
    min_ny = min(s1.ny, s2.ny)
    
    t1 = s1.temp[:min_ny, :min_nx]
    t2 = s2.temp[:min_ny, :min_nx]
    
    diff = t2 - t1
    
    print(f"Max Diff: {np.max(diff):.4f} C")
    print(f"Min Diff: {np.min(diff):.4f} C")
    print(f"Mean Diff: {np.mean(diff):.4f} C")
    
    # Plot Diff
    plt.figure(figsize=(10,8))
    plt.imshow(diff, cmap='bwr', origin='lower')
    plt.colorbar(label='Delta T (Case 2 - Case 1)')
    plt.title('Temperature Difference')
    plt.savefig('debug_diff.png')
    print("Saved debug_diff.png")

if __name__ == "__main__":
    debug_compare()

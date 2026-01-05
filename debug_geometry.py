import numpy as np
import sys
# Import the class/config from main script
from calculate_psi import ThermalSolver, CalculationConfig

def print_ascii_art():
    # Setup Case 3 Config
    cfg = CalculationConfig(
        wall_thickness_mm=360,
        insulation_thick_max_mm=200,
        insulation_thick_min_mm=100,
        reveal_insulation_mm=30,
        taper_length_mm=150,
        window_position_from_exterior_masonry_mm=150,
        masonry_rebate_overlap_mm=50,
        uninsulated_reveal=False
    )
    
    solver = ThermalSolver(cfg, rsi_value=0.13)
    # Geometry is setup in init
    
    # Coordinates of interest
    # Reveal Edge Y
    # Window Outer Face X
    
    # Solver DX is local...
    # Re-implement to_idx based on grid size (5.0mm)
    dx = 5.0 / 1000.0 # 5mm in meters
    to_idx = lambda mm: int(mm / 5.0)
    
    reveal_y_idx = to_idx(500) # Hardcoded in script
    w_outer_idx = to_idx(50 + 360) # Offset + Wall
    win_outer_idx = w_outer_idx - to_idx(150)
    
    print(f"Reveal Edge Y: {reveal_y_idx}")
    print(f"Win Outer X: {win_outer_idx}")
    print(f"Wall Outer X: {w_outer_idx}")
    
    # Inspect a grid around the corner
    # Y range: Reveal Edge - 10 to Reveal Edge + 60 (covering simple wall, rebate, frame)
    # X range: Win Outer - 10 to Wall Outer + 10
    
    y_start = reveal_y_idx - 5
    y_end = reveal_y_idx + 20 # 20*2.5mm = 50mm (Rebate Zone)
    
    x_start = win_outer_idx - 5
    x_end = w_outer_idx + 5
    
    print("\n--- GRID MAP INSPECTION (IDs) ---")
    print("Map format: [Y, X]")
    print(f"Y Range: {y_start} to {y_end}")
    print(f"X Range: {x_start} to {x_end}")
    print("Legend: 0=AirI, 1=AirE, 2=Wall, 3=Ins, 4=Frame, 5=Glass, 6=RevIns\n")
    
    # Header
    print("      ", end="")
    for x in range(x_start, x_end):
        print(f"{x%10}", end="")
    print()
    
    for y in range(y_start, y_end):
        print(f"Y={y:3d} ", end="")
        for x in range(x_start, x_end):
            val = solver.grid_map[y, x]
            char = str(val) if val < 10 else "?"
            # Highlight Wall (2) and RevIns (6)
            if val == 2: char = "W"
            if val == 6: char = "R"
            if val == 4: char = "F"
            if val == 0: char = "."
            if val == 3: char = "I"
            print(char, end="")
        
        # Annotate
        msg = ""
        if y == reveal_y_idx: msg = " <- Reveal Edge"
        print(msg)

if __name__ == "__main__":
    print_ascii_art()

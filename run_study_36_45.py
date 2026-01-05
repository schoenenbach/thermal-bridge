import os
import argparse
from config import CalculationConfig, SpacerType
from thermal_solver import ThermalSolver

def run_study(geometry_only=False):
    # Common Parameters
    TAPER_LEN = 150
    INS_MAX = 200
    INS_MIN = 100
    REVEAL_INS = 30
    GRID = 5 # mm
    
    # Define Configurations (Swiss Spacer Only)
    configs = []
    
    # Scenario 1: No Insulation
    # Case 1.1: 36cm
    configs.append({
        "name": "Wall 360mm (Pos 150mm) (No Ins)",
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
    
    # Case 1.2: 45cm
    configs.append({
        "name": "Wall 450mm (Pos 150mm) (No Ins)",
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
    
    # Scenario 2: Ext Insulation + Taper (No Reveal Ins)
    # Case 2.1: 36cm
    configs.append({
        "name": "Wall 360mm (Pos 150mm) (No Rev Ins)",
        "wall_desc": "360mm",
        "ins_desc": "200->100 mm",
        "spacer_desc": "Swiss",
        "cfg": CalculationConfig(
            wall_thickness_mm=360,
            insulation_thick_max_mm=INS_MAX,
            insulation_thick_min_mm=INS_MIN,
            reveal_insulation_mm=0,
            taper_length_mm=TAPER_LEN,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=True, # Explicitly no reveal insulation logic
            grid_size_mm=GRID,
            spacer_type=SpacerType.SWISS_ULTIMATE
        )
    })
    
    # Case 2.2: 45cm
    configs.append({
        "name": "Wall 450mm (Pos 150mm) (No Rev Ins)",
        "wall_desc": "450mm",
        "ins_desc": "200->100 mm",
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
    
    # Scenario 3: Ext Insulation + Taper + Reveal Insulation
    # Case 3.1: 36cm
    configs.append({
        "name": "Wall 360mm (Pos 150mm) (Full)",
        "wall_desc": "360mm",
        "ins_desc": "200->100 mm",
        "spacer_desc": "Swiss",
        "cfg": CalculationConfig(
            wall_thickness_mm=360,
            insulation_thick_max_mm=INS_MAX,
            insulation_thick_min_mm=INS_MIN,
            reveal_insulation_mm=REVEAL_INS,
            taper_length_mm=TAPER_LEN,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=False, # Enable Reveal Ins
            grid_size_mm=GRID,
            spacer_type=SpacerType.SWISS_ULTIMATE
        )
    })
    
    # Case 3.2: 45cm
    configs.append({
        "name": "Wall 450mm (Pos 150mm) (Full)",
        "wall_desc": "450mm",
        "ins_desc": "200->100 mm",
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
    
    results = []
    
    print(f"Starting 6-Case Study (Geometry Only: {geometry_only})...")
    
    for item in configs:
        name = item['name']
        cfg = item['cfg']
        # Sanitize filename
        safe_name = name.replace(" ", "_").replace("(", "").replace(")", "")
        
        print(f"Processing {name}...")
        
        # Pass 1: Psi
        solver_psi = ThermalSolver(cfg, rsi_value=0.13)
        if geometry_only:
            solver_psi.plot_geometry(f"plot_geometry_{safe_name}.png")
            print(f"  -> Saved plot_geometry_{safe_name}.png")
            continue
            
        solver_psi.solve(max_iter=15000)
        res_psi = solver_psi.calculate_psi()
        
        # Pass 2: fRsi (Rsi=0.25)
        # Note: Usually geometry is identical, just Rsi changes.
        solver_frsi = ThermalSolver(cfg, rsi_value=0.25)
        solver_frsi.solve(max_iter=15000)
        res_frsi = solver_frsi.calculate_psi()
        
        # Plot Temp (Use Psi run for standard check, or fRsi run? 
        # Usually Psi run has standard boundaries. Surface temps are best from fRsi run.)
        solver_frsi.plot_results(f"plot_temp_{safe_name}.png")
        
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
        
        print(f"  -> Psi: {res_psi['Psi']:.3f}, fRsi: {res_frsi['fRsi']:.3f}")

    if not geometry_only:
        # Save Results
        with open("results_36_45.md", "w") as f:
            f.write("# Thermal Bridge Calculation Results\n\n")
            f.write("| Case | Wall | Insulation | Spacer | Psi-Value | fRsi | Min Temp | Min Temp Details |\n")
            f.write("|---|---|---|---|---|---|---|---|\n")
            for r in results:
                details = f"Wall: {r['MinT_Wall']:.1f}°C, Frame: {r['MinT_Frame']:.1f}°C, Glass: {r['MinT_Glass']:.1f}°C"
                f.write(f"| {r['Case']} | {r['Wall']} | {r['Insulation']} | {r['Spacer']} | **{r['Psi']:.3f} W/mK** | {r['fRsi']:.3f} | {r['MinT']:.1f}°C | {details} |\n")
        
        print("Done. Results saved to results_36_45.md")
    else:
        print("Done generating geometries.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry-only", action="store_true", help="Only generate geometry plots, do not solve.")
    args = parser.parse_args()
    
    try:
        run_study(geometry_only=args.geometry_only)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

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
    GRID = 2.5 # mm
    
    # Define Configurations
    configs = []
    
    # Scenario 1: No Insulation
    # Case 1.1: 36cm
    configs.append({
        "name": "36cm_NoIns",
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
        "name": "45cm_NoIns",
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
        "name": "36cm_ExtIns_NoReveal",
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
        "name": "45cm_ExtIns_NoReveal",
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
    # Reveal Insulation added.
    
    # Case 3.1: 36cm
    configs.append({
        "name": "36cm_Full",
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
        "name": "45cm_Full",
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
        print(f"Processing {name}...")
        
        # Pass 1: Psi
        solver_psi = ThermalSolver(cfg, rsi_value=0.13)
        # Save Geometry Plot
        solver_psi.plot_geometry(f"plot_geometry_{name}.png")
        print(f"  -> Saved plot_geometry_{name}.png")
        
        if geometry_only:
            continue
            
        solver_psi.solve(max_iter=60000)
        res_psi = solver_psi.calculate_psi()
        
        # Pass 2: fRsi (Rsi=0.25)
        # Note: Usually geometry is identical, just Rsi changes.
        solver_frsi = ThermalSolver(cfg, rsi_value=0.25)
        solver_frsi.solve(max_iter=60000)
        res_frsi = solver_frsi.calculate_psi()
        
        # Plot Temp
        solver_psi.plot_results(f"plot_temp_{name}.png")
        
        results.append({
            "Case": name,
            "Psi": res_psi['Psi'],
            "fRsi": res_frsi['fRsi'],
            "MinT_Wall": res_frsi['MinT_Wall'],
            "MinT_Frame": res_frsi['MinT_Frame'],
            "MinT_Glass": res_frsi['MinT_Glass']
        })
        
        print(f"  -> Psi: {res_psi['Psi']:.3f}, fRsi: {res_frsi['fRsi']:.3f}")

    if not geometry_only:
        # Save Results
        with open("results_36_45.md", "w") as f:
            f.write("# Thermal Bridge Study (36cm vs 45cm)\n\n")
            f.write("| Case | Psi (W/mK) | fRsi | MinT Wall | MinT Frame | MinT Glass |\n")
            f.write("|---|---|---|---|---|---|\n")
            for r in results:
                f.write(f"| {r['Case']} | **{r['Psi']:.3f}** | {r['fRsi']:.3f} | {r['MinT_Wall']:.1f}°C | {r['MinT_Frame']:.1f}°C | {r['MinT_Glass']:.1f}°C |\n")
        
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

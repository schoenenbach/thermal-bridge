from config import CalculationConfig
from thermal_solver import ThermalSolver

if __name__ == "__main__":
    from config import SpacerType

    # Define High-Fidelity Configurations for Verification
    # Case A: 36cm Wall, No Insulation, Old Window (Stainless Spacer) - Baseline
    # Case A: 36cm Wall, No Insulation, Old Window (Stainless Spacer) - Baseline
    config_old = CalculationConfig(
        wall_thickness_mm=360,
        insulation_thick_max_mm=0,
        insulation_thick_min_mm=0,
        reveal_insulation_mm=0,
        taper_length_mm=0,
        window_position_from_exterior_masonry_mm=150,
        masonry_rebate_overlap_mm=50,
        uninsulated_reveal=True,
        grid_size_mm=2.5,           # High Res (adjusted for speed)
        spacer_type=SpacerType.STAINLESS_STEEL # "Old" (Ug 1.1)
    )

    # Case B: 36cm Wall, No Insulation, New Window (Swiss Spacer) - Comparison
    config_new = CalculationConfig(
        wall_thickness_mm=360,
        insulation_thick_max_mm=0,
        insulation_thick_min_mm=0,
        reveal_insulation_mm=0,
        taper_length_mm=0,
        window_position_from_exterior_masonry_mm=150,
        masonry_rebate_overlap_mm=50,
        uninsulated_reveal=True,
        grid_size_mm=2.5,           # High Res (adjusted for speed)
        spacer_type=SpacerType.SWISS_ULTIMATE 
    )

    # List of configs to run
    run_configs = [
        ("Old Window (Stainless)", config_old),
        ("New Window (Swiss)", config_new)
    ]
    
    results = []
    
    print("Starting High-Fidelity Thermal Bridge Calculation (2.5mm Grid)...")
    
    for name, cfg in run_configs:
        print(f"Calculating: {name} (Grid: {cfg.grid_size_mm}mm, Spacer: {cfg.spacer_type})...")
        case_id = name.replace(" ", "_").replace("(", "").replace(")", "").lower()
        
        # --- PASS 1: Calculate Psi (Rsi = 0.13) ---
        solver_psi = ThermalSolver(cfg, rsi_value=0.13)
        solver_psi.plot_geometry(f"debug_geometry_{case_id}.png") # Visual Check
        solver_psi.solve(max_iter=60000)
        res_psi = solver_psi.calculate_psi()
        
        # --- PASS 2: Calculate fRsi (Rsi = 0.25) ---
        solver_frsi = ThermalSolver(cfg, rsi_value=0.25)
        solver_frsi.solve(max_iter=60000)
        res_frsi = solver_frsi.calculate_psi()
        
        # Plotting
        fn = f"temp_dist_{case_id}.png"
        solver_psi.plot_results(fn)
        
        results.append({
            "CASE": name,
            "Psi": res_psi['Psi'],
            "fRsi": res_frsi['fRsi'],
            "MinT_Wall": res_frsi['MinT_Wall'],
            "MinT_Frame": res_frsi['MinT_Frame'],
            "MinT_Glass": res_frsi['MinT_Glass']
        })
        
        print(f"Done. Psi:{res_psi['Psi']:.3f}, fRsi:{res_frsi['fRsi']:.3f}")
        print(f"Min Temps -> Wall:{res_frsi['MinT_Wall']:.2f}C, Frame:{res_frsi['MinT_Frame']:.2f}C, Glass:{res_frsi['MinT_Glass']:.2f}C")
        print("-" * 40)

    # Generate Report MD
    with open("result_comparison_spacers.md", "w") as f:
        f.write("# Spacer Comparison Results (36cm Wall, No Ins)\n\n")
        f.write("| Case | Psi-Value | fRsi | MinT Wall | MinT Frame | MinT Glass |\n")
        f.write("|---|---|---|---|---|---|\n")
        for r in results:
            f.write(f"| {r['CASE']} | **{r['Psi']:.3f}** | {r['fRsi']:.3f} | {r['MinT_Wall']:.1f}°C | {r['MinT_Frame']:.1f}°C | {r['MinT_Glass']:.1f}°C |\n")


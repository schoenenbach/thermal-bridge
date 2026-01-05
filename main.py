from config import CalculationConfig
from thermal_solver import ThermalSolver

if __name__ == "__main__":
    # Define Calculation Configurations (Final Consolidation: 6 Scenarios)
    # All scenarios have Masonry Rebate (Fensteranschlag) ~50mm.
    # Window Position: 150mm depth.
    
    configs = [
        # --- Wall 36 cm ---
        
        # 1. Baseline (No Insulation)
        # Altbau status quo.
        CalculationConfig(
            wall_thickness_mm=360,
            insulation_thick_max_mm=0,
            insulation_thick_min_mm=0,
            reveal_insulation_mm=0,
            taper_length_mm=0,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=True 
        ),
        
        # 2. Renovated (Wall Insulated, NO Reveal Ins)
        # "Forgot the reveal".
        CalculationConfig(
            wall_thickness_mm=360,
            insulation_thick_max_mm=200,
            insulation_thick_min_mm=100,
            reveal_insulation_mm=0,
            taper_length_mm=150,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=True
        ),
        
        # 3. Renovated (Wall + Reveal Ins)
        # Correct execution.
        CalculationConfig(
            wall_thickness_mm=360,
            insulation_thick_max_mm=200,
            insulation_thick_min_mm=100,
            reveal_insulation_mm=30,
            taper_length_mm=150,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=False
        ),
        
        # --- Wall 45 cm ---
        
        # 4. Baseline (No Insulation)
        CalculationConfig(
            wall_thickness_mm=450,
            insulation_thick_max_mm=0,
            insulation_thick_min_mm=0,
            reveal_insulation_mm=0,
            taper_length_mm=0,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=True
        ),
        
        # 5. Renovated (Wall Insulated, NO Reveal Ins)
        CalculationConfig(
            wall_thickness_mm=450,
            insulation_thick_max_mm=200,
            insulation_thick_min_mm=100,
            reveal_insulation_mm=0,
            taper_length_mm=150,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=True
        ),
        
        # 6. Renovated (Wall + Reveal Ins)
        CalculationConfig(
            wall_thickness_mm=450,
            insulation_thick_max_mm=200,
            insulation_thick_min_mm=100,
            reveal_insulation_mm=30,
            taper_length_mm=150,
            window_position_from_exterior_masonry_mm=150,
            masonry_rebate_overlap_mm=50,
            uninsulated_reveal=False
        )
    ]
    
    results = []
    
    print("Starting Thermal Bridge Calculation...")
    
    for i, cfg in enumerate(configs):
        print(f"Calculating Case {i+1}...")
        
        # --- PASS 1: Calculate Psi (Rsi = 0.13) ---
        solver_psi = ThermalSolver(cfg, rsi_value=0.13)
        
        # filename_geo = f"geometry_case_{i+1}.png"
        # solver_psi.plot_geometry(filename_geo)
        # print(f"Geometry plotted: {filename_geo}")
        
        solver_psi.solve()
        res_psi = solver_psi.calculate_psi()
        psi_val = res_psi['Psi']
        u_wall_val = res_psi['U_Wall']
        
        # --- PASS 2: Calculate fRsi (Rsi = 0.25) ---
        solver_frsi = ThermalSolver(cfg, rsi_value=0.25)
        solver_frsi.solve()
        res_frsi = solver_frsi.calculate_psi()
        frsi_val = res_frsi['fRsi']
        mint_val = res_frsi['MinT']
        mint_wall_val = res_frsi['MinT_Wall']
        mint_frame_val = res_frsi['MinT_Frame']
        
        # Plotting (Let's plot the fRsi temperature field as it is critical for mold)
        # Or Psi field? Standard is usually Psi field.
        # Let's keep plotting the Psi run (Run 1)
        
        case_id = f"wall_{cfg.wall_thickness_mm}"
        if cfg.window_position_from_exterior_masonry_mm > 0:
            case_id += f"_pos_{cfg.window_position_from_exterior_masonry_mm}"
        if cfg.insulation_thick_max_mm == 0:
            case_id += "_no_ins"
        elif cfg.uninsulated_reveal:
            case_id += "_no_rev_ins"
            
        fn = f"temp_dist_{case_id}.png"
        solver_psi.plot_results(fn)
        
        case_name = f"Wall {cfg.wall_thickness_mm}mm"
        if cfg.window_position_from_exterior_masonry_mm > 0:
            case_name += f" (Pos {cfg.window_position_from_exterior_masonry_mm}mm)"
            
        if cfg.insulation_thick_max_mm == 0:
            case_name += " (No Ins)"
        elif cfg.uninsulated_reveal:
            case_name += " (No Rev Ins)"
            
        results.append({
            "CASE": case_name,
            "Psi": psi_val,
            "U_Wall": u_wall_val,
            "fRsi": frsi_val,
            "MinT": mint_val,
            "MinT_Wall": mint_wall_val,
            "MinT_Frame": mint_frame_val,
            "MinT_Glass": res_frsi['MinT_Glass']
        })
        if 'MinT_Glass' in res_frsi:
             print(f"Done. Psi:{res_frsi['Psi']:.3f}, fRsi:{res_frsi['fRsi']:.3f} | Wall:{res_frsi['MinT_Wall']:.1f}C, Frame:{res_frsi['MinT_Frame']:.1f}C, Glass:{res_frsi['MinT_Glass']:.1f}C")
        else:
             print(f"Done. Psi:{res_frsi['Psi']:.3f}, fRsi:{res_frsi['fRsi']:.3f} | Wall:{res_frsi['MinT_Wall']:.1f}C, Frame:{res_frsi['MinT_Frame']:.1f}C")

    # Generate Report MD
    with open("calculation_report.md", "w") as f:
        f.write("# Thermal Bridge Calculation Results\n\n")
        f.write("| Case | Wall | Insulation | Psi-Value | fRsi | Min Temp |\n")
        f.write("|---|---|---|---|---|---|\n")
        for r in results:
            f.write(f"| {r['CASE']} | {r['CASE'].split()[1]} | 200->100 mm | **{r['Psi']:.3f} W/mK** | {r['fRsi']:.3f} | {r['MinT']:.1f}°C |\n")
        
        f.write("\n## Temperature Plots\n")
        f.write("![36cm](temp_dist_wall_360.png)\n")
        f.write("![45cm](temp_dist_wall_450.png)\n")
        f.write("![36cm No Rev](temp_dist_wall_360_no_rev_ins.png)\n")
        f.write("![45cm No Rev](temp_dist_wall_450_no_rev_ins.png)\n")
        f.write("![36cm No Ins](temp_dist_wall_360_no_ins.png)\n")
        f.write("![45cm No Ins](temp_dist_wall_450_no_ins.png)\n")

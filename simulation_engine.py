"""
Simulation Engine for Thermal Bridge Calculations

Provides scenario definitions and solving workflow for window reveal geometries.
"""

import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
from config import CalculationConfig, SpacerType, TEMP_INT, TEMP_EXT, RSI_WALL, RSE, RSI_CORNER, MAT_WALL, MAT_INSULATION
from geometry import build_material_grid, MaterialID
from mesh import UniformMesh, AdaptiveMesh
from solver import get_solver_lib, solve, calculate_conductances_uniform, plot_temperature_map, plot_geometry
from declarative_geometry import DeclarativeGeometry
import yaml

# --- Scenarios ---
def get_scenarios():
    configs = []
    
    # Discovery from scenarios/ directory
    import glob
    import os
    import re
    
    # Match scenario_*.yaml
    yaml_files = glob.glob("scenarios/scenario_*.yaml")
    
    # Sort by number: scenario_1.yaml -> 1
    def extract_num(fname):
        match = re.search(r"scenario_(\d+)", fname)
        return int(match.group(1)) if match else 999
        
    yaml_files.sort(key=extract_num)
    
    for fpath in yaml_files:
        fname = os.path.basename(fpath).replace('.yaml', '')
        # Read name from YAML content for better display?
        # Or just use filename?
        # Let's peek at name field
        name = fname
        try:
            with open(fpath, 'r') as f:
                # Read first few lines or safe load
                # safe_load is fine
                data = yaml.safe_load(f)
                if 'name' in data:
                    name = data['name']
        except Exception as e:
            print(f"[WARNING] Failed to parse name from {fpath}: {e}")
            
        configs.append({
            "name": name,
            "file_suffix": fname,
            "cfg": fpath
        })
        
    return configs

# --- Solver Core ---
def solve_scenario(scenario_def, use_adaptive_mesh=True):
    """Solve a thermal bridge scenario and return results."""
    print(f"\nrunning {scenario_def['name']}...")
    cfg = scenario_def['cfg']
    suffix = scenario_def['file_suffix']
    
    # Load Geometry
    if isinstance(cfg, str) and cfg.endswith('.yaml'):
         # Load Declarative
         with open(cfg, 'r') as f:
             data = yaml.safe_load(f)
         geom = DeclarativeGeometry(data)
         # Extract grid size from resolved data in geom
         grid_sz = 2.5
         if 'canvas' in geom.data and 'grid' in geom.data['canvas']:
             grid_sz = float(geom.data['canvas']['grid'])
         cfg_grid_size = grid_sz
         wall_thick_mm = geom.data.get('variables', {}).get('wall_thick', 360)
    else:
        raise ValueError(f"Unsupported config type: {type(cfg)}. Expected YAML file path.")
    
    if use_adaptive_mesh:
        from mesh import AdaptiveMesh
        mesh = AdaptiveMesh(geom)
    else:
        from mesh import UniformMesh
        # UniformMesh needs explicit grid size if not default
        mesh = UniformMesh(geom, grid_size_mm=cfg_grid_size)

    mesh.generate()
    print(f"  {mesh.info()}")
    
    # 2. Material Grid & Conductivity
    grid_map, cond = build_material_grid(geom, mesh.xc, mesh.yc)
    
    # 3. Boundary Conditions
    mask_int = (grid_map == MaterialID.AIR_INT)
    mask_ext = (grid_map == MaterialID.AIR_EXT)
    
    # K_eff for Surface Resistance (Using local dx/dy would be best, but mesh arrays are 1D)
    # For adaptive mesh, we should check surface resistance locally, but simplified here:
    # Use average or min dx for safety, or better: apply resistance inside conductance calc?
    # Actually, build_material_grid applies K for solid materials.
    # Air nodes are fixed to Temp, so K doesn't matter for them *except* near boundary.
    # But wait, the standard way (ISO 10211) is that the surface resistance is a layer.
    # In FDM, we often adjust the conductivity of the boundary cell or use a ghost node.
    # Here, we set K of the air node to be K_eff = dx / (2 * Rsi). This assumes node is centered?
    # With Adaptive Mesh, dx varies. We need to be careful.
    
    # Let's iterate over boundary cells or use the mesh arrays.
    # mesh.dx_array is 1D (nx columns), mesh.dy_array is 1D (ny rows).
    # cond is (ny, nx).
    
    # Vectorized K_eff calculation
    # k_eff = dx / (2 * R) where dx is the width of the cell
    dx_grid = np.tile(mesh.dx_array, (mesh.ny, 1))
    
    # This logic assumes vertical walls (using dx) for horizontal flux?
    # This "Simple" Boundary Condition handling in the original code:
    # k_eff_int = dx_m / (2 * RSI_WALL)
    # cond[mask_int] = k_eff_int
    
    # This implies that for ALL air nodes, we set this K. 
    # This is slightly wrong for internal air nodes far from wall, but they are Dirichlet fixed anyway
    # so their K doesn't affect the solution, ONLY the flux calculation at the boundary.
    # So yes, we can set K for all air nodes based on their local dx.
    
    k_eff_int = (dx_grid / 1000.0) / (2 * RSI_WALL)
    k_eff_ext = (dx_grid / 1000.0) / (2 * RSE)
    
    cond[mask_int] = k_eff_int[mask_int]
    cond[mask_ext] = k_eff_ext[mask_ext]
    
    # 4. Conductance Matrices (Use general calculation for non-uniform mesh)
    from solver import calculate_conductances
    Gh, Gv = calculate_conductances(cond, mesh.dx_array, mesh.dy_array)
    
    # Correction for Anisotropic Mesh at Boundaries
    # The standard calculation uses scalar k for air, which cannot satisfy RSI for both dx and dy
    # if the air cell is not square. We explicitly overwrite boundary conductances.
    
    def apply_boundary_conductances(Gh, Gv, rsi, mask_air):
        # Horizontal Interfaces: (i, j) connects j and j+1
        # 1. Air at Left (j), Solid at Right (j+1)
        # mask is (ny, nx), Gh is (ny, nx) [last col unused usually or periodic]
        # We perform vectorized update.
        
        dx_m = mesh.dx_array / 1000.0
        dy_m = mesh.dy_array / 1000.0
        
        # --- Horizontal ---
        # Find interfaces
        is_air = mask_air
        is_solid = (~mask_air) & (grid_map != MaterialID.AIR_EXT) & (grid_map != MaterialID.AIR_INT)
        
        # Left Air, Right Solid
        # shift solid mask to left to align with Gh index (which is "left" of the link)
        # link (j) connects j and j+1.
        # IF is_air[:, :-1] AND is_solid[:, 1:]
        mask_lr = is_air[:, :-1] & is_solid[:, 1:]
        
        if np.any(mask_lr):
            # For these links, resistance is R_solid_half + RSI
            # Solid is at right (j+1)
            # We need k_solid and dx_solid from j+1
            # k is in cond.
            
            # Indices
            y_idx, x_idx = np.where(mask_lr)
            # x_idx corresponds to j. j+1 is solid.
            
            k_s = cond[y_idx, x_idx + 1]
            dx_s = dx_m[x_idx + 1]
            dy = dy_m[y_idx]
            
            # G = Area / R_tot = dy / (dx_s/(2*k_s) + RSI)
            Gh_new = dy / ( (dx_s / (2*k_s)) + rsi )
            Gh[y_idx, x_idx] = Gh_new

        # Left Solid, Right Air
        # IF is_solid[:, :-1] AND is_air[:, 1:]
        mask_rl = is_solid[:, :-1] & is_air[:, 1:]
        
        if np.any(mask_rl):
            # Solid is at left (j)
            y_idx, x_idx = np.where(mask_rl)
            k_s = cond[y_idx, x_idx]
            dx_s = dx_m[x_idx]
            dy = dy_m[y_idx]
            
            Gh_new = dy / ( (dx_s / (2*k_s)) + rsi )
            Gh[y_idx, x_idx] = Gh_new
            
        # --- Vertical ---
        # Vertical Interfaces: (i, j) connects i and i+1
        # Top Air (i), Bottom Solid (i+1)
        
        # Top Air, Bottom Solid
        mask_ud = is_air[:-1, :] & is_solid[1:, :]
        if np.any(mask_ud):
            y_idx, x_idx = np.where(mask_ud)
            # Solid is i+1
            k_s = cond[y_idx + 1, x_idx]
            dy_s = dy_m[y_idx + 1]
            dx = dx_m[x_idx]
            
            # G = Area / R_tot = dx / (dy_s/(2*k_s) + RSI)
            Gv_new = dx / ( (dy_s / (2*k_s)) + rsi )
            Gv[y_idx, x_idx] = Gv_new
            
        # Top Solid, Bottom Air
        mask_du = is_solid[:-1, :] & is_air[1:, :]
        if np.any(mask_du):
            y_idx, x_idx = np.where(mask_du)
            # Solid is i
            k_s = cond[y_idx, x_idx]
            dy_s = dy_m[y_idx]
            dx = dx_m[x_idx]
            
            Gv_new = dx / ( (dy_s / (2*k_s)) + rsi )
            Gv[y_idx, x_idx] = Gv_new
            
    # Apply corrections for Interior and Exterior
    apply_boundary_conductances(Gh, Gv, RSI_WALL, mask_int)
    apply_boundary_conductances(Gh, Gv, RSE, mask_ext)

    
    # 5. Solve (Pass 1: Rsi=0.13 for Psi)
    mask = mask_int | mask_ext
    values = np.zeros_like(cond)
    values[mask_int] = TEMP_INT
    values[mask_ext] = TEMP_EXT
    
    temp = np.ones_like(cond) * 10.0
    temp[mask_int] = TEMP_INT
    temp[mask_ext] = TEMP_EXT
    
    # Pass 1: Solve for Psi (Standard Rsi = 0.13)
    print(f"  [PASS 1] Solving for Psi-value (Rsi={RSI_WALL})...")
    temp_res = solve(temp, Gh, Gv, mask, values, max_iter=100000, tol=1e-7, 
                     batch_size=5000, verbose=True)
    
    # 6. Calculate Results - Total Flux L2D
    # Flux calculation needs to handle variable dy/dx
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
    
    # Handle YAML config abstraction
    if hasattr(geom, 'data'):
        vars = geom.data.get('variables', {})
        f_width = float(vars.get('frame_width', 70))
        wall_th = float(vars.get('wall_thick', 360))
        ins_th = float(vars.get('ins_thick_max', 0))
    else:
        # Fallback if DeclarativeGeometry interface changes or if we have another type
        # For now, just error or assume defaults?
        # Let's keep it safe.
        f_width = 70.0
        wall_th = 360.0
        ins_th = 0.0
        
    l_frame = f_width / 1000.0
    l_glass = l_win - l_frame
    
    # Wall U-Value (1D)
    r_wall_1d = RSI_WALL + (wall_th/1000.0)/MAT_WALL + RSE
    if ins_th > 0:
        r_wall_1d += (ins_th/1000.0)/MAT_INSULATION
    
    u_wall_1d = 1.0 / r_wall_1d
    u_frame = 1.3
    u_glass = 1.1
    
    ref_flow = u_wall_1d * l_wall + u_frame * l_frame + u_glass * l_glass
    psi = l2d - ref_flow
    
    # fRsi Pass (Rsi=0.25)
    # Recalculate K_eff for interior with new Rsi
    k_eff_int_rsi25 = (dx_grid / 1000.0) / (2 * RSI_CORNER)
    cond_frsi = cond.copy()
    cond_frsi[mask_int] = k_eff_int_rsi25[mask_int]
    
    Gh_frsi, Gv_frsi = calculate_conductances(cond_frsi, mesh.dx_array, mesh.dy_array)
    
    # Apply corrections for fRsi pass
    apply_boundary_conductances(Gh_frsi, Gv_frsi, RSI_CORNER, mask_int)
    apply_boundary_conductances(Gh_frsi, Gv_frsi, RSE, mask_ext)
    
    print(f"  [PASS 2] Solving for fRsi/MinT (Rsi={RSI_CORNER})...")
    temp_frsi = temp_res.copy()
    temp_frsi = solve(temp_frsi, Gh_frsi, Gv_frsi, mask, values, max_iter=100000, 
                      tol=1e-7, batch_size=5000, verbose=True)
    
    # Minimum surface temperature
    def get_min_surf(t_field, k_field, rsi_used, material_filter=None):
        padded = np.pad(mask_int, 1)
        
        boundary = (padded[:-2, 1:-1] | padded[2:, 1:-1] | 
                    padded[1:-1, :-2] | padded[1:-1, 2:]) & (~mask_int) & (grid_map != MaterialID.AIR_EXT)
        
        y, x = np.where(boundary)
        if len(y) == 0: 
            return TEMP_INT
            
        # Filter by material if requested
        if material_filter is not None:
            # grid_map[y, x] gives materials of the boundary solid nodes
            mats = grid_map[y, x]
            
            if isinstance(material_filter, (list, tuple)):
                # Vectorizedisin verification
                keep = np.isin(mats, material_filter)
            else:
                keep = (mats == material_filter)
                
            y = y[keep]
            x = x[keep]
            if len(y) == 0:
                return None # No surface nodes for this material
        
        k_solid = k_field[y, x]
        t_node = t_field[y, x]
        
        # Use local cell width for surface resistance calc
        # mesh.dx_array is in mm, convert to meters
        dx_local_m = mesh.dx_array[x] / 1000.0
        
        r1 = dx_local_m / (2*k_solid)
        r2 = rsi_used
        t_si = (TEMP_INT * r1 + t_node * r2) / (r1 + r2)
        return np.min(t_si)

    min_temp = get_min_surf(temp_frsi, cond_frsi, RSI_CORNER)
    
    # Calculate specific minimum temperatures
    # Wall Materials: Wall, Insulation, Reveal Ins, Concrete, Wood
    # Note: Wall might be bare (2) or insulated (3, 4)
    wall_mats = [MaterialID.WALL, MaterialID.INSULATION, MaterialID.REVEAL_INS, MaterialID.CONCRETE, MaterialID.WOOD]
    min_temp_wall = get_min_surf(temp_frsi, cond_frsi, RSI_CORNER, material_filter=wall_mats)
    
    # MaterialID.FRAME = 5
    # MaterialID.GLASS = 6
    min_temp_frame = get_min_surf(temp_frsi, cond_frsi, RSI_CORNER, material_filter=5)
    min_temp_glass = get_min_surf(temp_frsi, cond_frsi, RSI_CORNER, material_filter=6) 
    
    frsi = (min_temp - TEMP_EXT) / (TEMP_INT - TEMP_EXT)
    
    print(f"  Psi: {psi:.4f} W/mK")
    print(f"  fRsi: {frsi:.4f} (MinT: {min_temp:.2f}C)")
    if min_temp_wall is not None:
        print(f"    Wall MinT: {min_temp_wall:.2f}C")
    if min_temp_frame is not None:
        print(f"    Frame MinT: {min_temp_frame:.2f}C")
    if min_temp_glass is not None:
        print(f"    Glass MinT: {min_temp_glass:.2f}C")
        
    
    # Plot
    plot_temperature_map(temp_frsi, 
                         geom.get_canvas_config().width_mm, 
                         geom.get_canvas_config().height_mm,
                         f"result_{scenario_def['name']}.png", 
                         title=scenario_def['name'],
                         wall_thick_mm=wall_thick_mm,
                         grid_size_mm=getattr(mesh, 'grid_size_mm', None),
                         x_coords=mesh.x_coords,
                         y_coords=mesh.y_coords)
    
    return {
        "name": scenario_def['name'],
        "Psi": psi,
        "fRsi": frsi,
        "MinT": min_temp,
        "MinT_Wall": min_temp_wall,
        "MinT_Frame": min_temp_frame,
        "MinT_Glass": min_temp_glass
    }


def run_scenarios(scenario_indices=None, use_adaptive_mesh=True):
    """Run specific scenarios or all if none specified."""
    get_solver_lib()
    scenarios = get_scenarios()
    
    if scenario_indices:
        # Filter scenarios by 1-based index
        selected = []
        for idx in scenario_indices:
            try:
                i = int(idx) - 1
                if 0 <= i < len(scenarios):
                    selected.append(scenarios[i])
                else:
                    print(f"[WARNING] Scenario index {idx} out of range (1-{len(scenarios)})")
            except ValueError:
                print(f"[WARNING] Invalid scenario index: {idx}")
        
        if not selected:
            print("[ERROR] No valid scenarios selected.")
            return
        to_run = selected
    else:
        to_run = scenarios
    
    results = []
    for sc in to_run:
        res = solve_scenario(sc, use_adaptive_mesh=use_adaptive_mesh)
        results.append(res)
        
    print("\n--- Summary ---")
    print(f"{'Scenario':<40} | {'Psi (W/mK)':<10} | {'fRsi':<10} | {'MinT (C)':<10} | {'Wall T':<10} | {'Frame T':<10} | {'Glass T':<10}")
    print("-" * 115)
    for r in results:
        wall_t = f"{r['MinT_Wall']:.2f}" if r.get('MinT_Wall') is not None else "N/A"
        frame_t = f"{r['MinT_Frame']:.2f}" if r.get('MinT_Frame') is not None else "N/A"
        glass_t = f"{r['MinT_Glass']:.2f}" if r.get('MinT_Glass') is not None else "N/A"
        print(f"{r['name']:<40} | {r['Psi']:<10.4f} | {r['fRsi']:<10.4f} | {r['MinT']:<10.2f} | {wall_t:<10} | {frame_t:<10} | {glass_t:<10}")


def generate_geometries():
    """Generate and save geometry plots for all scenarios (Simulation Skipped)."""
    scenarios = get_scenarios()
    print(f"Generating geometry plots for {len(scenarios)} scenarios...")
    
    for sc in scenarios:
        name = sc['name']
        print(f"  Processing {name}...")
        
        cfg = sc['cfg']
        
        # Instantiate
        if isinstance(cfg, str) and cfg.endswith('.yaml'):
            with open(cfg, 'r') as f:
                data = yaml.safe_load(f)
            geom = DeclarativeGeometry(data)
        else:
            geom = WindowRevealGeometry(cfg)
            
        mesh = AdaptiveMesh(geom)
        mesh.generate()
        
        # Build Grid
        grid_map, _ = build_material_grid(geom, mesh.xc, mesh.yc)
        
        # Filename
        safe_name = name.replace(":", "").replace(" ", "_").replace("(", "").replace(")", "").replace("__", "_")
        filename = f"geometry_check_{safe_name}.png"
        
        print(f"    Mesh: {mesh.info()}")
        
        plot_geometry(grid_map, 
                      geom.get_canvas_config().width_mm, 
                      geom.get_canvas_config().height_mm,
                      filename=filename,
                      x_coords=mesh.x_coords,
                      y_coords=mesh.y_coords)
        print(f"    Saved {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thermal Bridge Simulation Engine")
    parser.add_argument("--geometries-only", action="store_true", help="Generate geometry plots only, skip simulation")
    parser.add_argument("--run-all", action="store_true", help="Run all scenarios")
    parser.add_argument("--scenarios", type=str, help="Comma-separated list of scenario indices to run (e.g. 1,3,5)")
    parser.add_argument("--use-uniform-mesh", action="store_true", help="Use Uniform Mesh instead of Adaptive Mesh")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    
    parser.add_argument("--scenario-file", type=str, help="Path to YAML scenario file to run")
    
    args = parser.parse_args()
    
    if args.list:
        scenarios = get_scenarios()
        print("\nAvailable Scenarios:")
        for i, sc in enumerate(scenarios, 1):
            print(f"  {i}: {sc['name']}")
        exit(0)

    if args.geometries_only:
        generate_geometries()
    else:
        indices = None
        if args.scenarios:
            indices = args.scenarios.split(",")
            
        custom_scenarios = []
        if args.scenario_file:
            # Create a bespoke scenario definition
            fpath = args.scenario_file
            fname = os.path.basename(fpath).replace('.yaml', '')
            custom_scenarios.append({
                "name": fname,
                "file_suffix": fname,
                "cfg": fpath # Pass path string, detected in solve_scenario
            })
            
            # Run custom immediately
            get_solver_lib()
            for sc in custom_scenarios:
                solve_scenario(sc, use_adaptive_mesh=not args.use_uniform_mesh)
        else:    
            run_scenarios(scenario_indices=indices, use_adaptive_mesh=not args.use_uniform_mesh)


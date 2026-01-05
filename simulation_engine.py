"""
Simulation Engine for Thermal Bridge Calculations

Provides scenario definitions and solving workflow for window reveal geometries.
"""

import argparse
import os
import warnings

# Suppress annoying numpy/matplotlib warnings about subnormal floats
warnings.filterwarnings("ignore", message="The value of the smallest subnormal for.* type is zero")

import numpy as np
import matplotlib.pyplot as plt
from config import CalculationConfig, SpacerType, TEMP_INT, TEMP_EXT, RSI_WALL, RSE, RSI_CORNER, MAT_WALL, MAT_INSULATION
from geometry import build_material_grid, build_transient_grid, MaterialID
from mesh import UniformMesh, AdaptiveMesh
from solver import get_solver_lib, solve, solve_transient, calculate_conductances_uniform, plot_temperature_map, plot_geometry
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

# --- Measurement Helpers ---

def probe_temperature(mesh, temp_field, cond, x, y, y_offset=0, x_offset=0):
    """
    Probe temperature at (x, y) according to ISO 10211 rules.
    
    y_offset and x_offset handle padding if the temp_field is larger than the mesh.
    
    IMPORTANT: cond should be the ORIGINAL (unpadded) conductivity array for correct
    ISO 10211 weighting. temp_field may be padded and offset is applied only to it.
    """
    eps = 1e-5
    
    col_candidates = []
    for i in range(mesh.nx):
        if mesh.x_coords[i] <= x + eps and mesh.x_coords[i+1] >= x - eps:
            col_candidates.append(i)
            
    row_candidates = []
    for j in range(mesh.ny):
        if mesh.y_coords[j] <= y + eps and mesh.y_coords[j+1] >= y - eps:
            row_candidates.append(j)
            
    weighted_sum = 0.0
    weight_sum = 0.0
    found_cells = 0
    
    for i in col_candidates:
        for j in row_candidates:
            # cell center
            xc = (mesh.x_coords[i] + mesh.x_coords[i+1]) / 2.0
            yc = (mesh.y_coords[j] + mesh.y_coords[j+1]) / 2.0
            
            s = np.sqrt((x - xc)**2 + (y - yc)**2)
            if s < 1e-9:
                return temp_field[j + y_offset, i + x_offset]
            
            # Use original cond (no offset) for material conductivity weighting
            # Apply offset only to temp_field which may be padded
            lam = cond[j, i]
            t_cell = temp_field[j + y_offset, i + x_offset]
            
            w = lam / s
            weighted_sum += w * t_cell
            weight_sum += w
            found_cells += 1
            
    if found_cells == 0:
        return 0.0
        
    return weighted_sum / weight_sum

def evaluate_measurements(measurements_def, geom, mesh, temp_field, cond, 
                        t_int, t_ext, rsi_used, grid_map, mask_int,
                        y_offset=0, x_offset=0, Gh=None, Gv=None, categories=None):
    """
    Evaluate measurements defined in YAML.
    categories: list of 'point_probes', 'surface_metrics', 'boundary_flux'. None=All.
    """
    results = {}
    if categories is None:
        categories = ['point_probes', 'surface_metrics', 'boundary_flux']
    
    # helper for surface metrics
    def get_surf_metric(t_f, k_f, rsi, boundary_type, material_filter=None):
        # We need a mask that matches the current field shape
        m_int = mask_int
        
        padded = np.pad(m_int, 1)
        # boundary nodes are solid nodes adjacent to internal air
        boundary = (padded[:-2, 1:-1] | padded[2:, 1:-1] | 
                    padded[1:-1, :-2] | padded[1:-1, 2:]) & (~m_int)
        
        # filter by exterior air if needed? usually we want internal surface
        # for window reveal, we filter out external air nodes from boundary
        boundary = boundary & (grid_map != MaterialID.AIR_EXT)
        
        y, x = np.where(boundary)
        if len(y) == 0: return None
        
        if material_filter is not None:
             mats = grid_map[y, x]
             # Handle material names from YAML (converted to IDs)
             mat_ids = []
             for m in material_filter:
                 if isinstance(m, str):
                     if hasattr(MaterialID, m):
                         mat_ids.append(getattr(MaterialID, m))
                     else:
                         print(f"[WARNING] Unknown material in measurements: {m}")
                 else:
                     mat_ids.append(m)
             
             keep = np.isin(mats, mat_ids)
             y, x = y[keep], x[keep]
             if len(y) == 0: return None

        k_solid = k_f[y, x]
        t_node = t_f[y, x]
        
        # dx_local_m. Note: x matches the field shape including x_offset
        # mesh.dx_array is original. so use x - x_offset
        dx_local_m = mesh.dx_array[x - x_offset] / 1000.0
        
        r1 = dx_local_m / (2 * k_solid)
        r2 = rsi
        t_si = (t_int * r1 + t_node * r2) / (r1 + r2)
        
        return t_si # return full array for min/max/avg

    # 1. Point Probes
    if 'point_probes' in categories:
        for p in measurements_def.get('point_probes', []):
            t_val = probe_temperature(mesh, temp_field, cond, p['x'], p['y'], y_offset, x_offset)
            res = {"value": t_val}
            if 'expected' in p:
                res["expected"] = p['expected']
                res["diff"] = abs(t_val - p['expected'])
                res["passed"] = res["diff"] <= p.get('tolerance', 0.1)
            results[p['name']] = res

    # 2. Surface Metrics
    if 'surface_metrics' in categories:
        for s in measurements_def.get('surface_metrics', []):
            mats = s.get('materials')
            t_vals = get_surf_metric(temp_field, cond, rsi_used, s.get('boundary', 'internal'), material_filter=mats)
            
            if t_vals is None or len(t_vals) == 0:
                results[s['name']] = {"value": None}
                continue
                
            mtype = s.get('type', 'min')
            if mtype == 'min': val = np.min(t_vals)
            elif mtype == 'max': val = np.max(t_vals)
            else: val = np.mean(t_vals)
            
            results[s['name']] = {"value": val}

    # 3. Boundary Flux
    if 'boundary_flux' in categories:
        for f in measurements_def.get('boundary_flux', []):
            # Calculate flux at specified boundary
            # If Gv/Gh passed, we can calculate precisely
            flux = 0.0
            boundary = f.get('boundary')
            if boundary == 'bottom' and y_offset > 0 and Gv is not None:
                 # Flux = sum(G * (T_air - T_surf))
                 # Link 0 connects row 0 (Air) and row 1 (Surface)
                 g_row = Gv[0, :]
                 dt = temp_field[0, :] - temp_field[1, :]
                 flow = g_row * dt
                 flux = np.sum(flow)
            
            res = {"value": flux}
            if 'expected' in f:
                res["expected"] = f['expected']
                res["diff"] = abs(flux - f['expected'])
                res["passed"] = res["diff"] <= f.get('tolerance', 0.5)
            results[f['name']] = res
        
    return results

# --- Solver Core ---

def solve_transient_scenario(geom, mesh, temp_init, Gh, Gv, mask, values, grid_map, t_int, t_ext, cfg):
    """
    Run transient simulation and generate animation frames.
    """
    print(f"  [TRANSIENT] Initializing transient solver...")
    print(f"  Duration: {cfg.get('duration_hours', 24)}h, dt: {cfg.get('dt_seconds', 300)}s")
    
    # Build Capacity Grids
    rho, cp = build_transient_grid(geom, grid_map)
    
    # Calculate Node Capacitance [J/K]
    # C = rho * cp * V = rho * cp * dx * dy * 1.0 (assuming 1m depth)
    dx_grid = np.tile(mesh.dx_array, (mesh.ny, 1)) / 1000.0 # meters
    dy_grid = np.tile(mesh.dy_array[:, None], (1, mesh.nx)) / 1000.0 # meters
    
    capacitance = rho * cp * dx_grid * dy_grid
    
    # Time loop
    dt = float(cfg.get('dt_seconds', 300))
    duration_s = float(cfg.get('duration_hours', 24)) * 3600.0
    steps = int(duration_s / dt)
    save_interval = int(cfg.get('save_interval_steps', 1))
    
    temp = temp_init.copy()
    temp_prev = temp_init.copy()
    
    import time
    start_time = time.time()
    
    # Prepare result storage
    frames = []
    
    for step in range(steps):
        # Update temp (Implicit Euler)
        temp_prev[:] = temp[:]
        
        # Call optimized C++ solver
        temp = solve_transient(temp, temp_prev, Gh, Gv, capacitance, mask, values, dt,
                               max_iter=100, tol=1e-4, omega=1.0)
        
        if step % 10 == 0:
            print(f"    Step {step}/{steps} (t={step*dt/3600:.1f}h)...", end='\r')
            
        if step % save_interval == 0 or step == steps - 1:
            # Generate snapshot logic
            # To avoid excessive plotting overhead, we only plot if interval is reasonable
            # OR we just collect arrays and plot later? Plotting later consumes memory.
            # Let's plot now.
            fname = f"result_{geom.data.get('name', 'transient')}_step_{step:04d}.png"
            title = f"Transient State t={step*dt/3600:.1f}h"
            
            # Use matplotlib to render frame to buffer for GIF
            try:
                from PIL import Image
                import io
                
                # Create figure but don't save to disk unless requested?
                # For now let's just collect for GIF and save a few keyframes
                # We reuse plot_temperature_map but we need it to return image or save to buffer
                # Provide a hook or just do it manually here
                
                # Simplified plot for animation
                fig, ax = plt.subplots(figsize=(8, 6))
                im = ax.imshow(temp, cmap='jet', origin='lower', animated=True)
                ax.set_title(title)
                ax.axis('off')
                
                # Save to buffer
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=80)
                plt.close(fig)
                buf.seek(0)
                frames.append(Image.open(buf))
            except ImportError:
                 pass
            
    elapsed = time.time() - start_time
    print(f"\n  [TRANSIENT] Completed in {elapsed:.2f}s")
    
    # Save GIF
    if frames:
        gif_name = f"result_{geom.data.get('name', 'transient')}.gif"
        print(f"  Saving animation to {gif_name}...")
        frames[0].save(gif_name, save_all=True, append_images=frames[1:], optimize=True, duration=100, loop=0)
    
    # Plot final state
    plot_temperature_map(temp, 
                         geom.get_canvas_config().width_mm, 
                         geom.get_canvas_config().height_mm,
                         f"result_{geom.data.get('name', 'transient')}_final.png", 
                         title=f"Transient End State (t={duration_s/3600:.1f}h)",
                         wall_thick_mm=geom.data.get('variables', {}).get('wall_thick', 360))
                         
    return {
        "name": geom.data.get('name', 'transient'),
        "measurements": {"EndTemp": {"value": np.mean(temp)}},
        "final_temp": temp
    }


def solve_scenario(scenario_def, use_adaptive_mesh=True, progress_callback=None):
    """Solve a thermal bridge scenario and return results."""
    print(f"\nrunning {scenario_def['name']}...")
    cfg = scenario_def['cfg']
    suffix = scenario_def['file_suffix']
    
    # Load Geometry
    # Load Geometry
    if isinstance(cfg, str) and cfg.endswith('.yaml'):
         # Load Declarative
         with open(cfg, 'r') as f:
             data = yaml.safe_load(f)
    elif isinstance(cfg, dict):
        data = cfg
    else:
        raise ValueError(f"Unsupported config type: {type(cfg)}. Expected YAML file path or dict.")

    geom = DeclarativeGeometry(data)
    # Extract grid size from resolved data in geom
    grid_sz = 2.5
    if 'canvas' in geom.data and 'grid' in geom.data['canvas']:
        grid_sz = float(geom.data['canvas']['grid'])
    cfg_grid_size = grid_sz
    wall_thick_mm = geom.data.get('variables', {}).get('wall_thick', 360)
    
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
    
    # Store original cond for ISO 10211 probe temperature calculations
    # (probing should use actual material conductivities, not padded air values)
    cond_original = cond.copy()
    
    # --- Auto-Padding for Convective BCs (ISO Case 2 Support) ---
    bcs = geom.data.get('boundary_conditions', {})
    conv_bcs = bcs.get('convective', {})
    
    pad_top = 'top' in conv_bcs
    pad_bottom = 'bottom' in conv_bcs
    pad_left = 'left' in conv_bcs
    pad_right = 'right' in conv_bcs
    
    has_padding = any([pad_top, pad_bottom, pad_left, pad_right])
    
    original_ny, original_nx = cond.shape
    
    # Initialize overrides list (Fixes NameError)
    explicit_mask_overrides = []
    y_off, x_off = 0, 0
    dx_array = mesh.dx_array
    dy_array = mesh.dy_array
    
    if has_padding:
        print("  [Auto-Padding] Extending domain for convective boundaries...")
        # New dimensions
        ny_new = original_ny + (1 if pad_top else 0) + (1 if pad_bottom else 0)
        nx_new = original_nx + (1 if pad_left else 0) + (1 if pad_right else 0)
        
        # Offsets
        y_off = 1 if pad_bottom else 0
        x_off = 1 if pad_left else 0
        
        # Pad Cond
        cond_new = np.ones((ny_new, nx_new)) * 0.025 # Default air
        cond_new[y_off:y_off+original_ny, x_off:x_off+original_nx] = cond
        cond = cond_new
        
        # Pad GridMap 
        grid_map_new = np.full((ny_new, nx_new), MaterialID.AIR_EXT, dtype=int)
        grid_map_new[y_off:y_off+original_ny, x_off:x_off+original_nx] = grid_map
        
        # Set specific sides to INT/EXT based on T
        if pad_bottom:
             T_val = float(conv_bcs['bottom'].get('T', 20.0))
             mat = MaterialID.AIR_INT if T_val > 10.0 else MaterialID.AIR_EXT
             grid_map_new[0, :] = mat
        if pad_top:
             T_val = float(conv_bcs['top'].get('T', 0.0))
             mat = MaterialID.AIR_INT if T_val > 10.0 else MaterialID.AIR_EXT
             grid_map_new[-1, :] = mat
        if pad_left:
             T_val = float(conv_bcs['left'].get('T', 20.0))
             mat = MaterialID.AIR_INT if T_val > 10.0 else MaterialID.AIR_EXT
             grid_map_new[:, 0] = mat
        if pad_right:
             T_val = float(conv_bcs['right'].get('T', 0.0))
             mat = MaterialID.AIR_INT if T_val > 10.0 else MaterialID.AIR_EXT
             grid_map_new[:, -1] = mat
             
        grid_map = grid_map_new
        
        # Pad dx/dy
        if pad_left: dx_array = np.insert(dx_array, 0, 1.0)
        if pad_right: dx_array = np.append(dx_array, 1.0)
        if pad_bottom: dy_array = np.insert(dy_array, 0, 1.0)
        if pad_top: dy_array = np.append(dy_array, 1.0)
    # -----------------------------------------------------------
    
    # 3. Boundary Conditions & Solver Setup
    
    # Defaults
    t_int = TEMP_INT # 20.0
    t_ext = TEMP_EXT # -5.0
    rsi_design = RSI_WALL # 0.13
    rse = RSE # 0.04
    rsi_check = RSI_CORNER # 0.25
    
    # Check for overrides in YAML
    # Expecting structure: boundary_conditions: convective: { internal: {T:.., R:..}, ... }
    bcs = {}
    if hasattr(geom, 'get_boundary_conditions'):
        bcs = geom.get_boundary_conditions() or {}
        
    if 'convective' in bcs:
        conv = bcs['convective']
        
        # Generic Parsing for T and R from all sides
        for side, params in conv.items():
            if not isinstance(params, dict): continue
            
            t_val = float(params.get('T', 20.0))
            r_val = float(params.get('R', RSI_WALL))
            
            # Heuristic: Warm side is Internal (>10C)
            if t_val > 10.0:
                t_int = t_val
                if 'R' in params: rsi_design = r_val
            else:
                t_ext = t_val
                if 'R' in params: rse = r_val
        
        # Explicit Overrides (legacy/specific support)
        if 'internal' in conv:
            t_int = float(conv['internal'].get('T', t_int))
            rsi_design = float(conv['internal'].get('R', rsi_design))
        if 'external' in conv:
            t_ext = float(conv['external'].get('T', t_ext))
            rse = float(conv['external'].get('R', rse))
        if 'internal_check' in conv:
            rsi_check = float(conv['internal_check'].get('R', rsi_check))
    
    mask_int = (grid_map == MaterialID.AIR_INT)
    mask_ext = (grid_map == MaterialID.AIR_EXT)
    
    # Vectorized K_eff calculation
    # k_eff = dx / (2 * R) where dx is the width of the cell
    # NOTE: dx_array may have been extended by auto-padding, use the updated array
    dx_grid = np.tile(dx_array, (cond.shape[0], 1))
    
    # We set K for Pass 1 (Design Rsi)
    k_eff_int_design = (dx_grid / 1000.0) / (2 * rsi_design)
    k_eff_ext = (dx_grid / 1000.0) / (2 * rse)
    
    cond_pass1 = cond.copy()
    cond_pass1[mask_int] = k_eff_int_design[mask_int]
    cond_pass1[mask_ext] = k_eff_ext[mask_ext]
    

    from solver import calculate_conductances
    
    # For padded scenarios (ISO Case 2 style), use original cond values instead of k_eff
    # since we explicitly override boundary conductances. The k_eff approach is for
    # internal air regions in scenarios 1-11, not for explicit boundary layer padding.
    if has_padding:
        Gh, Gv = calculate_conductances(cond, dx_array, dy_array)
    else:
        Gh, Gv = calculate_conductances(cond_pass1, dx_array, dy_array)
    
    # Explicit Boundary Conductance Overrides for Convective BCs (ISO Case 2 Compatibility)
    # When we have padding, explicitly set boundary conductances to match ISO 10211 requirements
    if has_padding:
        dx_m = dx_array / 1000.0
        
        # Bottom Boundary (if padded)
        if pad_bottom:
            # Link index 0 connects row 0 (air) and row 1 (surface)
            # G = Area / R = dx / RSI
            r_bottom = float(conv_bcs.get('bottom', {}).get('R', rsi_design))
            Gv[0, :] = dx_m / r_bottom
            # Disable lateral flow in bottom air layer
            Gh[0, :] = 0.0
            
        # Top Boundary (if padded)
        if pad_top:
            # Link at ny_new-2 connects row (ny_new-2) and row (ny_new-1)
            # where ny_new-1 is the top air layer
            r_top = float(conv_bcs.get('top', {}).get('R', rse))
            Gv[cond.shape[0]-2, :] = dx_m / r_top
            # Disable lateral flow in top air layer
            Gh[cond.shape[0]-1, :] = 0.0
            
        # Left/Right boundaries (if needed in future)
        # For now ISO Case 2 only uses top/bottom
    
    # Correction for Anisotropic Mesh at Boundaries
    def apply_boundary_conductances(Gh, Gv, rsi, mask_air):

        # Horizontal Interfaces: (i, j) connects j and j+1
        # 1. Air at Left (j), Solid at Right (j+1)
        # mask is (ny, nx), Gh is (ny, nx) [last col unused usually or periodic]
        # We perform vectorized update.
        
        # Use padded arrays from local scope
        dx_m = dx_array / 1000.0
        dy_m = dy_array / 1000.0
        
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
    # Skip if we have padding - explicit conductances already set above
    if not has_padding:
        apply_boundary_conductances(Gh, Gv, rsi_design, mask_int)
        apply_boundary_conductances(Gh, Gv, rse, mask_ext)

    
    # 5. Solve (Pass 1: Rsi=0.13 for Psi)
    mask = mask_int | mask_ext
    values = np.zeros_like(cond)
    values[mask_int] = t_int
    values[mask_ext] = t_ext

    # --- Apply Explicit Boundary Conditions from YAML ---
    # This allows ISO tests and custom geometries to override defaults
    if 'dirichlet' in bcs:
        d_bcs = bcs['dirichlet']
        if 'top' in d_bcs:
            mask[-1, :] = 1
            values[-1, :] = float(d_bcs['top'])
        if 'bottom' in d_bcs:
            mask[0, :] = 1
            values[0, :] = float(d_bcs['bottom'])
        if 'left' in d_bcs:
            mask[:, 0] = 1
            values[:, 0] = float(d_bcs['left'])
        if 'right' in d_bcs:
            mask[:, -1] = 1
            values[:, -1] = float(d_bcs['right'])


    if 'adiabatic' in bcs:
        # Adiabatic means flux=0, which is natural BC in FEM/FDM if not in mask.
        a_bcs = bcs['adiabatic'] # List of sides e.g. ['left', 'top']
        if isinstance(a_bcs, list):
            if 'top' in a_bcs:
                mask[-1, :] = 0
            if 'bottom' in a_bcs:
                mask[0, :] = 0
            if 'left' in a_bcs:
                mask[:, 0] = 0
            if 'right' in a_bcs:
                mask[:, -1] = 0
    # ----------------------------------------------------
    
    # intelligent Initialization
    # Check if we have opposing boundaries to establish a gradient
    if pad_bottom and pad_top:
        # Vertical Gradient
        t_b = float(conv_bcs.get('bottom', {}).get('T', t_int))
        t_t = float(conv_bcs.get('top', {}).get('T', t_ext))
        temp = np.linspace(t_b, t_t, cond.shape[0])[:, None] * np.ones((1, cond.shape[1]))
    elif pad_left and pad_right:
        # Horizontal Gradient
        t_l = float(conv_bcs.get('left', {}).get('T', t_int))
        t_r = float(conv_bcs.get('right', {}).get('T', t_ext))
        temp = np.linspace(t_l, t_r, cond.shape[1])[None, :] * np.ones((cond.shape[0], 1))
    else:
        # Flat fallback
        temp = np.ones_like(cond) * (t_int + t_ext) / 2.0

    temp[mask_int] = t_int
    temp[mask_ext] = t_ext
    
    # Apply strict boundary conditions from Dirichlet config (ISO tests etc.)
    # This ensures the solver sees the boundary values immediately in the first iteration
    temp[mask == 1] = values[mask == 1]
    
    # --- Transient Simulation Dispatch ---
    trans_cfg = geom.data.get('transient', {})
    if trans_cfg.get('enabled'):
        return solve_transient_scenario(geom, mesh, temp, Gh, Gv, mask, values, grid_map, t_int, t_ext, trans_cfg)
    
    # Pass 1: Solve for Psi (Standard Rsi = 0.13)
    print(f"  [PASS 1] Solving for Psi-value (Rsi={rsi_design})...")
    
    cb1 = None
    if progress_callback:
        cb1 = lambda s, t, d: progress_callback("Pass 1: Psi-Value", s, t, d)

    temp_res = solve(temp, Gh, Gv, mask, values, max_iter=500000, tol=1e-7, 
                     batch_size=10000, verbose=True, progress_callback=cb1)
    
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
    
    l2d = flux / (t_int - t_ext)
    
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
    
    # --- Measurements ---
    measurements_def = geom.data.get('measurements', {})

    # Pass 2 (fRsi) - Optional
    derived = measurements_def.get('derived', [])
    needs_frsi = any(d.get('formula') == 'frsi' or d.get('name') == 'fRsi' for d in derived)
    
    p2_results = {}
    temp_frsi = temp_res # fallback
    
    if needs_frsi:
        # fRsi Pass (Rsi=0.25)
        k_eff_int_rsi25 = (dx_grid / 1000.0) / (2 * rsi_check)
        cond_frsi = cond.copy()
        cond_frsi[mask_int] = k_eff_int_rsi25[mask_int]
        
        Gh_frsi, Gv_frsi = calculate_conductances(cond_frsi, dx_array, dy_array)
        
        # Corrections
        apply_boundary_conductances(Gh_frsi, Gv_frsi, rsi_check, mask_int)
        apply_boundary_conductances(Gh_frsi, Gv_frsi, rse, mask_ext)
        
        print(f"  [PASS 2] Solving for fRsi/MinT (Rsi={rsi_check})...")
        
        cb2 = None
        if progress_callback:
            cb2 = lambda s, t, d: progress_callback("Pass 2: fRsi/MinT", s, t, d)

        temp_frsi = temp_res.copy()
        temp_frsi = solve(temp_frsi, Gh_frsi, Gv_frsi, mask, values, max_iter=500000, 
                          tol=1e-7, batch_size=10000, verbose=True, progress_callback=cb2)
        
        p2_results = evaluate_measurements(measurements_def, geom, mesh, temp_frsi, cond_frsi,
                                         t_int, t_ext, rsi_check, grid_map, mask_int,
                                         y_off, x_off, categories=['surface_metrics'])
    else:
        print("  [Pass 2] Skipped (No fRsi requested).")
    
    # Pass 1 measurements (for Psi)
    
    # Pass 1 measurements (for Psi)
    # Validation checkpoints and Flux should be checked against Design conditions
    # Use original 'cond' for probing (ISO 10211 methodology), not padded cond with air values
    p1_results = evaluate_measurements(measurements_def, geom, mesh, temp_res, cond_original,
                                     t_int, t_ext, rsi_design, grid_map, mask_int,
                                     y_off, x_off, Gh=Gh, Gv=Gv,
                                     categories=['point_probes', 'boundary_flux'])
    
    # manual flux calculation for Psi fallback
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
    
    l2d = flux / (t_int - t_ext)
    
    # Reference Flow for Psi
    l_wall = 0.25
    l_win = 0.25
    vars = geom.data.get('variables', {})
    f_width = float(vars.get('frame_width', 70))
    wall_th = float(vars.get('wall_thick', 360))
    ins_th = float(vars.get('ins_thick_max', 0))
    
    l_frame = f_width / 1000.0
    l_glass = l_win - l_frame
    r_wall_1d = RSI_WALL + (wall_th/1000.0)/MAT_WALL + RSE
    if ins_th > 0: r_wall_1d += (ins_th/1000.0)/MAT_INSULATION
    u_wall_1d = 1.0 / r_wall_1d
    u_frame, u_glass = 1.3, 1.1
    ref_flow = u_wall_1d * l_wall + u_frame * l_frame + u_glass * l_glass
    psi = l2d - ref_flow


    
    # Print results
    print("\n  --- Measurement Results ---")
    combined_results = {**p1_results, **p2_results}
    
    # Handle explicit derived formulas
    for d in measurements_def.get('derived', []):
        if d['formula'] == 'psi_value':
            combined_results[d['name']] = {"value": psi}
            print(f"    {d['name']}: {psi:.4f} W/mK")
        elif d['formula'] == 'frsi':
            min_t = TEMP_INT
            found_min = False
            for name, res in combined_results.items():
                if res.get('value') is not None and any(x in name for x in ["MinT", "Checkpoint"]):
                    min_t = min(min_t, res['value'])
                    found_min = True
            
            frsi_val = (min_t - t_ext) / (t_int - t_ext)
            combined_results[d['name']] = {"value": frsi_val, "min_t": min_t}
            print(f"    {d['name']}: {frsi_val:.4f} (MinT: {min_t:.2f}C)")

    # Print Point Probes and Fluxes
    for name, res in combined_results.items():
        if "expected" in res:
            status = "PASS" if res.get("passed") else "FAIL"
            print(f"    {name}: {res['value']:.4f} (Expected: {res['expected']:.4f}) -> {status}")
        elif "value" in res and res["value"] is not None and name not in ["Psi", "fRsi"]:
             print(f"    {name}: {res['value']:.2f}")

    # Plotting
    if has_padding:
        y_end = temp_frsi.shape[0] - (1 if pad_top else 0)
        x_end = temp_frsi.shape[1] - (1 if pad_right else 0)
        temp_for_plot = temp_frsi[y_off:y_end, x_off:x_end]
    else:
        temp_for_plot = temp_frsi

    
    # Format Title to include Temperature Setup
    plot_title = f"{scenario_def['name']}\n(Ti={t_int}°C, Te={t_ext}°C)"

    plot_temperature_map(temp_for_plot, 
                         geom.get_canvas_config().width_mm, 
                         geom.get_canvas_config().height_mm,
                         f"result_{scenario_def['name']}.png", 
                         title=plot_title,
                         wall_thick_mm=wall_th,
                         grid_size_mm=getattr(mesh, 'grid_size_mm', None),
                         x_coords=mesh.x_coords,
                         y_coords=mesh.y_coords)
    
    return {
        "name": scenario_def['name'],
        "measurements": combined_results
    }


def run_scenarios(scenario_indices=None, use_adaptive_mesh=True):
    """Run specific scenarios or all if none specified."""
    get_solver_lib()
    scenarios = get_scenarios()
    
    if scenario_indices:
        selected = []
        for idx in scenario_indices:
            try:
                i = int(idx) - 1
                if 0 <= i < len(scenarios):
                    selected.append(scenarios[i])
            except ValueError: pass
        to_run = selected or scenarios
    else:
        to_run = scenarios
    
    results = []
    for sc in to_run:
        res = solve_scenario(sc, use_adaptive_mesh=use_adaptive_mesh)
        results.append(res)
        
    print("\n--- Summary ---")
    # Identify unique measurement names across all results to build table header
    all_keys = set()
    for r in results:
        if 'measurements' in r:
            all_keys.update(r['measurements'].keys())
            
    sorted_keys = sorted(list(all_keys))
    
    header = f"{'Scenario':<40}"
    for k in sorted_keys: header += f" | {k:<10}"
    print(header)
    print("-" * len(header))
    
    for r in results:
        line = f"{r['name']:<40}"
        measurements = r.get('measurements', {})
        for k in sorted_keys:
            if k in measurements:
                val = measurements[k].get('value')
                if val is None: line += f" | {'N/A':<10}"
                elif isinstance(val, (int, float)): line += f" | {val:<10.3f}"
                else: line += f" | {str(val):<10}"
            else:
                line += f" | {'-':<10}"
        print(line)



def generate_geometries(scenarios=None):
    """Generate and save geometry plots for all scenarios (Simulation Skipped)."""
    if scenarios is None:
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
            raise ValueError(f"Unsupported config type: {type(cfg)}. Expected YAML file path.")
            
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
        target_scenarios = None
        if args.scenario_file:
            fpath = args.scenario_file
            fname = os.path.basename(fpath).replace('.yaml', '')
            target_scenarios = [{
                "name": fname,
                "file_suffix": fname,
                "cfg": fpath
            }]
        
        generate_geometries(target_scenarios)
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


import numpy as np
import matplotlib.pyplot as plt
import scipy.ndimage as nd
from typing import List, Tuple, Dict
from config import *

class ThermalSolver:
    def __init__(self, config: CalculationConfig, rsi_value: float = 0.13):
        self.cfg = config
        self.rsi_value = rsi_value # Store Dynamic Rsi
        self.dx = self.cfg.grid_size_mm / 1000.0  # meters
        
        # Calculate domain size
        # Wall section needs to be long enough to reach 1D flow (e.g. 1m)
        self.wall_length = 1.0 
        self.insulation_length = 1.0 # perpendicular
        
        # Grid dimensions approx
        self.W = int((self.wall_length + 0.5) / self.dx) # Width
        self.H = int((1.0) / self.dx) # Height (arbitrary sufficient depth)
        
        # Define domain bounds relative to the corner
        # Let's handle coordinates: x=0 is the masonry corner.
        # x<0 is wall/interior, x>0 is infinite wall (cut off)
        # y=0 is the masonry outer face. y<0 is interior, y>0 is exterior insulation
        
        # Actually standard cartesian grid:
        # Define ranges in mm
        self.L_wall_interior = 1000 # mm, length of wall leg
        self.L_window_leg = 1000 # mm, length of window/facade leg
        
        # Canvas Size
        self.offset_x_mm = 50 # Buffer for Internal Air
        self.width_mm = self.offset_x_mm + self.cfg.wall_thickness_mm + self.cfg.insulation_thick_max_mm + 500 # Extra for boundary
        self.height_mm = self.L_window_leg
        
        self.nx = int(self.width_mm / self.cfg.grid_size_mm) + 1  # X direction (Thickness)
        self.ny = int(self.L_window_leg / self.cfg.grid_size_mm) + 1 # Y direction (Length along facade)
        
        self.grid_map = np.zeros((self.ny, self.nx), dtype=int) # Material ID
        self.temp = np.ones((self.ny, self.nx)) * TEMP_INT # Initial guess
        self.cond = np.zeros((self.ny, self.nx))
        
        # IDs
        self.ID_AIR_INT = 0
        self.ID_AIR_EXT = 1
        self.ID_WALL = 2
        self.ID_INSULATION = 3
        self.ID_FRAME = 4
        self.ID_GLASS = 5
        self.ID_REVEAL_INS = 6
        self.ID_SPACER = 7 # New ID

        self.setup_geometry()
        self.assign_materials()

    def setup_geometry(self):
        # Coordinates mapping
        # Let x=0 be the INTERIOR surface of the wall?
        # Let's align:
        # x range: [0, width_mm]
        # Wall spans from x=0 to x=wall_thickness
        # Insulation spans from x=wall_thickness to x=wall_thickness + ins_thickness
        
        # Geometry Construction
        # 1. Base Wall (Masonry)
        w_th = self.cfg.wall_thickness_mm
        # Since grid uses indices, let's map mm to indices
        to_idx = lambda mm: int(mm / (self.dx * 1000))
        
        # Geometry Construction
        # 1. Base Wall (Masonry)
        # w_th = self.cfg.wall_thickness_mm (already defined)
        
        offset = to_idx(self.offset_x_mm)
        
        idx_w_inner = offset
        idx_w_outer = offset + to_idx(w_th)
        idx_ins_max = offset + to_idx(w_th + self.cfg.insulation_thick_max_mm)
        reveal_y_mm = 500
        idx_reveal_edge = to_idx(reveal_y_mm)
        
        # 0. Initialize Grid
        # Default is ID_AIR_INT (0)
        # We need to mark ID_AIR_EXT (1)
        # Logic: Calculate the Exterior Boundary Line (X) for each Y
        
        # We can do this After placing materials, or Before?
        # Let's do it by iterating Y.
        
        # idx_taper_start = max(0, to_idx(reveal_y_mm - self.cfg.taper_length_mm)) # Fixed: Safety clamp
        # idx_ins_base_min = to_idx(w_th + self.cfg.insulation_thick_min_mm)
        
        # --- FIX 1: Consistent Window Position Logic ---
        pos_mm = max(0, self.cfg.window_position_from_exterior_masonry_mm)
        idx_pos = to_idx(pos_mm)
        
        # Define Outer Face of Window (shifted inwards from masonry outer face)
        idx_win_outer_face = idx_w_outer - idx_pos
        # Safety: Window cannot actally start before inner masonry face
        idx_win_outer_face = max(idx_w_inner + 1, idx_win_outer_face)
        
        # Frame coordinates based on this new reference
        # Make sure definitions are available
        f_depth_idx = to_idx(self.cfg.frame_depth_mm)
        f_width_idx = to_idx(self.cfg.frame_width_mm)
        
        idx_f_x_end = idx_win_outer_face
        idx_f_x_start = idx_f_x_end - f_depth_idx
        
        # FIX: Constant Frame Start Y (15mm gap)
        # Allows insulation to overlap frame instead of shifting frame
        # FIX: Constant Frame Start Y (Flush with Reveal Edge)
        # Fix "Hole" under frame: Frame should touch the masonry reveal.
        idx_f_y_start = idx_reveal_edge 
        idx_f_y_end = idx_f_y_start + f_width_idx
        
        # Glass Indices (Generic) based on frame
        g_thick_idx = to_idx(24)
        # idx_g_x_mid = int((idx_f_x_start + idx_f_x_end) / 2) # used later for sash
        
        # --- FIX 2: Single Placement of Frame/Glass ---
        # FIX: RESTORING MISSING WALL AND INSULATION LOGIC
        
        # 1. Fill basic Masonry Wall (up to reveal edge)
        # From y=0 to y=reveal_edge, x=0 to x=w_outer
        self.grid_map[0:idx_reveal_edge, idx_w_inner:idx_w_outer] = self.ID_WALL
        
        # 2. Base Insulation (Exterior WDVS)
        # Taper Logic Revised (Fix 3: Flush with Rebate):
        idx_ins_corner = idx_reveal_edge
        if self.cfg.masonry_rebate_overlap_mm > 0:
             idx_ins_corner += to_idx(self.cfg.masonry_rebate_overlap_mm)
        
        idx_taper_start = to_idx(reveal_y_mm - self.cfg.taper_length_mm)
        
        for y in range(0, idx_ins_corner):
            # Determine max x for insulation at this y
            if y < idx_taper_start:
                # Full thickness
                current_max_x = idx_ins_max
            else:
                # Tapering
                # fraction (0 to 1) from start to edge
                f = (y - idx_taper_start) / (idx_ins_corner - idx_taper_start)
                th = self.cfg.insulation_thick_max_mm - f * (self.cfg.insulation_thick_max_mm - self.cfg.insulation_thick_min_mm)
                current_max_x = offset + to_idx(w_th + th)
            
            # Fill Insulation
            self.grid_map[y, idx_w_outer:current_max_x] = self.ID_INSULATION
            
        # 3. Handle Rebate Overlap (Masonry) - This is done later in "Re-Apply Masonry Rebate"?
        # Or should we do it now?
        # The logic later (lines ~440) does: grid_map[rebate] = ID_WALL.
        # That logic relies on 'idx_reveal_edge' and 'idx_win_outer_face'.
        # That is robust.

        # 5. Reveal Insulation (The thin part)
        # Location: On the reveal face of the wall (the end of the wall at y=reveal_edge).
        
        rev_ins_th_idx = to_idx(self.cfg.reveal_insulation_mm)
        
        if self.cfg.masonry_rebate_overlap_mm > 0:
             # Rebate Geometry: Masonry extends in front of the frame
             idx_reb_y_start = idx_reveal_edge
             idx_reb_y_end = idx_reveal_edge + to_idx(self.cfg.masonry_rebate_overlap_mm)
             idx_reb_x_start = idx_win_outer_face
             idx_reb_x_end = idx_w_outer
             
             # Fill Rebate with Wall Material
             self.grid_map[idx_reb_y_start:idx_reb_y_end, idx_reb_x_start:idx_reb_x_end] = self.ID_WALL
             
        
        # --- FIX 2 (Placement): Now place Window Frame & Glass ---
        
        # 1. Place Frame (Fixed Frame + Sash)
        # Dimensions (Standardized)
        fixed_frame_width = 60 # Blendrahmen width (Face)
        fixed_frame_depth = 70 # Blendrahmen depth
        sash_width = 70        # Flügel width (Face)
        sash_depth = 70        # Flügel depth
        overlap = 10           # Overlap between Fixed and Sash
        
        # Fixed Frame Position:
        # Y: Starts at idx_f_y_start (15mm from reveal). Ends at + fixed_frame_width.
        # X: Outer face flush with window pos? Yes.
        idx_ff_y_start = idx_f_y_start
        idx_ff_y_end = idx_ff_y_start + to_idx(fixed_frame_width)
        idx_ff_x_end = idx_f_x_end # Outer face (flush)
        idx_ff_x_start = idx_ff_x_end - to_idx(fixed_frame_depth)
        
        # Sash Position:
        idx_sash_y_start = idx_ff_y_end - to_idx(overlap) # Overlap
        idx_sash_y_end = idx_sash_y_start + to_idx(sash_width)
        # Better: Recess Sash by 30mm from Fixed Frame outer face (User Request "More to inside").
        idx_sash_x_end = idx_ff_x_end - to_idx(30)
        idx_sash_x_start = idx_sash_x_end - to_idx(sash_depth)
        
        # Draw Fixed Frame
        self.grid_map[idx_ff_y_start:idx_ff_y_end, idx_ff_x_start:idx_ff_x_end] = self.ID_FRAME
        
        # EXTENSION: Universal Blendrahmen Extension (L-Profile)
        # To maintain consistency across all cases and fill the gap behind the Recessed Sash.
        # Extends Y from ff_y_end (60mm) to cover the Sash Recess/Insulation Zone.
        # Let's target 80mm visible height (from reveal edge).
        ext_y_end = idx_reveal_edge + to_idx(80) # Target 80mm coverage
        ext_y_start = idx_ff_y_end
        
        # Extends X from Sash Outer Face to Frame Outer Face
        ext_x_start = idx_sash_x_end
        ext_x_end = idx_win_outer_face
        
        if ext_y_end > ext_y_start and ext_x_end > ext_x_start:
             self.grid_map[ext_y_start:ext_y_end, ext_x_start:ext_x_end] = self.ID_FRAME

        # Draw Sash
        self.grid_map[idx_sash_y_start:idx_sash_y_end, idx_sash_x_start:idx_sash_x_end] = self.ID_FRAME

        # Glass Position:
        # Centered in Sash
        idx_g_x_mid = int((idx_sash_x_start + idx_sash_x_end) / 2)
        idx_g_x_start = idx_g_x_mid - int(to_idx(24)/2)
        idx_g_x_end = idx_g_x_mid + int(to_idx(24)/2)
        
        # Glass Y: Starts inside Sash
        idx_g_y_start = idx_sash_y_start + to_idx(10) # Frame overlap
        # Extends to... end of domain
        idx_g_y_end = self.ny
        
        # Draw Glass
        self.grid_map[idx_g_y_start:idx_g_y_end, idx_g_x_start:idx_g_x_end] = self.ID_GLASS

        # 3b. Determine Effective Spacer Conductivity
        spacer_lambda = 0.0
        if self.cfg.spacer_type == SpacerType.SWISS_ULTIMATE:
            spacer_lambda = MAT_SPACER_SWISS_ULTIMATE
        elif self.cfg.spacer_type == SpacerType.STAINLESS_STEEL:
            spacer_lambda = MAT_SPACER_STAINLESS
        elif self.cfg.spacer_type == SpacerType.ALUMINUM:
            spacer_lambda = MAT_SPACER_ALUMINUM
        
        # Draw Spacer?
        # Only if we have a valid spacer type
        if self.cfg.spacer_type != SpacerType.NONE:
            # Spacer Dimensions (Generic IGU Box)
            # Located at the bottom of the glass unit, inside the sash.
            # Height: 7mm
            # Width: Space between panes... wait, we modeled glass as a solid block.
            # In a solid block model, the "Spacer" effectively replaces the bottom X mm of grid cells of the "Glass" block.
            
            spacer_height_mm = 7
            idx_spacer_h = to_idx(spacer_height_mm)
            
            # Repaint the bottom of the GLASS block as SPACER
            # Start from glass bottom (idx_g_y_start)
            idx_sp_y_end = idx_g_y_start + idx_spacer_h
            
            # Bounds
            sp_x_start = idx_g_x_start
            sp_x_end = idx_g_x_end
            
            # We need a new ID for Spacer? Material check assigns conductivity.
            # Let's use a dynamic approach. We can reuse ID_GLASS but that treats it as Ug1.1
            # We need a new ID.
            # Let's add ID_SPACER to class in __init__?
            # Or just hack it: defined below as 7.
            
            self.grid_map[idx_g_y_start:idx_sp_y_end, sp_x_start:sp_x_end] = 7 # ID_SPACER
        
        # 4. Re-Apply Masonry Rebate (The "Anschlag" itself)
        # This ensures the masonry covers the frame where it should.
        if self.cfg.masonry_rebate_overlap_mm > 0:
             idx_reb_y_start = idx_reveal_edge
             idx_reb_y_end = idx_reveal_edge + to_idx(self.cfg.masonry_rebate_overlap_mm)
             idx_reb_x_start = idx_win_outer_face
             idx_reb_x_end = idx_w_outer
             
             # Overwrite Frame with Masonry in the Rebate Zone
             self.grid_map[idx_reb_y_start:idx_reb_y_end, idx_reb_x_start:idx_reb_x_end] = self.ID_WALL

        # 5. Reveal Insulation (The thin part)
        # FIX: Simplified Rectangle Logic per User Request
        # (Placed AFTER Rebate to potentially optimize/replace parts of it)
        if self.cfg.reveal_insulation_mm > 0 and not self.cfg.uninsulated_reveal:
             # DEBUG: Force Fill Rebate Zone with Wall first to prevent "Hoyle"
             # Even though Section 4 should have done it, we do it again here.
             idx_reb_y_start = idx_reveal_edge
             idx_reb_y_end = idx_reveal_edge + to_idx(self.cfg.masonry_rebate_overlap_mm)
             idx_reb_x_start = idx_win_outer_face
             idx_reb_x_end = idx_w_outer
             self.grid_map[idx_reb_y_start:idx_reb_y_end, idx_reb_x_start:idx_reb_x_end] = self.ID_WALL
            
             rev_ins_th_idx = to_idx(self.cfg.reveal_insulation_mm)
            
             # Y Range: User says "Higher up on Y-axis... On the outside".
             rebate_offset = 0
             if self.cfg.masonry_rebate_overlap_mm > 0:
                 rebate_offset = to_idx(self.cfg.masonry_rebate_overlap_mm)
            
             ri_y_start = idx_reveal_edge + rebate_offset # Sits ON the rebate tip
             ri_y_end = ri_y_start + rev_ins_th_idx
            
             # X Range: From Window Frame (Outer Edge) to WDVS Corner
             ri_x_start = idx_win_outer_face
             ri_x_end = idx_w_outer + to_idx(self.cfg.insulation_thick_min_mm)
            
             # Draw Rectangle
             self.grid_map[ri_y_start:ri_y_end, ri_x_start:ri_x_end] = self.ID_REVEAL_INS
             
        
        # 6. Mark External Air
        # Iterate rows and mark everything to the right of the last material as EXT
        for y in range(self.ny):
            # Find last solid pixel
            row = self.grid_map[y, :]
            # efficient numpy search
            solid_indices = np.where(row > 1)[0]
            if solid_indices.size > 0:
                last_solid = solid_indices[-1]
                self.grid_map[y, last_solid+1:] = self.ID_AIR_EXT
            else:
                pass

    def assign_materials(self):
        self.cond = np.zeros_like(self.temp)
        self.cond[self.grid_map == self.ID_WALL] = MAT_WALL
        self.cond[self.grid_map == self.ID_INSULATION] = MAT_INSULATION
        self.cond[self.grid_map == self.ID_REVEAL_INS] = MAT_REVEAL_INSULATION
        self.cond[self.grid_map == self.ID_FRAME] = MAT_FRAME_EQ
        self.cond[self.grid_map == self.ID_GLASS] = MAT_GLASS_UG11
        
        # Spacer
        spacer_lambda = 0.025 # Default air/low
        if self.cfg.spacer_type == SpacerType.SWISS_ULTIMATE:
            spacer_lambda = MAT_SPACER_SWISS_ULTIMATE
        elif self.cfg.spacer_type == SpacerType.STAINLESS_STEEL:
            spacer_lambda = MAT_SPACER_STAINLESS
        elif self.cfg.spacer_type == SpacerType.ALUMINUM:
            spacer_lambda = MAT_SPACER_ALUMINUM
            
        self.cond[self.grid_map == self.ID_SPACER] = spacer_lambda
        # Air
        self.cond[self.grid_map == self.ID_AIR_INT] = 0.025 # Approx static air
        # Boundaries handled in solve loop
        
    def solve(self, max_iter=10000, tol=1e-5):
        # Explicit or Iterative solver (Jacobi/SOR)
        
        for k in range(max_iter):
            t_old = self.temp.copy()
            
            # Define neighbors
            t_up = np.roll(self.temp, -1, axis=0)
            t_dn = np.roll(self.temp, 1, axis=0)
            t_lf = np.roll(self.temp, -1, axis=1)
            t_rt = np.roll(self.temp, 1, axis=1)
            
            k_c = self.cond
            k_up = np.roll(k_c, -1, axis=0)
            k_dn = np.roll(k_c, 1, axis=0)
            k_lf = np.roll(k_c, -1, axis=1)
            k_rt = np.roll(k_c, 1, axis=1)
            
            def harm(k1, k2): return 2*k1*k2/(k1+k2+1e-12)
            
            g_up = harm(k_c, k_up)
            g_dn = harm(k_c, k_dn)
            g_lf = harm(k_c, k_lf)
            g_rt = harm(k_c, k_rt)
            
            # Sum of conductances
            g_sum = g_up + g_dn + g_lf + g_rt
            
            # Update internal nodes
            t_new = (g_up*t_up + g_dn*t_dn + g_lf*t_lf + g_rt*t_rt) / (g_sum + 1e-12)
            
            # Apply Boundaries
            
            # 1. Adiabatic Cut-off (Top of Window, Bottom of Wall)
            # Top (y=max): Adiabatic -> T_top = T_below
            t_new[-1, :] = t_new[-2, :]
            # Bottom (y=0): Adiabatic -> T_bot = T_above
            t_new[0, :] = t_new[1, :]
            # Inner Cut (x=0): Adiabatic (Symmetry/Cut)
            t_new[:, 0] = TEMP_INT
            
            # 2. Surface Boundaries (Convection)
            # Identify Air Regions
            mask_int = self.grid_map == self.ID_AIR_INT
            mask_ext = self.grid_map == self.ID_AIR_EXT
            
            t_new[mask_int] = TEMP_INT
            t_new[mask_ext] = TEMP_EXT
            
            # Correction:
            k_eff_int = self.dx / (2 * self.rsi_value) # USE DYNAMIC RSI
            k_eff_ext = self.dx / (2 * RSE)
            
            self.cond[mask_int] = k_eff_int
            self.cond[mask_ext] = k_eff_ext
            
            self.temp = t_new
            self.temp[mask_int] = TEMP_INT
            self.temp[mask_ext] = TEMP_EXT
            
            if k % 1000 == 0:
                diff = np.max(np.abs(self.temp - t_old))
                if diff < tol:
                    break
        
        return self.temp

    def calculate_psi(self):
        # 1. Total Heat Flow L2D
        T = self.temp
        C = self.cond
        
        def get_flux(mask_from, mask_to, T_val_from):
            # Flux from 'mask_from' (Air) to 'mask_to' (Solid)
            
            total = 0
            # Right Neighbors
            k_harm_r = 2*C[:,:-1]*C[:,1:] / (C[:,:-1]+C[:,1:] + 1e-12)
            # Flow from Left to Right
            q_r = k_harm_r * (T[:,:-1] - T[:,1:])
            # Filter where Left is Air, Right is Solid
            f_r = (mask_from[:,:-1] & mask_to[:,1:])
            total += np.sum(q_r[f_r])
            
            # Left Neighbors (Right to Left)
            q_l = k_harm_r * (T[:,1:] - T[:,:-1]) # flow R->L
            # Filter where Right is Air, Left is Solid
            f_l = (mask_from[:,1:] & mask_to[:,:-1])
            total += np.sum(q_l[f_l]) # Wait, q_r formula was L->R. If R is Air, T_R=Air. Flow R->L is k * (T_R - T_L).
            # q_r computed T_left - T_right.
            # If Left is Air, Solid is Right. Flow L->R positive. total += q_r. Correct.
            # If Right is Air, Left is Solid. T_R is Air.
            # Flow from Air(R) to Solid(L) = k * (T_R - T_L) = - k * (T_L - T_R) = -q_r.
            # total += -q_r[f_l]. Correct.
            
            # Down Neighbors
            k_harm_d = 2*C[:-1,:]*C[1:,:] / (C[:-1,:]+C[1:,:] + 1e-12)
            q_d = k_harm_d * (T[:-1,:] - T[1:,:])
            # Top is Air, Bot is Solid
            f_d = (mask_from[:-1,:] & mask_to[1:,:])
            total += np.sum(q_d[f_d])
            
            # Up neighbors
            f_u = (mask_from[1:,:] & mask_to[:-1,:])
            total += np.sum(-q_d[f_u])
            
            return total

        mask_all_solid = self.grid_map > 1
        mask_int_air = self.grid_map == self.ID_AIR_INT
        
        l2d_watts = get_flux(mask_int_air, mask_all_solid, TEMP_INT)
        delta_t = TEMP_INT - TEMP_EXT
        l2d_coeff = l2d_watts / delta_t 
        
        # 2. Reference L1D
        # Reference Calculation ALWAYS uses Rsi=0.13 (Standard U-value definition)
        r_tot = RSE + (self.cfg.insulation_thick_max_mm/1000.0)/MAT_INSULATION + \
                (self.cfg.wall_thickness_mm/1000.0)/MAT_WALL + 0.13 
        u_wall_1d = 1.0 / r_tot
        
        # Lengths (External Dimensions)
        # From corner (y=reveal_y_mm).
        reveal_y_mm = 500
        l_wall_ext = reveal_y_mm / 1000.0
        
        # Window part reference
        l_win_total = (self.L_window_leg - reveal_y_mm) / 1000.0
        l_frame = self.cfg.frame_width_mm / 1000.0
        l_glass = l_win_total - l_frame
        
        u_frame = 1.3
        u_glass = 1.1
        
        ref_flow_coeff = u_wall_1d * l_wall_ext + u_frame * l_frame + u_glass * l_glass
        
        psi = l2d_coeff - ref_flow_coeff
        
        # fRsi Calculation
        min_surf_temp = TEMP_INT
        
        # Fallback manual dilation
        mask_boundary = np.zeros_like(mask_int_air)
        padded = np.pad(mask_int_air, 1)
        # Center | Up | Down | Left | Right
        m_up = padded[:-2, 1:-1]
        m_dn = padded[2:, 1:-1]
        m_lf = padded[1:-1, :-2]
        m_rt = padded[1:-1, 2:]
        boundary_candidates = (m_up | m_dn | m_lf | m_rt) & (~mask_int_air) & (self.grid_map > 1)
        
        # Get coordinates of boundary nodes
        bound_y, bound_x = np.where(boundary_candidates)
        
        min_temp_all = TEMP_INT
        min_temp_wall = TEMP_INT
        min_temp_frame = TEMP_INT
        min_temp_glass = np.nan
        
        if len(bound_y) > 0:
            k_solid = self.cond[bound_y, bound_x]
            t_cell = self.temp[bound_y, bound_x]
            mats = self.grid_map[bound_y, bound_x]
            
            # Calculate Surface Temp Tsi
            r1 = self.dx / (2.0 * (k_solid + 1e-12))
            r2 = self.rsi_value
            
            t_si = (TEMP_INT * r1 + t_cell * r2) / (r1 + r2)
            
            min_temp_all = np.min(t_si)
            
            # Filter for Wall/Insulation
            mask_wall = np.isin(mats, [self.ID_WALL, self.ID_INSULATION, self.ID_REVEAL_INS])
            if np.any(mask_wall):
                min_temp_wall = np.min(t_si[mask_wall])
                
            # Filter for Frame
            mask_f_only = (mats == self.ID_FRAME)
            if np.any(mask_f_only):
                min_temp_frame = np.min(t_si[mask_f_only])
                
            # Filter for Glass
            mask_g_only = (mats == self.ID_GLASS)
            if np.any(mask_g_only):
                 min_temp_glass = np.min(t_si[mask_g_only])
        
        frsi = (min_temp_all - TEMP_EXT) / (TEMP_INT - TEMP_EXT)
        
        return {
            'L2D': l2d_coeff,
            'Psi': psi,
            'U_Wall': u_wall_1d,
            'fRsi': frsi,
            'MinT': min_temp_all,
            'MinT_Wall': min_temp_wall,
            'MinT_Frame': min_temp_frame,
            'MinT_Glass': min_temp_glass
        }

    def plot_results(self, filename="result.png"):
        plt.figure(figsize=(10, 8))
        plt.imshow(self.temp, cmap='jet', origin='lower', extent=[0, self.width_mm, 0, self.height_mm])
        plt.colorbar(label='Temperature [°C]')
        plt.imshow(self.temp, cmap='jet', origin='lower', extent=[0, self.width_mm, 0, self.height_mm])
        plt.colorbar(label='Temperature [°C]')
        plt.title(f'Temperature Distribution (Thick: {self.cfg.wall_thickness_mm}mm, Grid: {self.cfg.grid_size_mm}mm)')
        plt.xlabel('Depth [mm]')
        plt.ylabel('Facade Length [mm]')
        plt.savefig(filename)
        plt.close() # Good practice to close figure

    def plot_geometry(self, filename="geometry_debug.png"):
        """Plots the Material ID map for rapid visual verification."""
        plt.figure(figsize=(12, 10))
        
        # Create a custom colormap for materials
        # ID_WALL=2, INS=3, REV=4, FRAM=5, GLAS=6, AIR_I=1, AIR_E=0
        cmap = plt.get_cmap('tab10', 10) 
        
        plt.imshow(self.grid_map, cmap=cmap, origin='lower', extent=[0, self.width_mm, 0, self.height_mm], interpolation='nearest')
        plt.colorbar(label='Material ID (0=AirExt, 2=Wall, 3=Ins, 4=RevIns, 5=Frame, 6=Glass)')
        plt.title(f'Geometry Check: {filename}')
        plt.xlabel('Depth [mm]')
        plt.ylabel('Facade Length [mm]')
        plt.grid(True, color='white', alpha=0.3)
        plt.savefig(filename)
        plt.close()

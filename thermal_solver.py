import numpy as np
import matplotlib.pyplot as plt
import scipy.ndimage as nd
from typing import List, Tuple, Dict
from config import *
import ctypes
import os

# Load C++ Library
try:
    so_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "thermal_solver_core.so"))
    lib = ctypes.CDLL(so_path)

    
    # solve_optimized(double* temp, const double* cond, const int* fixed_mask, const double* fixed_values, int rows, int cols, int iterations)
    lib.solve_optimized.argtypes = [
        ctypes.POINTER(ctypes.c_double), # temp (in/out)
        ctypes.POINTER(ctypes.c_double), # cond
        ctypes.POINTER(ctypes.c_int),    # fixed_mask
        ctypes.POINTER(ctypes.c_double), # fixed_values
        ctypes.c_int, # rows
        ctypes.c_int, # cols
        ctypes.c_int  # iterations
    ]
    lib.solve_optimized.restype = ctypes.c_double

    # solve_red_black(double* temp, const double* cond, const int* fixed_mask, const double* fixed_values, int rows, int cols, int iterations, double omega)
    lib.solve_red_black.argtypes = [
        ctypes.POINTER(ctypes.c_double), # temp (in/out)
        ctypes.POINTER(ctypes.c_double), # cond
        ctypes.POINTER(ctypes.c_int),    # fixed_mask
        ctypes.POINTER(ctypes.c_double), # fixed_values
        ctypes.c_int, # rows
        ctypes.c_int, # cols
        ctypes.c_int,  # iterations
        ctypes.c_double # omega
    ]
    lib.solve_red_black.restype = ctypes.c_double
    USE_CPP = True
    print("[INFO] C++ Accelerated Solver Loaded.")
except Exception as e:
    print(f"[WARNING] C++ Solver not found/loaded: {e}. Using pure Python.")
    USE_CPP = False

class ThermalSolver:
    def __init__(self, config: CalculationConfig, rsi_value: float = 0.13, use_adaptive: bool = True):
        self.cfg = config
        self.rsi_value = rsi_value 
        self.use_adaptive = use_adaptive
        
        # New: Store Grid Coordinates (Non-Uniform)
        self.x_coords = None # Faces
        self.y_coords = None # Faces
        self.xc = None # Centers
        self.yc = None # Centers
        self.dx_array = None # Widths
        self.dy_array = None # Heights
        
        # Dimensions are now derived from grid generation
        self.setup_adaptive_grid() if self.use_adaptive else self.setup_uniform_grid()
        
        self.grid_map = np.zeros((self.ny, self.nx), dtype=int) 
        self.temp = np.ones((self.ny, self.nx)) * TEMP_INT 
        
        # IDs
        from geometry import MaterialID
        self.ID_AIR_INT = MaterialID.AIR_INT
        self.ID_AIR_EXT = MaterialID.AIR_EXT
        self.ID_WALL = MaterialID.WALL
        self.ID_INSULATION = MaterialID.INSULATION
        self.ID_REVEAL_INS = MaterialID.REVEAL_INS
        self.ID_FRAME = MaterialID.FRAME
        self.ID_GLASS = MaterialID.GLASS
        self.ID_SPACER = MaterialID.SPACER

        self.setup_geometry_map()
        self.assign_materials_adaptive()

    def setup_adaptive_grid(self):
        """Generates a non-uniform rectilinear grid."""
        # 1. Define Key X-Coordinates (Vertical cuts)
        # Relative to Masonry Corner (x=0)
        # - Interior Wall Start
        # - Reveal Insulation Start/End
        # - Frame Start/End
        # - Window Pane Splits
        # - Insulation Start/End/Steps (Taper)
        
        # Canvas Bounds
        offset_x = -50.0 # Internal Air
        
        # Collect critical x-points
        x_points = set()
        x_points.add(offset_x)
        x_points.add(0.0) # Masonry Inner Face
        
        w_th = self.cfg.wall_thickness_mm
        x_points.add(w_th) # Masonry Outer Face (Reveal Edge Reference)
        
        # Window Position
        pos_mm = max(0, self.cfg.window_position_from_exterior_masonry_mm)
        win_outer_face = w_th - pos_mm
        x_points.add(win_outer_face)
        
        # Frame
        f_depth = self.cfg.frame_depth_mm
        f_start = win_outer_face - f_depth
        x_points.add(f_start)
        
        # Sash / Glass
        # Simplification: Split Frame into 3 zones?
        # Let's add points for Glass (24mm centered in sash)
        # Sash is recessed 30mm from Fixed Frame outer
        sash_outer = win_outer_face - 30
        x_points.add(sash_outer)
        sash_depth = 70
        sash_inner = sash_outer - sash_depth
        x_points.add(sash_inner)
        
        glass_mid = (sash_outer + sash_inner) / 2
        x_points.add(glass_mid - 12); x_points.add(glass_mid + 12)
        
        # Insulation
        x_points.add(w_th + self.cfg.insulation_thick_max_mm)
        x_points.add(w_th + self.cfg.insulation_thick_min_mm)
        x_points.add(w_th + self.cfg.insulation_thick_max_mm + 500) # Far field
        
        # Reveal Insulation
        if self.cfg.reveal_insulation_mm > 0:
            # Sits on Reveal Face (which is w_th... wait. Reveal Face is Y-plane.)
            # But the reveal insulation has thickness in Y...
            # Wait, Reveal Insulation is on the jamb. 
            # It adds thickness to the jamb?
            # Usually: Reveal Insulation is on the masonry reveal surface (Y-plane).
            # So its thickness is in Y direction.
            # But if it wraps around...
            # Let's assume standard: ID_REVEAL_INS is a block filling the corner.
            pass
            
        # Sort critical points
        crit_x = sorted(list(x_points))
        
        # Generate Grid between points
        self.x_coords = [crit_x[0]]
        
        def add_segments(target_list, start, end, target_dh):
            dist = end - start
            if dist <= 1e-9: return
            n = max(1, int(round(dist / target_dh)))
            # If refinement needed
            steps = np.linspace(start, end, n+1)
            for s in steps[1:]:
                target_list.append(s)

        for i in range(len(crit_x)-1):
            start = crit_x[i]
            end = crit_x[i+1]
            
            # Determine Density
            # High density near Window/Reveal (0 to w_th + 100)
            is_detail = (start > (w_th - 200)) and (end < (w_th + 200))
            if is_detail:
                dh = 0.5 # 0.5mm near details
                # Ultra fine for glass/frame gaps?
                if (start > f_start - 10) and (end < win_outer_face + 10):
                     dh = 0.25
            else:
                dh = 10.0 # 10mm coarse
                
            add_segments(self.x_coords, start, end, dh)
            
        self.x_coords = np.array(self.x_coords)
        self.dx_array = np.diff(self.x_coords)
        self.xc = (self.x_coords[:-1] + self.x_coords[1:]) / 2.0
        self.nx = len(self.xc)
        
        # 2. Define Y-Coordinates
        # y=0 is Reveal Edge (Corner of Masonry) ???
        # Previously: y=0 was masonry outer face? No, y was "Facade Length".
        # Let's align y=0 with Masonry Reveal Edge.
        # <0 is wall (down), >0 is window/facade (up)
        
        # Bounds
        y_bottom = 0.0 # Origin
        y_top = 1000.0 # 1m window leg
        y_wall_deep = -500.0 # 500mm wall leg
        
        y_points = set()
        y_points.add(y_bottom)
        y_points.add(y_top)
        y_points.add(y_wall_deep)
        
        # Frame Y
        # Frame starts at 15mm from reveal?
        # Or flush?
        # Let's match previous logic: idx_reveal_edge was 500mm in prev grid.
        # Here let y=0 be the physical corner.
        
        # Frame Position
        # From previous Code: Start Y (15mm gap) or Flush?
        # We used idx_f_y_start = idx_reveal_edge (Flush).
        y_f_start = 0.0 
        y_f_end = y_f_start + self.cfg.frame_width_mm
        y_points.add(y_f_start)
        y_points.add(y_f_end)
        
        # Sash Overlap
        overlap = 10
        y_sash_start = y_f_end - overlap
        y_sash_end = y_sash_start + 70 # Sash Width
        y_points.add(y_sash_start)
        y_points.add(y_sash_end)
        
        # Glass Start (10mm overlap)
        y_glass_start = y_sash_start + 10
        y_points.add(y_glass_start)
        
        # Reveal Insulation (Y thickness)
        if self.cfg.reveal_insulation_mm > 0:
             # Sits on y=0 (Rebate tip) or wrap?
             # If Rebate Overlap exists:
             reb_ov = self.cfg.masonry_rebate_overlap_mm
             if reb_ov > 0:
                 y_points.add(reb_ov)
                 y_points.add(reb_ov + self.cfg.reveal_insulation_mm)
             else:
                 y_points.add(self.cfg.reveal_insulation_mm)
                 
        # Taper
        taper_len = self.cfg.taper_length_mm
        y_points.add(-taper_len)
        
        # Sort
        crit_y = sorted(list(y_points))
        
        self.y_coords = [crit_y[0]]
        for i in range(len(crit_y)-1):
            start = crit_y[i]
            end = crit_y[i+1]
            
            # Density
            # Near Reveal (y=0) and Frame
            is_detail = (start > -150) and (end < 150)
            if is_detail:
                dh = 0.5
                if (start > -10) and (end < 120): dh = 0.25 # Frame Zone
            else:
                dh = 10.0
            
            add_segments(self.y_coords, start, end, dh)
            
        self.y_coords = np.array(self.y_coords)
        self.dy_array = np.diff(self.y_coords)
        self.yc = (self.y_coords[:-1] + self.y_coords[1:]) / 2.0
        self.ny = len(self.yc)
        
        # Dimensions
        self.width_mm = self.x_coords[-1] - self.x_coords[0]
        self.height_mm = self.y_coords[-1] - self.y_coords[0]
        
        # print(f"Adaptive Grid: {self.nx} x {self.ny} (Uniform was {int(self.width_mm)}x{int(self.height_mm)})")

    def setup_uniform_grid(self):
        # Fallback to logic from original init
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
        
        # For uniform grid, dx_array and dy_array are constant
        self.x_coords = np.arange(0, self.width_mm + self.cfg.grid_size_mm, self.cfg.grid_size_mm)
        self.y_coords = np.arange(0, self.height_mm + self.cfg.grid_size_mm, self.cfg.grid_size_mm)
        self.dx_array = np.full(self.nx, self.cfg.grid_size_mm)
        self.dy_array = np.full(self.ny, self.cfg.grid_size_mm)
        self.xc = self.x_coords[:-1] + self.cfg.grid_size_mm / 2
        self.yc = self.y_coords[:-1] + self.cfg.grid_size_mm / 2

    def setup_geometry_map(self):
        # Fill grid_map based on geometric predicates on xc, yc
        # Geometry is defined in physical coordinates (mm), referenced to Masonry Corner
        
        # Map everything to mm relative to corner (y=0 is reveal edge, x=w_th is outer face)
        
        # 1. Initialize Air Ind
        self.grid_map[:] = self.ID_AIR_INT
        
        X, Y = np.meshgrid(self.xc, self.yc) # 2D Arrays of center coordinates
        
        w_th = self.cfg.wall_thickness_mm
        
        # 2. Wall (Masonry)
        # x: [0, w_th]
        # y: [-inf, 0] + Rebate
        rebate = self.cfg.masonry_rebate_overlap_mm
        mask_wall_base = (X >= 0) & (X <= w_th) & (Y <= 0)
        self.grid_map[mask_wall_base] = self.ID_WALL
        
        # Rebate (Nose)
        if rebate > 0:
             # Rebate Extends Y: [0, rebate]
             # X: [Win_Outer, w_th]
             pos = max(0, self.cfg.window_position_from_exterior_masonry_mm)
             win_outer = w_th - pos
             mask_rebate = (Y > 0) & (Y <= rebate) & (X >= win_outer) & (X <= w_th)
             self.grid_map[mask_rebate] = self.ID_WALL
             
        # 3. Insulation (Exterior)
        # Taper Logic
        # Taper starts at y = -taper_len, X_max = w_th + max_ins
        # At y=0 (Corner), X_max = w_th + min_ins (or max if uniform)
        # Wait, Taper is meant to THIN OUT towards the window? Or THICKEN?
        # "Taper... to accommodate the reveal" -> Usually insulation is thinner on the reveal.
        # But here assume standard WDVS:
        # Deep wall: Full Thickness
        # Near Window: Tapers? Or just cuts?
        # User Logic: taper_length_mm is where it starts tapering from MAX to MIN.
        # MIN is at the corner.
        
        taper_start_y = -self.cfg.taper_length_mm
        
        # Base Insulation Region (y < 0)
        # Max X is function of Y
        
        # Optimize: 1D function for max_ins_x(y) broadcasted
        def get_ins_max_x(y_v):
            if y_v < taper_start_y: return w_th + self.cfg.insulation_thick_max_mm
            elif y_v > 0: return w_th + self.cfg.insulation_thick_min_mm # Corner/Rebate
            else:
                # Linear Taper
                f = (y_v - taper_start_y) / (0 - taper_start_y) # 0 to 1
                th = self.cfg.insulation_thick_max_mm - f * (self.cfg.insulation_thick_max_mm - self.cfg.insulation_thick_min_mm)
                return w_th + th
                
        # Vectorize
        v_max_x = np.vectorize(get_ins_max_x)(self.yc)
        # Broadcast to (NY, NX)
        # Check X against v_max_x
        # X is (NY, NX)
        # v_max_x is (NY,) -> reshape to (NY, 1)
        mask_ins = (X > w_th) & (X <= v_max_x[:, None]) & (Y <= 0) # Only up to corner y=0
        self.grid_map[mask_ins] = self.ID_INSULATION
        
        # 4. Reveal Insulation
        # On top of Rebate (Y > rebate) ?
        # Or covering the rebate face?
        # Defined as "Rectangle" in previous step.
        # X range: [Win_Outer, w_th + min_ins]
        # Y range: [Rebate_End, Rebate_End + Rev_Iso_Thick]
        
        if self.cfg.reveal_insulation_mm > 0 and not self.cfg.uninsulated_reveal:
             rev_start_y = 0.0 + rebate
             rev_end_y = rev_start_y + self.cfg.reveal_insulation_mm
             
             win_outer = w_th - max(0, self.cfg.window_position_from_exterior_masonry_mm)
             rev_end_x = w_th + self.cfg.insulation_thick_min_mm # Matches WDVS corner
             
             mask_ri = (Y >= rev_start_y) & (Y <= rev_end_y) & (X >= win_outer) & (X <= rev_end_x)
             self.grid_map[mask_ri] = self.ID_REVEAL_INS
             
        # 5. Window Frame
        # Fixed Frame
        f_width = self.cfg.frame_width_mm
        f_depth = self.cfg.frame_depth_mm
        win_outer = w_th - max(0, self.cfg.window_position_from_exterior_masonry_mm)
        
        ff_y_start = 0.0 # Flush
        ff_y_end = ff_y_start + f_width
        ff_x_end = win_outer
        ff_x_start = ff_x_end - f_depth
        
        mask_ff = (Y >= ff_y_start) & (Y <= ff_y_end) & (X >= ff_x_start) & (X <= ff_x_end)
        self.grid_map[mask_ff] = self.ID_FRAME
        
        # Sash
        overlap = 10
        sash_y_start = ff_y_end - overlap
        sash_width = 70
        sash_depth = 70
        sash_recess = 30
        
        s_y_end = sash_y_start + sash_width
        s_x_end = ff_x_end - sash_recess
        s_x_start = s_x_end - sash_depth
        
        mask_sash = (Y >= sash_y_start) & (Y <= s_y_end) & (X >= s_x_start) & (X <= s_x_end)
        self.grid_map[mask_sash] = self.ID_FRAME
        
        # Extension (L-Profile behind sash)
        # From ff_y_end up to ... 80mm from corner
        ext_y_end = 80.0
        if ext_y_end > ff_y_end:
            # X: Sash Outer to Frame Outer
            mask_ext = (Y >= ff_y_end) & (Y <= ext_y_end) & (X >= s_x_end) & (X <= ff_x_end)
            self.grid_map[mask_ext] = self.ID_FRAME
            
        # 6. Glass
        # Centered in Sash
        g_mid_x = (s_x_start + s_x_end) / 2
        g_half_th = 12
        g_x_start = g_mid_x - g_half_th
        g_x_end = g_mid_x + g_half_th
        
        g_y_start = sash_y_start + 10 # 10mm overlap
        
        mask_glass = (Y >= g_y_start) & (X >= g_x_start) & (X <= g_x_end)
        self.grid_map[mask_glass] = self.ID_GLASS
        
        # 7. Use AIR_EXT for everything "Right" of the structure
        # (Naive Fill: Scan each Y, find last solid X)
        # Vectorized fill?
        for i in range(self.ny):
            row = self.grid_map[i, :]
            solids = np.where(row > 1)[0]
            if solids.size > 0:
                last = solids[-1]
                self.grid_map[i, last+1:] = self.ID_AIR_EXT
                
    def assign_materials_adaptive(self):
        # Same as old assign_materials but updates self.cond
        # Logic is identical mapping
        self.cond = np.zeros_like(self.temp)
        self.cond[self.grid_map == self.ID_WALL] = MAT_WALL
        self.cond[self.grid_map == self.ID_INSULATION] = MAT_INSULATION
        self.cond[self.grid_map == self.ID_REVEAL_INS] = MAT_REVEAL_INSULATION
        self.cond[self.grid_map == self.ID_FRAME] = MAT_FRAME_EQ
        self.cond[self.grid_map == self.ID_GLASS] = MAT_GLASS_UG11
        
        # Spacer logic (Needs Geometry Info)
        if self.cfg.spacer_type != SpacerType.NONE:
             # Find Glass Bottom
             # Just search grid
             rows, cols = np.where(self.grid_map == self.ID_GLASS)
             if rows.size > 0:
                 min_r = np.min(rows)
                 # Spacer Height = 7mm
                 # We need to find how many rows correspond to 7mm at this location
                 # Since Y grid is variable, we must iterate/sum dy
                 h_sum = 0
                 r_ptr = min_r
                 while h_sum < 7.0 and r_ptr < self.ny:
                     h_sum += self.dy_array[r_ptr] # dy at row r_ptr
                     # Mark Spacer
                     # glass cols only
                     glass_row_cols = np.where(self.grid_map[r_ptr, :] == self.ID_GLASS)[0]
                     self.grid_map[r_ptr, glass_row_cols] = self.ID_SPACER
                     r_ptr += 1

        # Spacer Lambda
        spacer_lambda = 0.025
        if self.cfg.spacer_type == SpacerType.SWISS_ULTIMATE: spacer_lambda = MAT_SPACER_SWISS_ULTIMATE
        elif self.cfg.spacer_type == SpacerType.STAINLESS_STEEL: spacer_lambda = MAT_SPACER_STAINLESS
        elif self.cfg.spacer_type == SpacerType.ALUMINUM: spacer_lambda = MAT_SPACER_ALUMINUM
        
        self.cond[self.grid_map == self.ID_SPACER] = spacer_lambda
        self.cond[self.grid_map == self.ID_AIR_INT] = 0.025
        

    def calculate_conductances(self):
        """
        Calculates horizontal (Gh) and vertical (Gv) conductance matrices.
        Gh[i, j] = Conductance between node (i, j) and (i, j+1)
        Gv[i, j] = Conductance between node (i, j) and (i+1, j)
        """
        # Conductance G = (k * Area) / Distance
        # 1. Harmonic Mean of lambda for interface conductivity
        # k_interface = 2 * k1 * k2 / (k1 + k2)
        
        # Grid sizes (meters)
        # self.dx_array[j] is width of cell j
        # self.dy_array[i] is height of cell i
        
        # Horizontal Conductance (Left-Right)
        # Interface between (i, j) and (i, j+1)
        # Area = dy_array[i] * 1.0 (depth)
        # Distance = (dx_array[j] + dx_array[j+1]) / 2.0
        
        k = self.cond
        k_right = np.roll(k, -1, axis=1) # (i, j+1)
        
        # Harmonic mean
        harm_k_h = 2 * k * k_right / (k + k_right + 1e-12)
        
        # Geometric factors for Horizontal Flow
        # dx between centers:
        dx_col = self.dx_array # (NX,)
        dx_dist_h = (dx_col[:-1] + dx_col[1:]) / 2.0
        # Pad last col (boundary) - distance to "ghost" node? Just duplicate last dx
        dx_dist_h = np.append(dx_dist_h, dx_col[-1]) 
        
        # DY (Area) is row-dependent (NY,)
        dy_row = self.dy_array
        
        # Gh = k_int * Area / Length
        # Broadcast: (NY, NX) = (NY, NX) * (NY, 1) / (1, NX)
        self.Gh = harm_k_h * dy_row[:, None] / dx_dist_h[None, :]
        
        
        # Vertical Conductance (Down-Up? or Top-Bottom)
        # Solver uses (i, j) and (i+1, j) -> Downwards connection
        # Interface between (i, j) and (i+1, j)
        k_down = np.roll(k, -1, axis=0) # (i+1, j)
        harm_k_v = 2 * k * k_down / (k + k_down + 1e-12)
        
        # Distance between centers
        dy_dist_v = (dy_row[:-1] + dy_row[1:]) / 2.0
        dy_dist_v = np.append(dy_dist_v, dy_row[-1])
        
        # Area (DX)
        
        self.Gv = harm_k_v * dx_col[None, :] / dy_dist_v[:, None]

    def solve(self, max_iter=60000, tol=1e-5, omega=1.85):
        # 1. Prepare Boundaries (Fixed Mask)
        mask_int = (self.grid_map == self.ID_AIR_INT)
        mask_ext = (self.grid_map == self.ID_AIR_EXT)
        
        fixed_mask = (mask_int | mask_ext).astype(np.int32)
        
        # 2. Update Effective Conductivities for Air Boundaries
        # Rsi/Rse application depends on Grid Size!
        # h_int = 1/Rsi. G_surf = h_int * Area.
        # This replaces the logic of "Effective Lambda".
        # We should calculate Surface Conductance explicitly?
        # NO, "Effective Lambda" approach works if we treat the air cell as a resistor R = dx / (2*k_eff) = Rsi.
        # This ensures the resistance from Center of Air Cell to Interface is Rsi.
        # k_eff = dx / (2 * Rsi)
        # This is strictly correct ONLY if the air cell is the boundary.
        # With variable grid, dx varies!
        
        # Vectorized Update of Air Conductivities
        # Use self.dx_array (1D) broadcasted
        
        k_eff_int_vec = self.dx_array / (2 * self.rsi_value)
        k_eff_ext_vec = self.dx_array / (2 * RSE)
        
        # Apply to self.cond based on column index
        # We need to construct a 2D K_eff array
        K_eff = np.zeros_like(self.temp)
        # Broadcast X-dependent K
        K_eff[:] = k_eff_int_vec[None, :]
        
        self.cond[mask_int] = K_eff[mask_int]
        
        # For Ext
        K_eff[:] = k_eff_ext_vec[None, :]
        self.cond[mask_ext] = K_eff[mask_ext]
        
        # 3. Compute Conductance Matrices Gh, Gv
        self.calculate_conductances()
        
        # Prepare Fixed Values
        fixed_values = np.zeros_like(self.temp)
        fixed_values[mask_int] = TEMP_INT
        fixed_values[mask_ext] = TEMP_EXT
        self.temp[mask_int] = TEMP_INT
        self.temp[mask_ext] = TEMP_EXT
        
        if USE_CPP and hasattr(lib, 'solve_general_conductance'):
            # Data preparation
            temp_c = np.ascontiguousarray(self.temp, dtype=np.float64)
            gh_c = np.ascontiguousarray(self.Gh, dtype=np.float64)
            gv_c = np.ascontiguousarray(self.Gv, dtype=np.float64)
            mask_c = np.ascontiguousarray(fixed_mask, dtype=np.int32)
            fval_c = np.ascontiguousarray(fixed_values, dtype=np.float64)
            
            rows, cols = self.temp.shape
            
            p_temp = temp_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
            p_gh = gh_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
            p_gv = gv_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
            p_mask = mask_c.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
            p_fval = fval_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
            
            # Setup Argtypes if not done globally (It wasn't done yet)
            lib.solve_general_conductance.argtypes = [
                ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_double),
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_double
            ]
            lib.solve_general_conductance.restype = ctypes.c_double
            
            batch = 2000
            for k in range(0, max_iter, batch):
                diff = lib.solve_general_conductance(p_temp, p_gh, p_gv, p_mask, p_fval, rows, cols, batch, omega)
                
                step = k + batch
                if step % 10000 == 0:
                     print(f"  Iteration {step}/{max_iter}: Diff={diff:.2e}")
                     
                if diff < tol:
                    print(f"Adaptive Solver Converged: {step} iters, Diff={diff:.2e}")
                    break
            self.temp = temp_c
            return self.temp
            
        else:
            print("Fallback: Python Solver")
            # Implement Python version of General Solver if needed, but for now just fail or verify
            return self.temp # Todo implementation


    def calculate_psi(self):
        # 1. Total Heat Flow L2D
        T = self.temp
        
        # We must assume self.Gh and self.Gv are populated
        if not hasattr(self, 'Gh') or self.Gh is None:
            self.calculate_conductances()
        
        Gh = self.Gh
        Gv = self.Gv
        
        def get_flux(mask_from, mask_to):
            # Flux from 'mask_from' (Air) to 'mask_to' (Solid)
            # Only consider adjacent pairs
            
            total = 0.0
            
            # 1. Horizontal Flux (Left <-> Right)
            # Gh[i,j] connects (i,j) and (i,j+1)
            # Flow from j to j+1 = Gh * (T_j - T_j+1)
            
            # a) Left is Air (From), Right is Solid (To)
            # T_left is Air Temp (Fixed). T_right is Surface Temp.
            # Flow L->R = Gh * (T_L - T_R)
            # Mask Check: mask_from[:, :-1] (Left) AND mask_to[:, 1:] (Right)
            f_lr = (mask_from[:, :-1] & mask_to[:, 1:])
            # Corresponding Conductances are Gh[:, :-1]
            # Corresponding Temps: T[:, :-1] (Air), T[:, 1:] (Surface)
            q_lr = Gh[:, :-1] * (T[:, :-1] - T[:, 1:])
            total += np.sum(q_lr[f_lr])
            
            # b) Right is Air (From), Left is Solid (To)
            # Flow R->L = Gh * (T_R - T_L)
            # Mask: mask_from[:, 1:] (Right/Air) AND mask_to[:, :-1] (Left/Solid)
            f_rl = (mask_from[:, 1:] & mask_to[:, :-1])
            q_rl = Gh[:, :-1] * (T[:, 1:] - T[:, :-1])
            total += np.sum(q_rl[f_rl])
            
            # 2. Vertical Flux (Top <-> Bottom)
            # Gv[i,j] connects (i,j) and (i+1, j) (Top -> Bottom)
            # Flow T->B = Gv * (T_top - T_bot)
            
            # a) Top is Air (From), Bot is Solid (To)
            # Mask: mask_from[:-1, :] AND mask_to[1:, :]
            f_tb = (mask_from[:-1, :] & mask_to[1:, :])
            q_tb = Gv[:-1, :] * (T[:-1, :] - T[1:, :])
            total += np.sum(q_tb[f_tb])
            
            # b) Bot is Air (From), Top is Solid (To)
            # Mask: mask_from[1:, :] AND mask_to[:-1, :]
            f_bt = (mask_from[1:, :] & mask_to[:-1, :])
            q_bt = Gv[:-1, :] * (T[1:, :] - T[:-1, :])
            total += np.sum(q_bt[f_bt])
            
            return total

        mask_all_solid = self.grid_map > 1
        mask_int_air = self.grid_map == self.ID_AIR_INT
        
        l2d_watts = get_flux(mask_int_air, mask_all_solid)
        delta_t = TEMP_INT - TEMP_EXT
        l2d_coeff = l2d_watts / delta_t 
        
        # 2. Reference L1D
        # Reference Calculation ALWAYS uses Rsi=0.13 (Standard U-value definition)
        r_tot = RSE + (self.cfg.insulation_thick_max_mm/1000.0)/MAT_INSULATION + \
                (self.cfg.wall_thickness_mm/1000.0)/MAT_WALL + 0.13 
        u_wall_1d = 1.0 / r_tot
        
        # Lengths (External Dimensions)
        # Determine reveal position from grid (y=0 is reveal edge in adaptive mode)
        # In adaptive: y ranges from y_wall_deep to y_top
        # Wall leg is from y_min to y=0 (reveal)
        # Window leg is from y=0 to y_max
        
        if self.use_adaptive:
            # Adaptive: y=0 is reveal edge
            l_wall_ext = abs(self.y_coords[0]) / 1000.0  # From bottom to y=0
            l_win_total = (self.y_coords[-1] - 0.0) / 1000.0  # From y=0 to top
        else:
            # Uniform: use old logic
            reveal_y_mm = 500
            l_wall_ext = reveal_y_mm / 1000.0
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
            # For adaptive grid, dx varies by column
            # bound_x contains column indices, use dx_array[bound_x]
            dx_local = self.dx_array[bound_x] if self.use_adaptive else np.full_like(bound_x, self.dx, dtype=float)
            r1 = dx_local / (2.0 * (k_solid + 1e-12))
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

import numpy as np
import matplotlib.pyplot as plt
import argparse
from dataclasses import dataclass
from typing import List, Tuple, Dict

# --- Configuration & Constants ---
# Materials (Lambda in W/mK)
MAT_WALL = 0.81  # Brick/Masonry (Standard Vollziegel 1800kg/m3)
MAT_INSULATION = 0.035  # ETICS WLS 035
MAT_REVEAL_INSULATION = 0.035

# Boundary Conditions (Temperature in C, Resistance in m2K/W)
TEMP_INT = 20.0
TEMP_EXT = -5.0
RSI_WALL = 0.13
RSI_CORNER = 0.25 
RSE = 0.04

# --- Calibrated Material Properties (Fixing double resistance error) ---
# The U-value provided (Ug, Uf) INCLUDES Rsi and Rse.
# In the Finite Difference Model, Rsi and Rse are applied as boundary conditions.
# Therefore, the material block must have a resistance of R_mat = 1/U - Rsi - Rse.

# Frame
# U_f = 1.3
# R_f_total = 1 / 1.3 = 0.769 m2K/W
# R_f_mat = 0.769 - RSI_WALL - RSE = 0.769 - 0.13 - 0.04 = 0.599 m2K/W
# Frame Depth d = 0.08 m
# Lambda_frame_eq = d / R_f_mat = 0.08 / 0.599 = 0.133 W/mK
MAT_FRAME_EQ = 0.08 / (1.0/1.3 - RSI_WALL - RSE) 

# Glass 
# U_g = 1.1
# R_g_total = 1 / 1.1 = 0.909 m2K/W
# R_g_mat = 0.909 - RSI_WALL - RSE = 0.909 - 0.13 - 0.04 = 0.739 m2K/W
# Glass Model Thickness d = 0.024 m (24mm used in grid)
# Lambda_glass_eq = 0.024 / R_g_mat
MAT_GLASS_UG11 = 0.024 / (1.0/1.1 - RSI_WALL - RSE)

# Boundary Conditions (Temperature in C, Resistance in m2K/W)
TEMP_INT = 20.0
TEMP_EXT = -5.0
RSI_WALL = 0.13
RSI_CORNER = 0.25 # For fRsi check usually, but for Psi we often use 0.13 standard.
                  # ISO 10211 says use Rsi=0.13 for U-value calculation, Rsi=0.25 for min temp.
                  # We will use 0.13 for Psi calc.
RSE = 0.04

@dataclass
class CalculationConfig:
    wall_thickness_mm: int
    insulation_thick_max_mm: int
    insulation_thick_min_mm: int
    reveal_insulation_mm: int
    taper_length_mm: int  # Length over which insulation tapers
    frame_depth_mm: int = 80
    frame_width_mm: int = 80 # Face width
    window_position_from_exterior_masonry_mm: int = 0 # 0 = Flush
    masonry_rebate_overlap_mm: int = 0
    uninsulated_reveal: bool = False

class ThermalSolver:
    def __init__(self, config: CalculationConfig, grid_size_mm: int = 5, rsi_value: float = 0.13):
        self.cfg = config
        self.rsi_value = rsi_value # Store Dynamic Rsi
        self.dx = grid_size_mm / 1000.0  # meters
        
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
        
        self.nx = int(self.width_mm / grid_size_mm) + 1  # X direction (Thickness)
        self.ny = int(self.L_window_leg / grid_size_mm) + 1 # Y direction (Length along facade)
        
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
        w_th = self.cfg.wall_thickness_mm
        
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
        
        idx_taper_start = max(0, to_idx(reveal_y_mm - self.cfg.taper_length_mm)) # Fixed: Safety clamp
        idx_ins_base_min = to_idx(w_th + self.cfg.insulation_thick_min_mm)
        
        # --- FIX 1: Consistent Window Position Logic ---
        pos_mm = max(0, self.cfg.window_position_from_exterior_masonry_mm)
        idx_pos = to_idx(pos_mm)
        
        # Define Outer Face of Window (shifted inwards from masonry outer face)
        idx_win_outer_face = idx_w_outer - idx_pos
        # Safety: Window cannot actally start before inner masonry face
        idx_win_outer_face = max(idx_w_inner + 1, idx_win_outer_face)
        
        # Frame coordinates based on this new reference
        # Frame coordinates based on this new reference
        # Make sure definitions are available
        f_depth_idx = to_idx(self.cfg.frame_depth_mm)
        f_width_idx = to_idx(self.cfg.frame_width_mm)
        
        idx_f_x_end = idx_win_outer_face
        idx_f_x_start = idx_f_x_end - f_depth_idx
        
        # FIX: Constant Frame Start Y (15mm gap)
        # Allows insulation to overlap frame instead of shifting frame
        idx_f_y_start = idx_reveal_edge + to_idx(15) 
        idx_f_y_end = idx_f_y_start + f_width_idx
        
        # Glass Indices (Generic) based on frame
        g_thick_idx = to_idx(24)
        idx_g_x_mid = int((idx_f_x_start + idx_f_x_end) / 2)
        idx_g_x_start = idx_g_x_mid - int(g_thick_idx/2)
        idx_g_x_end = idx_g_x_mid + int(g_thick_idx/2)
        

        # --- FIX 2: Single Placement of Frame/Glass ---
        # FIX: RESTORING MISSING WALL AND INSULATION LOGIC
        
        # 1. Fill basic Masonry Wall (up to reveal edge)
        # From y=0 to y=reveal_edge, x=0 to x=w_outer
        # Wait, if Rebate exists, Masonry extends differently.
        # Base Wall:
        self.grid_map[0:idx_reveal_edge, idx_w_inner:idx_w_outer] = self.ID_WALL
        
        # 2. Base Insulation (Exterior WDVS)
        # Taper Logic Revised (Fix 3: Flush with Rebate):
        idx_ins_corner = idx_reveal_edge
        if self.cfg.masonry_rebate_overlap_mm > 0:
             # If rebate exists, the EXTERNAL insulation also extends to cover it?
             # Or does the Rebate stick out?
             # Usually WDVS flush with Rebate.
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
        # It goes from the corner (x=w_outer) inwards along the masonry face? 
        # No, a "Laibung" is the surface perpendicular to the facade.
        # So it is at y=reveal_edge, between x=0 and x=w_outer? 
        # No, the reveal is the surface of the brick that faces the window opening.
        # So the insulation is placed on the wall end face.
        # It covers the frame partially.
        # Thickness: reveal_insulation_mm.
        # It extends from the external insulation corner inwards to the frame.
        
        rev_ins_th_idx = to_idx(self.cfg.reveal_insulation_mm)
        
        # It sits on the "top" (y-positive) face of the masonry wall.
        # Y range: [idx_reveal_edge, idx_reveal_edge + rev_ins_th_idx] -> NO.
        # The masonry ENDS at y=reveal_edge.
        # So the reveal insulation is added ON TOP of the masonry end, pushing into the opening?
        # Yes.
        # So it occupies y: [idx_reveal_edge, idx_reveal_edge + rev_ins_th_idx]
        # X range: From Outer Insulation corner (depends on taper) to Frame?
        # It usually connects the outer insulation to the frame.
        # Let's fill the corner.
        
        # The main insulation ends at idx_reveal_edge.
        # The reveal insulation turns the corner.
        # It should overlap the frame.
        # Let's assume it covers the frame by 'overlap' amount (e.g. 30mm).
        # X start: idx_w_outer (connects to external ins?) 
        # Actually, External Insulation usually overlaps the corner.
        
        # Simplified geometry:
        # Create a block of Reveal Insulation at y=[reveal_edge, reveal_edge + thick].
        # X extent: From w_outer (connecting to ext ins) down to frame overlap.
        # Frame is at [w_outer - depth, w_outer].
        # Reveal insulation is usually on the EXTERIOR side of the frame.
        # Wait, if frame is flush with masonry, the reveal insulation sits ON the masonry face?
        # No, if frame is flush, the reveal insulation sits on the FRAME face? No.
        
        # CORRECT DETAIL (from typical ETICS):
        # Wall ends. Frame is mounted.
        # Insulation board is glued to the reveal face of the wall (if space exists) or the frame is smaller than opening.
        # If frame is flush with masonry outer edge (x=w_outer):
        # The reveal insulation is placed on the EXTERIOR face of the reveal (the return).
        # This implies it sits at x > w_outer? No, that's the facade.
        
        # Let's assume the window is smaller than the masonry opening.
        # Masonry Opening Edge is at y=reveal_edge.
        # Window Frame starts at y=reveal_edge + gap (filled with foam/insulation).
        # Reveal Insulation fills that gap and overlaps the frame.
        
        # Let's adjust:
        # Masonry ends at y=reveal_edge.
        # Frame starts at y=reveal_edge + reveal_ins_th_idx. (Window is smaller).
        # Calculating gap.
        # Actually, let's keep Frame at y=reveal_edge (Mechanically fixed to wall side? No, usually gap).
        # Let's assume the window is installed with a gap for the insulation.
        # New Frame Y Start: idx_reveal_edge + rev_ins_th_idx.
        
        # If window is deeper (Middle), the reveal is actually the masonry surface between corner and window.
        # The Reveal Insulation needs to cover this masonry surface.
        # Length of reveal insulation = pos_shift.
        # But our grid models Y as "Facade Length" and X as "Thickness".
        # If window moves in X, the "Reveal" surface is exposed on the X-face? No.
        # Let's visualize: 
        # Wall is vertical column. Window sits in hole.
        # If window is at 0 (Outer edge), the reveal is just the thickness of the insulation?
        # A "Laibung" is the surface perpendicular to the facade.
        # In our 2D Top-View (Ground Plan):
        # Wall is Horizontal or Vertical?
        # I treated Wall as Vertical Strip (X=Thickness).
        # And Window Leg as Horizontal Strip (Y=Length).
        # The Window Opening is at y > reveal_edge.
        # So the "Reveal" is the face of the wall at y=reveal_edge (The cut end of the wall).
        # This face spans x=0 to x=w_outer.
        
        # So if the window is pushed "inwards" (towards x=0), 
        # The Frame sits at x < w_outer.
        # The "Reveal" (Masonry surface) is the line at y=reveal_edge, from x=w_outer down to x=frame_outer.
        # THIS is the surface we insulate.
        
        # Determine Frame Y Position:
        # It still sits in the opening (y > reveal_edge).
        # Does it shift in Y? No, it just shifts in X.
        
        idx_f_y_start = idx_reveal_edge + rev_ins_th_idx
        idx_f_y_end = idx_f_y_start + f_width_idx
        
        self.grid_map[idx_f_y_start:idx_f_y_end, idx_f_x_start:idx_f_x_end] = self.ID_FRAME
        
        # Update Glass
        idx_g_y_start = idx_f_y_end
        idx_g_y_end = self.ny
        self.grid_map[idx_g_y_start:idx_g_y_end, idx_g_x_start:idx_g_x_end] = self.ID_GLASS
        
        # Place Reveal Insulation
        # Y: [idx_reveal_edge, idx_f_y_end - some_visible_frame?] 
        # Usually reveal ins covers frame partially.
        # Let's say it covers 30mm of the frame.
        # So it extends in Y from reveal_edge to (FrameStart + 30mm).
        # X: [idx_w_outer, idx_w_outer + something?]
        # No, X is along the thickness.
        # The reveal insulation is a board perpendicular to the facade.
        # It sits in the X-Y plane.
        # It fills the space between Masonry End (y=reveal_edge) and the visual opening.
        # Thickness is in Y direction? No, Thickness is in Y (relative to wall length) or X (relative to wall thickness)?
        # "Reveal insulation thickness" usually means the board thickness (Y direction in our plot).
        
        # Wait, schematic:
        # Masonry Wall: Horizontal in plot? Or Vertical?
        # I defined: X = Thickness, Y = Facade Length.
        # So Wall is a vertical strip? 
        # My setup: "Wall spans from x=0 to x=w_outer". This is a vertical strip.
        # So Y is the direction along the wall surface.
        # "Masonry extends from y=0 to y=reveal_edge".
        # So the REVEAL is a Horizontal cut at y=reveal_edge.
        
        # The Reveal Insulation is a board placed on this cut (y=reveal_edge).
        # So its thickness is in Y direction.
        # It extends in X direction from the Insulation Outer Corner inwards towards the frame.
        
        # So:
        # Y range: [idx_reveal_edge, idx_reveal_edge + rev_ins_th_idx]
        # X range: [idx_f_x_start + overlap?, idx_ins_edge?]
        # It connects to the External Insulation.
        # External insulation at the corner (y=reveal_edge) has thickness 'insulation_thick_min_mm'.
        # X max at corner = w_outer + ins_min.
        
        # So Reveal Insulation fills:
        # Y: [idx_reveal_edge, idx_reveal_edge + rev_ins_th_idx]
        # X: [idx_f_x_start + 10mm (small overlap on glass?), idx_w_outer + ins_min]
        # Actually it usually overlaps the frame, not the glass. 
        # Frame depth is 80mm. Overlap 40mm.
        # X_inner = idx_w_outer - (some overlap).
        # Frame is at X [w_outer - 80, w_outer].
        # Reveal insulation covers the joint. 
        
        if self.cfg.masonry_rebate_overlap_mm > 0:
             # Rebate Geometry: Masonry extends in front of the frame
             # X: [idx_win_outer_face, idx_w_outer] (The gap created by setting window deeper)
             # Y: [idx_reveal_edge, idx_reveal_edge + overlap]
             
             idx_reb_y_start = idx_reveal_edge
             idx_reb_y_end = idx_reveal_edge + to_idx(self.cfg.masonry_rebate_overlap_mm)
             idx_reb_x_start = idx_win_outer_face
             idx_reb_x_end = idx_w_outer
             
             # Fill Rebate with Wall Material
             self.grid_map[idx_reb_y_start:idx_reb_y_end, idx_reb_x_start:idx_reb_x_end] = self.ID_WALL
             
             # Important: If we have a rebate, the Frame placement below must acknowledge it.
             # The Frame is placed at idx_f_y_start = idx_reveal_edge + 15mm.
             # If rebate overlap is 50mm, then the first 35mm of the frame are covered by masonry.
             # The code below places FRAME over everything.
             # We should probably place Rebate AFTER Frame?
             # No, Frame is "behind" masonry.
             # So Place Frame FIRST (as planned below), THEN Place Masonry Rebate on top.
             pass

        
        # --- FIX 2 (Placement): Now place Window Frame & Glass ---
        # AFTER reveal insulation? 
        # If we stick to "Insulation covers Frame", Insulation should be LAST or Frame placed such that it doesn't overwrite.
        # But Frame is placed at idx_f_y_start = 15mm.
        # Insulation is at y=0mm to 30mm.
        # Overlap y=15mm to 30mm.
        # In this overlap, we want Insulation (on top/exterior).
        # So we should place Frame FIRST, then Insulation?
        # OR place Frame, then re-place Insulation intersection.
        
        # Let's Place Frame First (Logic moved up? No, simpler to just place it now and re-apply Insulation overlap if needed)
        # Actually, simpler: Place Frame. Then Place Insulation.
        # But 'uninsulated_reveal' logic removed insulation.
        
        # Correct Order:
        # 1. Place Frame (entire rect)
        # 2. Place Insulation (overwrites Frame in overlap zone)
        # 3. Handle uninsulated (replace Insulation with Air)
        
        # Re-Implementing Order:
        
        # 1. Place Frame
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
        # Y: Starts after Fixed Frame (minus overlap). 
        # Actually usually Sash sits *inside* (towards room) or *in front*?
        # In a standard inward-opening window:
        # Fixed frame is attached to wall. Sash is "inside" the opening (Y direction? No, Y is parallel to wall face).
        # Section view (top-down):
        # Wall is top/bottom? No, Wall is Left (or Right). X is depth. Y is facade length.
        # Wait, grid is [y, x]. 
        # Y=0 is deep in wall. Y=Reveal Edge is the corner.
        # Window is placed at Y > Reveal Edge (the opening).
        # So Fixed Frame is at "Reveal Edge + 15mm".
        # Sash is further "in" the opening (Higher Y).
        
        idx_sash_y_start = idx_ff_y_end - to_idx(overlap) # Overlap
        idx_sash_y_end = idx_sash_y_start + to_idx(sash_width)
        # Sash Depth: usually flush with Fixed Frame on the inside? Or shifted?
        # Let's align them on the "inside" (Room side) or "outside"?
        # Standard: Sash is slightly recessed from outside or flush.
        # Let's assume flush on the outside for simplicity, or 10mm recessed.
        # Re-reading standard details: Sash is often offset.
        # Let's put Sash flush with Fixed Frame outer face for visual simplicity unless specified.
        # Better: Recess Sash by 30mm from Fixed Frame outer face (User Request "More to inside").
        idx_sash_x_end = idx_ff_x_end - to_idx(30)
        idx_sash_x_start = idx_sash_x_end - to_idx(sash_depth)
        
        # Draw Fixed Frame
        self.grid_map[idx_ff_y_start:idx_ff_y_end, idx_ff_x_start:idx_ff_x_end] = self.ID_FRAME
        
        # Draw Sash
        self.grid_map[idx_sash_y_start:idx_sash_y_end, idx_sash_x_start:idx_sash_x_end] = self.ID_FRAME

        # Glass Position:
        # Centered in Sash?
        # Sash X range: [sash_x_start, sash_x_end]
        # Glass sits inside Sash groove.
        # Assuming Glass 24mm.
        idx_g_x_mid = int((idx_sash_x_start + idx_sash_x_end) / 2)
        idx_g_x_start = idx_g_x_mid - int(to_idx(24)/2)
        idx_g_x_end = idx_g_x_mid + int(to_idx(24)/2)
        
        # Glass Y: Starts inside Sash
        idx_g_y_start = idx_sash_y_start + to_idx(10) # Frame overlap
        # Extends to... end of domain? Or just cut off (infinite 2D)?
        # For Psi calculation, we model 1200mm window.
        idx_g_y_end = self.ny
        
        # Draw Glass
        self.grid_map[idx_g_y_start:idx_g_y_end, idx_g_x_start:idx_g_x_end] = self.ID_GLASS
        
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
            
            rev_ins_th_idx = to_idx(self.cfg.reveal_insulation_mm)
            
            # Y Range: Sits on the reveal face (Y > Reveal Edge)
            ri_y_start = idx_reveal_edge
            ri_y_end = idx_reveal_edge + rev_ins_th_idx
            
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
                # No solid? (Should not happen in our geometry, wall is everywhere or window)
                # If pure air row?
                pass

    def assign_materials(self):
        self.cond = np.zeros_like(self.temp)
        self.cond[self.grid_map == self.ID_WALL] = MAT_WALL
        self.cond[self.grid_map == self.ID_INSULATION] = MAT_INSULATION
        self.cond[self.grid_map == self.ID_REVEAL_INS] = MAT_REVEAL_INSULATION
        self.cond[self.grid_map == self.ID_FRAME] = MAT_FRAME_EQ
        self.cond[self.grid_map == self.ID_GLASS] = MAT_GLASS_UG11
        # Air
        self.cond[self.grid_map == self.ID_AIR_INT] = 0.025 # Approx static air or just exclude?
        # FDM usually requires conductive domain. Air cavities are modeled with equiv lambda.
        # Here we have "Outdoor Air" and "Indoor Air" as boundaries, not domains.
        # The grid points with 0 ID are "Outside the domain" -> Dirichlet or Neumann?
        # We handle boundaries explicitly.
        
    def solve(self, max_iter=10000, tol=1e-5):
        # Explicit or Iterative solver (Jacobi/SOR)
        # Using simple isotropic FDM steps
        # Grid is uniform dx
        
        # Create mask for valid cells (Material > 1)
        # Actually we compute everywhere and fix boundaries.
        
        # Boundary Arrays
        # Identify surface cells
        
        for k in range(max_iter):
            t_old = self.temp.copy()
            
            # Vectorized Update (Jacobi)
            # T_new = (T_up + T_down + T_left + T_right)/4 (if uniform lambda)
            # With variable lambda: Harmonic mean or simple average of neighbor conductance?
            # Standard: Heat balance at node i,j
            # sum(Cond_neighbor * (T_neighbor - T_i,j)) = 0
            
            # Simple 5-point stencil with varying k
            # k_ip = harmonic(k[i,j], k[i+1,j])
            
            # To speed up, we can assume constant lambda per cell and use resistance between nodes.
            # R_right = dx / (lambda_avg * dy*1) = 1/lambda_avg
            # Node formula: T_i,j = (sum T_n/R_n) / (sum 1/R_n)
            
            # Let's use simple shift for neighbor access
            # T = self.temp
            
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
            
            # Harmonic mean conductivity between cells
            # kw_up = 2 * k_c * k_up / (k_c + k_up + 1e-9)
            # Simplified: Arithmetic mean for standard FDM on interface?
            # Control volume method suggests harmonic mean for diffusion.
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
            # WITH Air Buffer, x=0 is the air boundary.
            # Usually far-field Air is constant T.
            t_new[:, 0] = TEMP_INT
            
            # 2. Surface Boundaries (Convection)
            # Apply Robin Boundary Condition or fix "Air" nodes to Air Temp + Resistance?
            # Easier: Detect surface nodes (neighbors to air or domain edge) and add a conductance term to Air Temp.
            # Or model Air as a material with effective conductivity?
            # R_surface = 1/h. dx/k_eq = R_surf. k_eq = dx/R_surf.
            # Set k for empty cells to k_eq and T to T_air.
            
            # k_rsi = self.dx / RSI_WALL
            # k_rse = self.dx / RSE
            
            # Identify Air Regions
            # Interior Air: x < wall, y > wall_end (The room side of the window)
            # Exterior Air: x > all_materials (Outdoor)
            
            # Let's refine the Grid Map:
            # 0 = Interior Air
            # 1 = Exterior Air
            # >1 = Solid
            
            # Update "Solid" mask
            is_solid = self.grid_map > 1
            
            # For non-solid cells, force Temp to Constant (Dirichlet for far field air?)
            # Or better: The nodes IN the air are constant. The nodes ON the surface interact.
            # My logic updated T everywhere. Now reset Air nodes.
            
            mask_int = self.grid_map == self.ID_AIR_INT
            mask_ext = self.grid_map == self.ID_AIR_EXT
            
            t_new[mask_int] = TEMP_INT
            t_new[mask_ext] = TEMP_EXT
            
            # Re-calculate boundary interaction for surface nodes?
            # The simplified update above (average of neighbors) works if Air nodes are neighbors with high conductivity?
            # No, we need explicit Surface Resistance.
            # Equation for surface node:
            # sum(g_neighbors * T_n) + g_air * T_air = 0
            # g_air = Area / R_s = dx / R_s (per depth 1) ??
            # In FDM 2D: Conductance G = k * (Area/Dist). Area=dx*1. Dist=dx. -> G = k_mat.
            # Surface Conductance G_s = h * Area = (1/Rs) * dx.
            
            # So if a node is adjacent to Air, we add (1/Rs * dx) to G_sum and (1/Rs * dx * T_air) to numerator.
            
            # Let's iterate over solid boundary nodes? specific logic for efficiency.
            # We can represent Air nodes as having an "Effective Conductivity" to the boundary.
            # g_link = 1 / (Rs + dx/2k)? No.
            
            # Simpler approach:
            # Assign "Fake Material" to Air cells with k_surf such that k_surf / (dx/2) = 1/Rs ?
            # Resistance from center of solid to surface = dx/(2k).
            # Resistance from surface to air = Rs.
            # Total R = dx/(2k) + Rs.
            # If we model the air node at distance dx/2 from surface node?
            # Let's set Air Node = T_Air.
            # Conductivity between Solid and Air Node = k_effective?
            # R_link = dx / k_eff. We want R_link = Rs + dx/(2k_solid). 
            # This depends on k_solid. Too complex for vectorized matrix.
            
            # Standard "Ghost Node" or "Convection Link":
            # Just use 1/Rs * dx as the conductance to the air temperature.
            
            # Vectorized implementation of surface BC:
            # Compute a "C_boundary" and "T_boundary_contribution" maps.
            
            # Resetting air nodes is correct (Dirichlet).
            # The flux from Air to Solid uses the "Material Conductivity" of the Air cell?
            # If we set k_air = dx / Rs ?
            # Then flux = k_air * (T_air - T_surf) / dx = (T_air - T_surf) / Rs. Correct.
            # So, we map the Air materials to specific conductivities:
            # k_int = self.dx / RSI_WALL
            # k_ext = self.dx / RSE
            
            k_eff_int = self.dx / RSI_WALL
            k_eff_ext = self.dx / RSE
            
            # Apply to Cond map
            self.cond[mask_int] = k_eff_int
            self.cond[mask_ext] = k_eff_ext
            
            # Now the standard harmonic mean update logic works, 
            # IF we consider the distance between Solid Center and Air Center is dx.
            # Flux = k_eff_air * (T_air - T_solid) / dx = (dx/Rs) * dT / dx = dT/Rs. Correct.
            
            # Only caveat: Harmonic mean of (k_solid, k_air_eff).
            # harm(k_s, k_a) = 2 ks ka / (ks+ka).
            # If ks >> ka, ~ 2 ka.
            # Flux ~ 2 * (dx/Rs) * dT / dx = 2 * dT / Rs. Factor of 2 error?
            # Because distance is dx, but interface is at dx/2.
            # If we put T_air at the neighbor node (dist dx), the resistance is Rs.
            # FDM assumes average k over dist dx.
            # If we set k_air such that R_total_link = Rs.
            # The simple harmonic mean handles interface conductivity.
            # We want R_eq = Rs. 
            # The solver sees R = dx / k_harm.
            # dx / (2 ks ka / (ks+ka)) = (ks+ka)dx / 2ks ka = dx/2ka + dx/2ks.
            # We want dx/2ka + dx/2ks = Rs + dx/2ks (internal resistance).
            # So we need dx/2ka = Rs. => ka = dx / (2 Rs).
            
            # Correction:
            k_eff_int = self.dx / (2 * self.rsi_value) # USE DYNAMIC RSI
            k_eff_ext = self.dx / (2 * RSE)
            
            self.cond[mask_int] = k_eff_int
            self.cond[mask_ext] = k_eff_ext
            
            # Re-run Update with fixed boundary nodes
            # Pre-compute conductances? No, k varies.
            
            # We need to enforce Dirichlet on Air Nodes *after* every step.
            
            self.temp = t_new
            self.temp[mask_int] = TEMP_INT
            self.temp[mask_ext] = TEMP_EXT
            
            if k % 1000 == 0:
                diff = np.max(np.abs(self.temp - t_old))
                # print(f"Iter {k}, Max Diff: {diff}")
                if diff < tol:
                    break
        
        return self.temp

    def calculate_psi(self):
        # 1. Total Heat Flow L2D
        # Sum heat flow through interior surface.
        # Flux = (T_air - T_surf) / Rs
        # Sum over all interface segments.
        
        flux_sum = 0.0
        
        # Identify interface nodes (Solid nodes with Air neighbors)
        mask_int = self.grid_map == self.ID_AIR_INT
        # Find solid neighbors
        # Iterate or convolution?
        
        # Simple loop over interior boundary cells
        # We know where the interior boundary is roughly.
        # Wall surface: x=0, y < reveal_edge
        # Reveal surface: y ~ reveal_edge, x < w_outer
        # Frame/Glass surface: y > reveal_edge...
        
        # Let's start with a generic integration:
        # P = sum ( T_air - T_surface_node ) * Area / R_link ?
        # R_link from logic above: R_link = R_surf + R_internal ~ R_surf (dominant) + dx/2k.
        # Flow = (T_int - T_node) / (Rsi + dx/(2*k_node))
        
        # Actually, we can calculate flow leaving the system boundaries (Air nodes).
        # Flow = sum over Air_Int_Nodes ( for each neighbor Solid: (T_air - T_sol) * conductance )
        # Conductance is the harmonic mean / dx formula we used.
        
        total_watts_per_m = 0.0
        
        # Iterate all INT AIR nodes
        # This is slow in python, but grid is small (500x500 max).
        
        rows, cols = self.grid_map.shape
        
        # optimization: find boundary indices
        # mask_int is boolean.
        # convolving mask_int with solid neighbors?
        
        # Let's just loop over the "Interior Surface" scan lines.
        # 1. Wall Surface (x=0)
        # 2. Window/Reveal geometry
        
        # Or calculate via external flux (Energy balance check).
        # Calculate Input Flux (Indoor) and Output Flux (Outdoor).
        
        # Let's do Input Flux.
        # Iterate all cells, check neighbors.
        # Vectorized Flux Calc?
        
        T = self.temp
        C = self.cond
        
        def get_flux(mask_from, mask_to, T_val_from):
            # Flux from 'mask_from' (Air) to 'mask_to' (Solid)
            # F = k_harm * (T_from - T_to) / dx * Area(dx)
            # Sum for all interfaces.
            
            total = 0
            # Up
            # mask_to_shift = np.roll(mask_to, 1, axis=0) # neighbors
            # Just look at transitions
            
            # Vertical interfaces (Left/Right)
            # (i, j) is Air, (i, j+1) is Solid
            # cond_h = harm(C[i,j], C[i,j+1])
            # q = cond_h * (T[i,j] - T[i,j+1]) / dx * dx = cond_h * (Ti - Ti+1)
            
            # Horizontal (i,j) Air, (i+1, j) Solid
            
            nonlocal T, C
            
            # Right Neighbors
            k_harm_r = 2*C[:,:-1]*C[:,1:] / (C[:,:-1]+C[:,1:] + 1e-12)
            # Flow from Left to Right
            q_r = k_harm_r * (T[:,:-1] - T[:,1:])
            # Filter where Left is Air, Right is Solid
            f_r = (mask_from[:,:-1] & mask_to[:,1:])
            total += np.sum(q_r[f_r])
            
            # Left Neighbors (Right to Left)
            # Flow from Right to Left = -q_r
            # Filter where Right is Air, Left is Solid
            f_l = (mask_from[:,1:] & mask_to[:,:-1])
            total += np.sum(-q_r[f_l])
            
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
        l2d_coeff = l2d_watts / delta_t # Restored Line
        
        # 2. Flux Balance Check (Fix 7)
        mask_ext_air = self.grid_map == self.ID_AIR_EXT
        q_in = l2d_watts
        q_out = get_flux(mask_ext_air, mask_all_solid, TEMP_EXT)
        q_out = get_flux(mask_ext_air, mask_all_solid, TEMP_EXT)
        balance_err = abs(q_in + q_out) / max(abs(q_in), 1e-9)
        # print(f"Flux Balance Error: {balance_err:.4%}") # Optional Log
        
        # 2. Reference L1D
        # Psi = L2D - sum(U_i * l_i)
        
        # U_wall (Masonry + Insulation)
        # U_wall (Masonry + Insulation)
        # 1/U = Rse + R_wall + Rsi = 0.04 + w_th/0.7 + 0.13
        # Check actual R-value path. Wall + Insulation.
        # r_tot = RSE + d_ins/lam_ins + d_wall/lam_wall + RSI_WALL
        # NOTE: Using 1D calculation for reference.
        # Reference Calculation ALWAYS uses Rsi=0.13 (Standard U-value definition)
        r_tot = RSE + (self.cfg.insulation_thick_max_mm/1000.0)/MAT_INSULATION + \
                (self.cfg.wall_thickness_mm/1000.0)/MAT_WALL + 0.13 
        u_wall_1d = 1.0 / r_tot
        
        # Lengths (External Dimensions)
        # From corner (y=500mm).
        # l_wall: Length of wall leg. y=0 to y=500. -> 0.5m.
        # Lengths (External Dimensions) (Fix 5: Dynamic)
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
        # Min Surface Temp on Interior Surface
        # Interior Surface Nodes: Neighbors of ID_AIR_INT
        # Extract surface nodes
        
        # Get mask of solid nodes ajacent to AIR_INT
        # Simple scan or reuse neighbor logic
        # Or just checking min temp of valid domain closer to interior?
        # Actually correct way: Check all Solid nodes that have an Air neighbor.
        
        min_surf_temp = TEMP_INT
        # Brute force scan surface
        rows, cols = self.grid_map.shape
        import scipy.ndimage as nd
        
        # Dilate Air Mask to find boundary
        # mask_int_air 
        # struct = nd.generate_binary_structure(2, 1)
        # boundary = nd.binary_dilation(mask_int_air, structure=struct) & ~mask_int_air
        # This gives solid nodes on boundary.
        
        # Just loop (fast enough) or use numpy logic if ndimage not available (it is usually)
        # Fallback manual dilation
        mask_boundary = np.zeros_like(mask_int_air)
        padded = np.pad(mask_int_air, 1)
        # Center | Up | Down | Left | Right
        m_up = padded[:-2, 1:-1]
        m_dn = padded[2:, 1:-1]
        m_lf = padded[1:-1, :-2]
        m_rt = padded[1:-1, 2:]
        boundary_candidates = (m_up | m_dn | m_lf | m_rt) & (~mask_int_air) & (self.grid_map > 1)
        
        # --- FIX 4: True Surface Temperature Calculation ---
        # Get coordinates of boundary nodes
        bound_y, bound_x = np.where(boundary_candidates)
        
        min_temp_all = TEMP_INT
        min_temp_wall = TEMP_INT
        min_temp_frame = TEMP_INT
        
        if len(bound_y) > 0:
            k_solid = self.cond[bound_y, bound_x]
            t_cell = self.temp[bound_y, bound_x]
            mats = self.grid_map[bound_y, bound_x]
            
            # Calculate Surface Temp Tsi
            # R1 = dx / (2 * k)
            # R2 = Rsi_used (self.rsi_value)
            # Tsi = (T_air * R1 + T_cell * R2) / (R1 + R2)
            
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
            else:
                 min_temp_glass = np.nan
        
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
        plt.title(f'Temperature Distribution (Thick: {self.cfg.wall_thickness_mm}mm)')
        plt.xlabel('Depth [mm]')
        plt.ylabel('Facade Length [mm]')
        
        # Verify orientation
        # Axis 0 is Y (Height), Axis 1 is X (Width)
        # Imshow expects [rows, cols]. origin lower puts index 0 at bottom.
        # Correct.
        
        plt.savefig(filename)

        plt.savefig(filename)

    def plot_geometry(self, filename="geometry_debug.png"):
        """Plots the Material ID map for rapid visual verification."""
        plt.figure(figsize=(12, 10))
        
        # Create a custom colormap for materials
        # ID_WALL=2, INS=3, REV=4, FRAM=5, GLAS=6, AIR_I=1, AIR_E=0
        cmap = plt.get_cmap('tab10', 10) # Simple fallback if cm.get_cmap warns
        
        plt.imshow(self.grid_map, cmap=cmap, origin='lower', extent=[0, self.width_mm, 0, self.height_mm], interpolation='nearest')
        plt.colorbar(label='Material ID (0=AirExt, 2=Wall, 3=Ins, 4=RevIns, 5=Frame, 6=Glass)')
        plt.title(f'Geometry Check: {filename}')
        plt.xlabel('Depth [mm]')
        plt.ylabel('Facade Length [mm]')
        plt.grid(True, color='white', alpha=0.3)
        plt.savefig(filename)
        plt.close()

# --- Main Scenarios ---
if __name__ == "__main__":
    # Define Calculation Configurations (Focused on 150mm Window Position)
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
    
    print("Starting Thermal Bridge Calculation...")
    
    for i, cfg in enumerate(configs):
        print(f"Calculating Case {i+1}...")
        
        # --- PASS 1: Calculate Psi (Rsi = 0.13) ---
        solver_psi = ThermalSolver(cfg, rsi_value=0.13)
        
        # JUST PLOT GEOMETRY for checking
        filename_geo = f"geometry_case_{i+1}.png"
        solver_psi.plot_geometry(filename_geo)
        
        # SKIP SOLVER for rapid iteration
        print(f"Geometry plotted: {filename_geo} (Skipping Solve)")
        continue
        
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

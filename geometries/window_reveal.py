"""
Window Reveal Geometry for Thermal Bridge Calculations

Refactored to use Element Library (elements.py) for cleaner composition.
Wraps CalculationConfig for backward compatibility.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometry import SketchGeometry, RefinementZone, MaterialID, CanvasConfig
from config import CalculationConfig, SpacerType, TEMP_INT, TEMP_EXT, RSI_WALL, RSE
from config import (
    MAT_WALL, MAT_INSULATION, MAT_REVEAL_INSULATION, MAT_FRAME_EQ, MAT_GLASS_UG11,
    MAT_SPACER_SWISS_ULTIMATE, MAT_SPACER_STAINLESS, MAT_SPACER_ALUMINUM, MAT_STYRODUR
)
# New constants for Shutter Rails
MAT_ALUMINUM = 160.0
MAT_CAVITY_ISO = 0.25      # Equivalent lambda for unventilated cavity
MAT_EPDM = 0.25
from typing import List

# Import Element Library
from elements import (
    add_rect, add_wall, add_insulation, add_insulation_tapered, 
    add_rebate_corner, add_window_detail
)

class WindowRevealGeometry(SketchGeometry):
    """
    Window reveal/jamb geometry composed using elements.py.
    Values match the coordinate system of valid results (1200x1000).
    """
    
    def __init__(self, config: CalculationConfig):
        super().__init__()
        self.cfg = config
        
        # --- 1. Coordinate Calculations ---
        self.OFF_X = 50.0  
        self.OFF_Y = 250.0 
        
        self.w_th = config.wall_thickness_mm
        self.pos = max(0, config.window_position_from_exterior_masonry_mm)
        
        # X Coordinates (Absolute)
        self.x_wall_int = self.OFF_X
        self.x_wall_ext = self.OFF_X + self.w_th
        self.x_win_outer = self.x_wall_ext - self.pos
        
        # Y Coordinates
        self.y_bottom = 0.0
        self.y_reveal = self.OFF_Y
        self.y_top = self.OFF_Y + 250.0 
        
        # Frame Dimensions
        self.f_depth = config.frame_depth_mm
        self.f_width = config.frame_width_mm
        
        # Calculate derived frame coordinates for Air Polygon
        self.x_f_end = self.x_win_outer
        self.x_f_start = self.x_f_end - self.f_depth
        self.y_f_start = self.y_reveal
        # self.y_f_end derived in add_window_detail

        # Sash Dimensions (for Air Polygon trace)
        self.sash_overlap = 10.0
        self.sash_depth = 70.0
        self.sash_width = 70.0
        self.sash_recess = 30.0
        self.glass_thick = 24.0
        
        # --- 2. Build Elements ---
        
        # Reveal Shift (Removal of masonry reveal for insulation)
        # As requested: "move the respective wall parts down (on the x-axis) 
        # so that the reveal insulation fits between the shutter rails and the wall."
        # We interpret this as lowering the wall height by the insulation thickness
        # for the entire depth of the reveal (from window to exterior).
        self.reveal_shift_y = 0.0
        if config.reveal_insulation_mm > 0 and not config.uninsulated_reveal:
            self.reveal_shift_y = float(config.reveal_insulation_mm)

        # A. Interior Air (Complex Polygon)
        # We define this manually because it follows a unique contour
        self._build_interior_air_polygon()
        
        # B. Wall
        # Split wall into interior and exterior (reveal) parts
        w_int = self.x_win_outer - self.x_wall_int
        w_ext = self.x_wall_ext - self.x_win_outer
        
        # Interior Part (Full height)
        add_wall(self, self.x_wall_int, self.y_bottom, w_int, self.y_reveal)
        
        # Reveal Part (Lowered by reveal_shift_y)
        add_wall(self, self.x_win_outer, self.y_bottom, w_ext, self.y_reveal - self.reveal_shift_y)
        
        # C. Rebate (if present)
        rebate_h = float(config.masonry_rebate_overlap_mm)
        if rebate_h > 0:
            # Rebate sits on the LOWERED wall surface
            y_rebate_start = self.y_reveal - self.reveal_shift_y
            
            add_rebate_corner(self, 
                              x_corner=self.x_win_outer, 
                              y_corner=y_rebate_start,
                              rebate_depth=w_ext,
                              rebate_height=rebate_h)
            
        # D. Insulation (External)
        if config.insulation_thick_max_mm > 0:
            self._build_external_insulation(config, rebate_h)

        # E. Reveal Insulation
        if config.reveal_insulation_mm > 0 and not config.uninsulated_reveal:
            self._build_reveal_insulation(config, rebate_h)
            
        # F. Window Assembly (Frame + Sash + Glass)
        add_window_detail(self,
                          x_frame_start=self.x_f_start,
                          y_frame_start=self.y_reveal,
                          frame_depth=self.f_depth, # 70
                          frame_width=self.f_width, # 70
                          sash_depth=self.sash_depth, # 70
                          sash_width=self.sash_width, # 70
                          sash_overlap=self.sash_overlap, # 10
                          sash_recess=self.sash_recess, # 30
                          glass_thickness=self.glass_thick, # 24
                          y_top=self.y_top, # 500
                          mat_frame_lambda=MAT_FRAME_EQ,
                          mat_glass_lambda=MAT_GLASS_UG11)

        # G. Shutter Rails (ISG + Aussteller)
        self._build_shutter_rails()

        # --- 3. Canvas Config ---
        self._configure_canvas()

    def _build_interior_air_polygon(self):
        """Define the complex interior air shape."""
        # Calculate sash/glass helpers for tracing
        # Coordinates matching add_window_detail logic
        y_f_end = self.y_f_start + self.f_width
        
        x_sash_end = self.x_f_end - self.sash_recess
        x_sash_start = x_sash_end - self.sash_depth
        y_sash_start = y_f_end - self.sash_overlap
        y_sash_end = y_sash_start + self.sash_width
        
        glass_mid_x = (x_sash_start + x_sash_end) / 2
        x_glass_start = glass_mid_x - self.glass_thick / 2
        
        # Helper Points
        self.add_point("AirInt_BL", 0.0, self.y_bottom)
        self.add_point("Wall_BL", self.x_wall_int, self.y_bottom)
        self.add_point("Wall_TL", self.x_wall_int, self.y_reveal)
        self.add_point("Frame_BL", self.x_f_start, self.y_reveal)
        self.add_point("Frame_Int_Step", self.x_f_start, y_sash_start)
        self.add_point("Sash_BL", x_sash_start, y_sash_start)
        self.add_point("Sash_TL", x_sash_start, y_sash_end)
        self.add_point("Sash_Glass_Step", x_glass_start, y_sash_end)
        self.add_point("Glass_TL", x_glass_start, self.y_top)
        self.add_point("AirInt_TopLeft", 0.0, self.y_top)
        
        poly_points = [
            "AirInt_BL", "Wall_BL", "Wall_TL", "Frame_BL", 
            "Frame_Int_Step", "Sash_BL", "Sash_TL", "Sash_Glass_Step",
            "Glass_TL", "AirInt_TopLeft"
        ]
        
        self.add_shape(poly_points, MaterialID.AIR_INT, 0.025, "Interior Air")

    def _build_external_insulation(self, config, rebate_h):
        ins_max = config.insulation_thick_max_mm
        taper_len = config.taper_length_mm
        
        x_ins_start = self.x_wall_ext
        # Exterior wall part height is (y_reveal - reveal_shift_y)
        y_ins_top = self.y_reveal - self.reveal_shift_y + rebate_h
        
        if taper_len > 0:
            # Tapered
            y_taper_start = y_ins_top - float(taper_len)
            thick_top = config.insulation_thick_min_mm
            
            # 1. Main Block (Bottom to Taper Start)
            add_insulation(self, x_ins_start, self.y_bottom, ins_max, y_taper_start - self.y_bottom,
                           lambda_val=MAT_INSULATION, name="Insulation Main")
            
            # 2. Tapered Part
            # Check for Styrodur Variant
            if config.use_styrodur_variant:
                mat_taper = MAT_STYRODUR
                id_taper = MaterialID.STYRODUR
            else:
                mat_taper = MAT_INSULATION
                id_taper = MaterialID.INSULATION
            
            add_insulation_tapered(self,
                                   x_base=x_ins_start,
                                   y_bottom=y_taper_start,
                                   y_top=y_ins_top,
                                   thick_main=ins_max,
                                   thick_taper=thick_top,
                                   taper_start_y=y_taper_start, # Redundant here but API takes it
                                   lambda_val=mat_taper,
                                   name="Insulation Taper",
                                   material_id=id_taper)
        else:
            # Uniform Block
            add_insulation(self, x_ins_start, self.y_bottom, ins_max, y_ins_top - self.y_bottom,
                           lambda_val=MAT_INSULATION)

    def _build_reveal_insulation(self, config, rebate_h):
        rev_ins = config.reveal_insulation_mm
        if config.use_styrodur_variant:
            rev_mat = MAT_STYRODUR
            rev_id = MaterialID.STYRODUR
            rev_ins = min(rev_ins, 30.0)
        else:
            rev_mat = MAT_REVEAL_INSULATION
            rev_id = MaterialID.REVEAL_INS
            
        y_masonry_top = self.y_reveal - self.reveal_shift_y + float(rebate_h)
        x_start = self.x_win_outer
        
        thick_min = config.insulation_thick_min_mm
        taper_len = config.taper_length_mm
        ins_max = config.insulation_thick_max_mm

        if taper_len > 0 and (ins_max > thick_min):
            # Prolong the taper from the external insulation through the reveal insulation layer
            # Slope m = (thick_max - thick_min) / taper_length
            m = (ins_max - thick_min) / float(taper_len)
            taper_delta = m * rev_ins
            
            x_end_bottom = self.x_wall_ext + thick_min
            x_end_top = x_end_bottom - taper_delta
            
            # Define tapered polygon
            self.add_point("RevIns_BL", x_start, y_masonry_top)
            self.add_point("RevIns_BR", x_end_bottom, y_masonry_top)
            self.add_point("RevIns_TR", x_end_top, y_masonry_top + rev_ins)
            self.add_point("RevIns_TL", x_start, y_masonry_top + rev_ins)
            
            self.add_shape(["RevIns_BL", "RevIns_BR", "RevIns_TR", "RevIns_TL"], 
                           rev_id, rev_mat, "Reveal Insulation Tapered")
        else:
            # Simple rectangular reveal insulation
            width = (self.x_wall_ext + thick_min) - x_start
            add_rect(self, "Reveal Insulation", x_start, y_masonry_top, width, rev_ins,
                     rev_id, rev_mat)

    def _build_shutter_rails(self):
        """
        Add Insect Screen (ISG) and Shutter Rails.
        Reference: 'Außenkante Rahmen' (x_win_outer) & 'Vorderkante' (y_reveal).
        Flow: Frame Edge -> ISG -> Seal -> Shutter -> Exterior
        """
        # --- 1. ISG Rail (Insect Screen) ---
        # 28mm wide (along Y), 35mm deep (along X)
        # Position: "Direkt auf dem Rahmen" (Starts at x_win_outer?)
        # Wait, if it is "Auf dem Rahmen" and "Vor... ISG", and user Reference X=0 is Frame Edge.
        # Implemented logic:
        # My X = User Y (Depth/Outwards +)
        # My Y = User X (Width/Along Frame)
        
        isg_width = 53.0 # Manufacturer: 53mm
        isg_depth = 22.0 # Measured: 22mm
        wall_th = 2.0
        
        # Shift Y by 53mm ("Thickness of reveal") to start in clear opening
        # clearing the masonry rebate (typically 50mm).
        # "take the absolute value here, not a reveal based variable" -> Use fixed 53.0
        y_offset = 53.0 
        
        x_isg_start = self.x_win_outer
        y_isg_start = self.y_reveal + y_offset # Start after the rebate/offset
        
        # Outer Alu Box
        add_rect(self, "ISGRail_Alu", x_isg_start, y_isg_start, 
                 isg_depth, isg_width, MaterialID.ALUMINUM, MAT_ALUMINUM)
        
        # Inner Cavity (18 x 49)
        add_rect(self, "ISGRail_Air", 
                 x_isg_start + wall_th, y_isg_start + wall_th,
                 isg_depth - 2*wall_th, isg_width - 2*wall_th,
                 MaterialID.CAVITY, MAT_CAVITY_ISO)

        # --- 2. Seal (Keder) ---
        # 1mm thick, between ISG and Shutter
        # Contact area is based on overlap. Both 53mm now.
        seal_depth = 1.0
        x_seal_start = x_isg_start + isg_depth
        
        add_rect(self, "RailSeal", x_seal_start, y_isg_start,
                 seal_depth, isg_width, 
                 MaterialID.SPACER, MAT_EPDM)

        # --- 3. Shutter Rail (Rollladen) ---
        # 53mm wide (along Y), 22mm deep (along X)
        shutter_width = 53.0
        shutter_depth = 22.0
        
        x_shut_start = x_seal_start + seal_depth
        y_shut_start = y_isg_start # Same Y position as ISG (aligned)
        
        # Outer Alu Box
        add_rect(self, "ShutRail_Alu", x_shut_start, y_shut_start,
                 shutter_depth, shutter_width, MaterialID.ALUMINUM, MAT_ALUMINUM)
                 
        # Inner Cavity (49 x 18) -> 53-4 x 22-4 (2mm wall)
        add_rect(self, "ShutRail_Air", 
                 x_shut_start + wall_th, y_shut_start + wall_th,
                 shutter_depth - 2*wall_th, shutter_width - 2*wall_th,
                 MaterialID.CAVITY, MAT_CAVITY_ISO)


    def _configure_canvas(self):
        # Domain: Ensure enough space for insulation + exterior air buffer
        buffer_width = 150.0 
        if self.cfg.insulation_thick_max_mm > 0:
            required_width = float(self.cfg.insulation_thick_max_mm) + 50.0
            buffer_width = max(buffer_width, required_width)
        x_dom_max = self.x_wall_ext + buffer_width
        
        self.set_canvas(0.0, x_dom_max, 
                        0.0, self.y_top, 
                        grid_mm=self.cfg.grid_size_mm)

    def get_canvas_config(self) -> CanvasConfig:
        # Just delegate to parent or helper, but parent logic implementation needs access 
        # to the _canvas_override.
        # However, refinement zones need this logic duplicated? 
        # No, simpler: just call the super/SketchGeometry functionality if setup correct.
        # But we need to return specific refinement config.
        # Let's keep the logic matching _configure_canvas to be safe.
        cfg = super().get_canvas_config()
        # Override finer grids
        cfg.fine_dx_mm = 0.5
        cfg.fine_dy_mm = 0.5
        cfg.ultra_dx_mm = 0.25
        cfg.ultra_dy_mm = 0.25
        return cfg

    def get_refinement_zones(self) -> List[RefinementZone]:
        config = self.get_canvas_config()
        zones = []
        
        # Reveal Corner (Critical)
        zones.append(RefinementZone(
            x_min=self.x_f_start - 20,
            x_max=self.x_wall_ext + 30,
            y_min=self.y_reveal - 30,
            y_max=self.y_reveal + 100,
            target_dx=config.fine_dx_mm,
            priority=2
        ))
        
        return zones

    def get_spacer_lambda(self) -> float:
        if self.cfg.spacer_type == SpacerType.SWISS_ULTIMATE:
            return MAT_SPACER_SWISS_ULTIMATE
        elif self.cfg.spacer_type == SpacerType.STAINLESS_STEEL:
            return MAT_SPACER_STAINLESS
        elif self.cfg.spacer_type == SpacerType.ALUMINUM:
            return MAT_SPACER_ALUMINUM
        return 0.14

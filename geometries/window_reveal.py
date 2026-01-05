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
        
        # A. Interior Air (Complex Polygon)
        # We define this manually because it follows a unique contour
        self._build_interior_air_polygon()
        
        # B. Wall
        # 360mm or 450mm wall block
        add_wall(self, self.x_wall_int, self.y_bottom, self.w_th, self.y_reveal)
        
        # C. Rebate (if present)
        rebate_h = float(config.masonry_rebate_overlap_mm)
        if rebate_h > 0:
            # Rebate sits on top of wall corner (shoulder)
            # x_corner is where window touches wall? 
            # In original code: x_min=x_win_outer, x_max=x_wall_ext
            # Width = x_wall_ext - x_win_outer ??
            # Wait, "x_win_outer" is "exterior face of window frame".
            # Window position "150mm from exterior masonry"
            # If wall is flush with rebate (typical), then rebate depth defines where window sits.
            # Original code: Add Rect(x_win_outer, x_wall_ext).
            # Width = x_wall_ext - x_win_outer.
            rebate_depth = self.x_wall_ext - self.x_win_outer
            
            add_rebate_corner(self, 
                              x_corner=self.x_win_outer, 
                              y_corner=self.y_reveal,
                              rebate_depth=rebate_depth,
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
        y_ins_top = self.y_reveal + rebate_h
        
        if taper_len > 0:
            # Tapered
            y_taper_start = y_ins_top - float(taper_len)
            thick_top = config.insulation_thick_min_mm
            
            # 1. Main Block (Bottom to Taper Start)
            add_insulation(self, x_ins_start, self.y_bottom, ins_max, y_taper_start - self.y_bottom,
                           lambda_val=MAT_INSULATION, name="Insulation Main")
            
            # 2. Tapered Part
            # Check for Styrodur Variant
            mat_taper = MAT_STYRODUR if config.use_styrodur_variant else MAT_INSULATION
            
            add_insulation_tapered(self,
                                   x_base=x_ins_start,
                                   y_bottom=y_taper_start,
                                   y_top=y_ins_top,
                                   thick_main=ins_max,
                                   thick_taper=thick_top,
                                   taper_start_y=y_taper_start, # Redundant here but API takes it
                                   lambda_val=mat_taper,
                                   name="Insulation Taper")
        else:
            # Uniform Block
            add_insulation(self, x_ins_start, self.y_bottom, ins_max, y_ins_top - self.y_bottom,
                           lambda_val=MAT_INSULATION)

    def _build_reveal_insulation(self, config, rebate_h):
        rev_ins = config.reveal_insulation_mm
        rev_mat = MAT_STYRODUR if config.use_styrodur_variant else MAT_REVEAL_INSULATION
        
        if config.use_styrodur_variant:
            rev_ins = min(rev_ins, 30.0)
            
        y_base = self.y_reveal + (float(rebate_h) if rebate_h > 0 else 0)
        
        # Reveal Insulation sits on top of the rebate/masonry shoulder
        x_start = self.x_win_outer
        # Extends outwards to cover the masonry/insulation interface?
        x_end = self.x_wall_ext + config.insulation_thick_min_mm
        width = x_end - x_start
        
        add_rect(self, "Reveal Insulation", x_start, y_base, width, rev_ins,
                 MaterialID.REVEAL_INS, rev_mat)

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

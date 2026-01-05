"""
Window Reveal Geometry for Thermal Bridge Calculations

Refactored to use SketchGeometry (Points + Shapes).
Wraps CalculationConfig for backward compatibility.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometry import SketchGeometry, RefinementZone, MaterialID
from config import CalculationConfig, SpacerType, TEMP_INT, TEMP_EXT, RSI_WALL, RSE
from config import (
    MAT_WALL, MAT_INSULATION, MAT_REVEAL_INSULATION, MAT_FRAME_EQ, MAT_GLASS_UG11,
    MAT_SPACER_SWISS_ULTIMATE, MAT_SPACER_STAINLESS, MAT_SPACER_ALUMINUM
)
from typing import List

class WindowRevealGeometry(SketchGeometry):
    """
    Window reveal/jamb geometry for thermal bridge calculations.
    
    Refactored to use named Points and PolygonShapes.
    Matches the coordinate system of valid results (1200x1000).
    """
    
    def __init__(self, config: CalculationConfig):
        super().__init__()
        self.cfg = config
        
        # --- Canvas Setup ---
        # Match dimensions from analyze_images (approx 1200x1000)
        # Assuming Wall starts at some offset.
        # Based on ref: Wall is a block approx 360mm wide.
        # Let's use similar OFF_X, OFF_Y but reduced Y range.
        
        self.OFF_X = 50.0  
        self.OFF_Y = 500.0 
        
        self.w_th = config.wall_thickness_mm
        self.pos = max(0, config.window_position_from_exterior_masonry_mm)
        
        # X Coordinates (Absolute)
        self.x_int_air_left = 0.0
        self.x_wall_int = self.OFF_X
        self.x_wall_ext = self.OFF_X + self.w_th
        self.x_win_outer = self.x_wall_ext - self.pos
        
        # Y Coordinates
        self.y_bottom = 0.0
        self.y_reveal = self.OFF_Y
        self.y_top = self.OFF_Y + 500.0 # Total height 1000
        
        # Frame
        self.f_depth = config.frame_depth_mm
        self.f_width = config.frame_width_mm
        self.x_f_end = self.x_win_outer
        self.x_f_start = self.x_f_end - self.f_depth
        
        self.y_f_start = self.y_reveal
        self.y_f_end = self.y_f_start + self.f_width
        
        # Sash
        self.sash_overlap = 10
        self.sash_depth = 70
        self.sash_width = 70
        self.sash_recess = 30
        
        self.x_sash_end = self.x_f_end - self.sash_recess
        self.x_sash_start = self.x_sash_end - self.sash_depth
        
        self.y_sash_start = self.y_f_end - self.sash_overlap
        self.y_sash_end = self.y_sash_start + self.sash_width
        
        # Glass
        self.glass_thick = 24
        self.glass_mid_x = (self.x_sash_start + self.x_sash_end) / 2
        self.x_glass_start = self.glass_mid_x - self.glass_thick / 2
        self.x_glass_end = self.glass_mid_x + self.glass_thick / 2
        self.y_glass_start = self.y_sash_start + 10
        
        
        # --- Points Definitions ---
        
        # 1. Interior Air
        # Left of wall, up to top
        self.add_point("AirInt_BL", self.x_int_air_left, self.y_bottom)
        self.add_point("AirInt_BR", self.x_wall_int, self.y_bottom)
        self.add_point("AirInt_TR", self.x_wall_int, self.y_top)
        self.add_point("AirInt_TL", self.x_int_air_left, self.y_top)
        
        self.add_shape(["AirInt_BL", "AirInt_BR", "AirInt_TR", "AirInt_TL"],
                       material_id=MaterialID.AIR_INT, lambda_val=0.025,
                       name="Interior Air")

        # 2. Wall (Masonry LEG)
        # From bottom to reveal height
        self.add_point("Wall_BL", self.x_wall_int, self.y_bottom)
        self.add_point("Wall_BR", self.x_wall_ext, self.y_bottom)
        self.add_point("Wall_TR", self.x_wall_ext, self.y_reveal)
        self.add_point("Wall_TL", self.x_wall_int, self.y_reveal)
        
        self.add_shape(["Wall_BL", "Wall_BR", "Wall_TR", "Wall_TL"],
                       material_id=MaterialID.WALL, lambda_val=MAT_WALL,
                       name="Wall")
                       
        # 3. Rebate (if present)
        rebate = config.masonry_rebate_overlap_mm
        if rebate > 0:
            y_rebate_end = self.y_reveal + float(rebate)
            
            # The rebate sits on top of the wall leg, extending inwards from exterior face
            # Wait, rebate overlap means it creates a "nose" for the window to sit against.
            # Usually creates an L-shape wall.
            # Shape: Rectangle on top of wall corner?
            # Bounds: x_win_outer to x_wall_ext, y_reveal to y_reveal + rebate
            
            self.add_point("Reb_BL", self.x_win_outer, self.y_reveal)
            self.add_point("Reb_BR", self.x_wall_ext, self.y_reveal)
            self.add_point("Reb_TR", self.x_wall_ext, y_rebate_end)
            self.add_point("Reb_TL", self.x_win_outer, y_rebate_end)
            
            self.add_shape(["Reb_BL", "Reb_BR", "Reb_TR", "Reb_TL"],
                           material_id=MaterialID.WALL, lambda_val=MAT_WALL,
                           name="Rebate")

        # 4. Insulation (External)
        if config.insulation_thick_max_mm > 0:
            ins_max = config.insulation_thick_max_mm
            taper_len = config.taper_length_mm
            
            x_ins_start = self.x_wall_ext
            x_ins_end = x_ins_start + ins_max
            
            self.add_point("Ins_BL", x_ins_start, self.y_bottom)
            self.add_point("Ins_BR", x_ins_end, self.y_bottom)
            
            # Taper logic
            rebate_h = float(config.masonry_rebate_overlap_mm)
            y_ins_top = self.y_reveal + rebate_h
            
            if taper_len > 0:
                y_taper_start = y_ins_top - float(taper_len)
                x_ins_min_end = x_ins_start + config.insulation_thick_min_mm # at corner
                
                self.add_point("Ins_Taper_Start", x_ins_end, y_taper_start)
                self.add_point("Ins_Top_Corner", x_ins_min_end, y_ins_top)
                self.add_point("Ins_Top_Inner", x_ins_start, y_ins_top)
                
                self.add_shape(["Ins_BL", "Ins_BR", "Ins_Taper_Start", "Ins_Top_Corner", "Ins_Top_Inner"],
                               material_id=MaterialID.INSULATION, lambda_val=MAT_INSULATION,
                               name="Insulation")
            else:
                 self.add_point("Ins_Top_Outer", x_ins_end, y_ins_top)
                 self.add_point("Ins_Top_Inner", x_ins_start, y_ins_top)
                 
                 self.add_shape(["Ins_BL", "Ins_BR", "Ins_Top_Outer", "Ins_Top_Inner"],
                                material_id=MaterialID.INSULATION, lambda_val=MAT_INSULATION,
                                name="Insulation")

        # 5. Reveal Insulation
        if config.reveal_insulation_mm > 0 and not config.uninsulated_reveal:
            rev_ins = config.reveal_insulation_mm
            y_base = self.y_reveal + (float(rebate) if rebate > 0 else 0)
            
            # Assuming reveal insulation wraps the rebate or lines the reveal
            # Based on standard details: it lines the masonry face perpendicular to window
            # Here: on top of rebate? Or lining the rebate "vertical" face?
            # Let's assume on top of rebate/wall shoulder.
            
            x_start = self.x_win_outer
            x_end = self.x_wall_ext + config.insulation_thick_min_mm
            
            # Logic: block above the masonry/rebate
            
            self.add_point("Rev_BL", x_start, y_base)
            self.add_point("Rev_BR", x_end, y_base)
            self.add_point("Rev_TR", x_end, y_base + rev_ins)
            self.add_point("Rev_TL", x_start, y_base + rev_ins)
            
            self.add_shape(["Rev_BL", "Rev_BR", "Rev_TR", "Rev_TL"],
                           material_id=MaterialID.REVEAL_INS, lambda_val=MAT_REVEAL_INSULATION,
                           name="Reveal Insulation")

        # 6. Frame
        self.add_point("Frame_BL", self.x_f_start, self.y_f_start)
        self.add_point("Frame_BR", self.x_f_end, self.y_f_start)
        self.add_point("Frame_TR", self.x_f_end, self.y_f_end)
        self.add_point("Frame_TL", self.x_f_start, self.y_f_end)
        
        self.add_shape(["Frame_BL", "Frame_BR", "Frame_TR", "Frame_TL"],
                       material_id=MaterialID.FRAME, lambda_val=MAT_FRAME_EQ,
                       name="Fixed Frame")
                       
        # 7. Sash
        self.add_point("Sash_BL", self.x_sash_start, self.y_sash_start)
        self.add_point("Sash_BR", self.x_sash_end, self.y_sash_start)
        self.add_point("Sash_TR", self.x_sash_end, self.y_sash_end)
        self.add_point("Sash_TL", self.x_sash_start, self.y_sash_end)
        
        self.add_shape(["Sash_BL", "Sash_BR", "Sash_TR", "Sash_TL"],
                       material_id=MaterialID.FRAME, lambda_val=MAT_FRAME_EQ,
                       name="Sash")
                       
        # 8. Glass
        self.add_point("Glass_BL", self.x_glass_start, self.y_glass_start)
        self.add_point("Glass_BR", self.x_glass_end, self.y_glass_start)
        self.add_point("Glass_TR", self.x_glass_end, self.y_top)
        self.add_point("Glass_TL", self.x_glass_start, self.y_top)
        
        self.add_shape(["Glass_BL", "Glass_BR", "Glass_TR", "Glass_TL"],
                       material_id=MaterialID.GLASS, lambda_val=MAT_GLASS_UG11,
                       name="Glass")
                       
        # Set Canvas
        # Everything outside these shapes is AIR_EXT (Default)
        # But we explicitly defined AIR_INT
        # So AIR_INT shape overrides AIR_EXT default
        # WALL overrides AIR_INT where it might overlap? (Usually disjoint)
        
        # Domain: Fixed 1000mm width as requested
        x_dom_max = 1000.0
        
        self.set_canvas(0.0, x_dom_max, 
                        0.0, self.y_top, 
                        grid_mm=config.grid_size_mm)
                        
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
        """Get thermal conductivity for configured spacer type."""
        if self.cfg.spacer_type == SpacerType.SWISS_ULTIMATE:
            return MAT_SPACER_SWISS_ULTIMATE
        elif self.cfg.spacer_type == SpacerType.STAINLESS_STEEL:
            return MAT_SPACER_STAINLESS
        elif self.cfg.spacer_type == SpacerType.ALUMINUM:
            return MAT_SPACER_ALUMINUM
        return 0.14  # Default

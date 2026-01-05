"""
Window Reveal Geometry for Thermal Bridge Calculations

Provides a GeometryBuilder implementation for window reveal/jamb thermal bridges
that wraps the existing CalculationConfig for backward compatibility.

Usage:
    from config import CalculationConfig
    from geometries.window_reveal import WindowRevealGeometry
    
    config = CalculationConfig(wall_thickness_mm=360, ...)
    geometry = WindowRevealGeometry(config)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometry import (
    GeometryBuilder, CanvasConfig, GeometryRegion,
    RefinementZone, MaterialID
)
from config import CalculationConfig, SpacerType, TEMP_INT, TEMP_EXT, RSI_WALL, RSE
from config import (
    MAT_WALL, MAT_INSULATION, MAT_REVEAL_INSULATION, MAT_FRAME_EQ, MAT_GLASS_UG11,
    MAT_SPACER_SWISS_ULTIMATE, MAT_SPACER_STAINLESS, MAT_SPACER_ALUMINUM
)
from typing import List


class WindowRevealGeometry(GeometryBuilder):
    """
    Window reveal/jamb geometry for thermal bridge calculations.
    
    Wraps CalculationConfig for backward compatibility while using
    the new geometry/mesh module structure.
    
    Coordinate system:
    - x=0: Interior masonry face
    - x=wall_thickness: Exterior masonry face (reveal corner)
    - y=0: Reveal edge (masonry corner)
    - y<0: Wall leg (deep into wall, away from window)
    - y>0: Window leg (towards window/facade)
    """
    
    def __init__(self, config: CalculationConfig):
        """
        Args:
            config: CalculationConfig with wall/insulation/window parameters
        """
        self.cfg = config
        
        # Pre-calculate key geometry values
        self.w_th = config.wall_thickness_mm
        self.pos = max(0, config.window_position_from_exterior_masonry_mm)
        self.win_outer = self.w_th - self.pos  # Window outer face X
        
        # Frame dimensions
        self.f_depth = config.frame_depth_mm
        self.f_width = config.frame_width_mm
        self.f_x_end = self.win_outer
        self.f_x_start = self.f_x_end - self.f_depth
        
        # Sash dimensions
        self.sash_recess = 30  # mm from window outer face
        self.sash_depth = 70
        self.sash_width = 70
        self.sash_overlap = 10  # overlap with fixed frame
        
        self.sash_x_end = self.f_x_end - self.sash_recess
        self.sash_x_start = self.sash_x_end - self.sash_depth
        
        # Glass (centered in sash, 24mm thick)
        self.glass_thick = 24
        self.glass_mid_x = (self.sash_x_start + self.sash_x_end) / 2
        self.glass_x_start = self.glass_mid_x - self.glass_thick / 2
        self.glass_x_end = self.glass_mid_x + self.glass_thick / 2
        
        # Domain bounds
        self.x_min = -50  # Interior air buffer
        self.x_max = self.w_th + config.insulation_thick_max_mm + 500  # Far field
        self.y_min = -500  # Wall leg (500mm)
        self.y_max = 1000  # Window leg (1m)
        
    def get_canvas_config(self) -> CanvasConfig:
        # Use grid_size from config if available, else reasonable default
        base_grid = getattr(self.cfg, 'grid_size_mm', 2.5)
        
        return CanvasConfig(
            x_min_mm=self.x_min,
            x_max_mm=self.x_max,
            y_min_mm=self.y_min,
            y_max_mm=self.y_max,
            default_dx_mm=max(5.0, base_grid * 2),  # Coarse areas
            default_dy_mm=max(5.0, base_grid * 2),
            fine_dx_mm=base_grid,  # Detail areas use config grid size
            fine_dy_mm=base_grid,
            ultra_dx_mm=max(0.5, base_grid / 2),  # Only for ultra-fine details
            ultra_dy_mm=max(0.5, base_grid / 2),
        )
    
    def get_regions(self) -> List[GeometryRegion]:
        """
        Build regions from background to foreground.
        Order matters - later regions override earlier ones.
        """
        regions = []
        
        rebate = self.cfg.masonry_rebate_overlap_mm
        taper_len = self.cfg.taper_length_mm
        
        # 1. Interior Air (background for y>0, x<0)
        regions.append(GeometryRegion(
            name="Interior Air",
            material_id=MaterialID.AIR_INT,
            x_min=self.x_min, x_max=0,
            y_min=self.y_min, y_max=self.y_max,
            lambda_w_mk=0.025
        ))
        
        # 2. Wall (Masonry) - Base
        regions.append(GeometryRegion(
            name="Wall",
            material_id=MaterialID.WALL,
            x_min=0, x_max=self.w_th,
            y_min=self.y_min, y_max=0,
            lambda_w_mk=MAT_WALL
        ))
        
        # 3. Masonry Rebate (nose) if present
        if rebate > 0:
            regions.append(GeometryRegion(
                name="Rebate",
                material_id=MaterialID.WALL,
                x_min=self.win_outer, x_max=self.w_th,
                y_min=0, y_max=rebate,
                lambda_w_mk=MAT_WALL
            ))
        
        # 4. Exterior Insulation (ETICS) if present
        if self.cfg.insulation_thick_max_mm > 0:
            # Insulation with taper
            # For simplicity, define as rectangle - taper handled via shape predicate
            ins_x_max = self.w_th + self.cfg.insulation_thick_max_mm
            ins_x_min_at_corner = self.w_th + self.cfg.insulation_thick_min_mm
            
            def insulation_shape(X, Y):
                """Tapered insulation shape predicate."""
                # Below taper start: full thickness
                full_thick = Y < -taper_len
                
                # In taper zone: linear interpolation
                in_taper = (Y >= -taper_len) & (Y <= 0)
                if taper_len > 0:
                    f = (Y + taper_len) / taper_len  # 0 at taper start, 1 at corner
                    max_x_at_y = self.w_th + self.cfg.insulation_thick_max_mm - \
                                 f * (self.cfg.insulation_thick_max_mm - self.cfg.insulation_thick_min_mm)
                    taper_ok = X <= max_x_at_y
                else:
                    taper_ok = X <= ins_x_max
                    
                return full_thick | (in_taper & taper_ok)
            
            regions.append(GeometryRegion(
                name="Insulation",
                material_id=MaterialID.INSULATION,
                x_min=self.w_th, x_max=ins_x_max,
                y_min=self.y_min, y_max=0,
                lambda_w_mk=MAT_INSULATION,
                shape_predicate=insulation_shape
            ))
        
        # 5. Reveal Insulation if present
        if self.cfg.reveal_insulation_mm > 0 and not self.cfg.uninsulated_reveal:
            rev_y_start = rebate
            rev_y_end = rebate + self.cfg.reveal_insulation_mm
            rev_x_end = self.w_th + self.cfg.insulation_thick_min_mm
            
            regions.append(GeometryRegion(
                name="Reveal Insulation",
                material_id=MaterialID.REVEAL_INS,
                x_min=self.win_outer, x_max=rev_x_end,
                y_min=rev_y_start, y_max=rev_y_end,
                lambda_w_mk=MAT_REVEAL_INSULATION
            ))
        
        # 6. Window Frame (Fixed Frame)
        regions.append(GeometryRegion(
            name="Fixed Frame",
            material_id=MaterialID.FRAME,
            x_min=self.f_x_start, x_max=self.f_x_end,
            y_min=0, y_max=self.f_width,
            lambda_w_mk=MAT_FRAME_EQ
        ))
        
        # 7. Sash (overlaps frame)
        sash_y_start = self.f_width - self.sash_overlap
        sash_y_end = sash_y_start + self.sash_width
        
        regions.append(GeometryRegion(
            name="Sash",
            material_id=MaterialID.FRAME,
            x_min=self.sash_x_start, x_max=self.sash_x_end,
            y_min=sash_y_start, y_max=sash_y_end,
            lambda_w_mk=MAT_FRAME_EQ
        ))
        
        # 8. L-Profile extension (back of sash to frame)
        ext_y_end = 80.0
        if ext_y_end > self.f_width:
            regions.append(GeometryRegion(
                name="Frame Extension",
                material_id=MaterialID.FRAME,
                x_min=self.sash_x_end, x_max=self.f_x_end,
                y_min=self.f_width, y_max=ext_y_end,
                lambda_w_mk=MAT_FRAME_EQ
            ))
        
        # 9. Glass (extends from sash upward)
        glass_y_start = sash_y_start + 10  # 10mm overlap
        
        regions.append(GeometryRegion(
            name="Glass",
            material_id=MaterialID.GLASS,
            x_min=self.glass_x_start, x_max=self.glass_x_end,
            y_min=glass_y_start, y_max=self.y_max,
            lambda_w_mk=MAT_GLASS_UG11
        ))
        
        # 10. Exterior Air (everything right of structure)
        # This is handled by detecting "outside" after material assignment
        
        return regions
    
    def get_critical_x_points(self) -> List[float]:
        """Key X coordinates for mesh alignment."""
        points = [
            self.x_min,
            0,  # Interior masonry face
            self.f_x_start,
            self.sash_x_start,
            self.glass_x_start,
            self.glass_x_end,
            self.sash_x_end,
            self.f_x_end,
            self.win_outer,
            self.w_th,
            self.w_th + self.cfg.insulation_thick_min_mm,
            self.w_th + self.cfg.insulation_thick_max_mm,
            self.x_max,
        ]
        # Filter to valid range and unique
        return sorted(set(p for p in points if self.x_min <= p <= self.x_max))
    
    def get_critical_y_points(self) -> List[float]:
        """Key Y coordinates for mesh alignment."""
        points = [
            self.y_min,
            -self.cfg.taper_length_mm,
            0,  # Reveal edge
            self.cfg.masonry_rebate_overlap_mm,
            self.cfg.masonry_rebate_overlap_mm + self.cfg.reveal_insulation_mm,
            self.f_width,  # Frame top
            self.f_width - self.sash_overlap,  # Sash start
            self.f_width - self.sash_overlap + self.sash_width,  # Sash end
            self.f_width - self.sash_overlap + 10,  # Glass start
            80.0,  # Extension end
            self.y_max,
        ]
        return sorted(set(p for p in points if self.y_min <= p <= self.y_max))
    
    def get_refinement_zones(self) -> List[RefinementZone]:
        """Define zones requiring finer mesh resolution."""
        config = self.get_canvas_config()
        zones = []
        
        # Near reveal corner - use fine resolution (not ultra)
        # This is the critical thermal bridge region
        zones.append(RefinementZone(
            x_min=self.f_x_start - 10,
            x_max=self.w_th + 30,
            y_min=-30,
            y_max=100,
            target_dx=config.fine_dx_mm,
            priority=2
        ))
        
        # Frame/sash area - fine resolution
        zones.append(RefinementZone(
            x_min=self.f_x_start,
            x_max=self.f_x_end,
            y_min=0,
            y_max=self.f_width + self.sash_width,
            target_dx=config.fine_dx_mm,
            priority=1
        ))
        
        # Taper zone - slightly finer than default
        if self.cfg.taper_length_mm > 0:
            zones.append(RefinementZone(
                x_min=self.w_th,
                x_max=self.w_th + self.cfg.insulation_thick_max_mm,
                y_min=-self.cfg.taper_length_mm,
                y_max=0,
                target_dx=config.fine_dx_mm,
                priority=1
            ))
        
        return zones
    
    def get_boundary_conditions(self) -> dict:
        return {
            'fixed_regions': [
                (MaterialID.AIR_INT, TEMP_INT),
                (MaterialID.AIR_EXT, TEMP_EXT),
            ],
            'surface_resistance': {
                MaterialID.AIR_INT: RSI_WALL,
                MaterialID.AIR_EXT: RSE,
            }
        }
    
    def get_spacer_lambda(self) -> float:
        """Get thermal conductivity for configured spacer type."""
        if self.cfg.spacer_type == SpacerType.SWISS_ULTIMATE:
            return MAT_SPACER_SWISS_ULTIMATE
        elif self.cfg.spacer_type == SpacerType.STAINLESS_STEEL:
            return MAT_SPACER_STAINLESS
        elif self.cfg.spacer_type == SpacerType.ALUMINUM:
            return MAT_SPACER_ALUMINUM
        return 0.14  # Default


if __name__ == "__main__":
    # Quick test with sample config
    from config import CalculationConfig
    
    cfg = CalculationConfig(
        wall_thickness_mm=360,
        insulation_thick_max_mm=100,
        insulation_thick_min_mm=30,
        reveal_insulation_mm=30,
        taper_length_mm=150,
        window_position_from_exterior_masonry_mm=150,
        masonry_rebate_overlap_mm=50,
    )
    
    geom = WindowRevealGeometry(cfg)
    canvas = geom.get_canvas_config()
    
    print(f"Canvas: {canvas.width_mm} x {canvas.height_mm} mm")
    print(f"  X: [{canvas.x_min_mm}, {canvas.x_max_mm}]")
    print(f"  Y: [{canvas.y_min_mm}, {canvas.y_max_mm}]")
    print(f"\nRegions ({len(geom.get_regions())}):")
    for r in geom.get_regions():
        print(f"  - {r.name}: ({r.x_min:.0f}-{r.x_max:.0f}) x ({r.y_min:.0f}-{r.y_max:.0f})")
    print(f"\nCritical X: {geom.get_critical_x_points()}")
    print(f"Critical Y: {geom.get_critical_y_points()}")
    print(f"\nRefinement Zones: {len(geom.get_refinement_zones())}")

"""
Element Library for Window Reveal Geometries

Provides factory functions to add common building elements to a SketchGeometry.
Uses absolute coordinates (mm).
"""

from geometry import SketchGeometry, MaterialID
from geometry import SketchGeometry, MaterialID
from config import (
    MAT_WALL, MAT_INSULATION, MAT_STYRODUR, 
    MAT_FRAME_EQ, MAT_GLASS_UG11, MAT_REVEAL_INSULATION
)

def add_rect(sketch: SketchGeometry, 
             name_prefix: str, 
             x: float, y: float, 
             width: float, height: float, 
             material_id: int, 
             lambda_val: float):
    """
    Add a generic rectangular element.
    """
    p1 = f"{name_prefix}_BL"
    p2 = f"{name_prefix}_BR"
    p3 = f"{name_prefix}_TR"
    p4 = f"{name_prefix}_TL"
    
    sketch.add_point(p1, x, y)
    sketch.add_point(p2, x + width, y)
    sketch.add_point(p3, x + width, y + height)
    sketch.add_point(p4, x, y + height)
    
    sketch.add_shape([p1, p2, p3, p4], material_id, lambda_val, name_prefix)

def add_wall(sketch: SketchGeometry, 
             x: float, y: float, 
             width: float, height: float, 
             lambda_val: float = MAT_WALL):
    """
    Add a masonry wall block.
    """
    add_rect(sketch, "Wall", x, y, width, height, MaterialID.WALL, lambda_val)

def add_insulation(sketch: SketchGeometry, 
                   x: float, y: float, 
                   width: float, height: float, 
                   lambda_val: float = MAT_INSULATION,
                   name="Insulation",
                   material_id: int = MaterialID.INSULATION):
    """
    Add a rectangular insulation block.
    """
    add_rect(sketch, name, x, y, width, height, material_id, lambda_val)

def add_insulation_tapered(sketch: SketchGeometry, 
                           x_base: float,     # Inner face of insulation (against wall)
                           y_bottom: float,   # Bottom of insulation
                           y_top: float,      # Top of insulation (at reveal)
                           thick_main: float, # Max thickness
                           thick_taper: float,# Min thickness at top
                           taper_start_y: float, # Y where taper begins
                           lambda_val: float = MAT_INSULATION,
                           name="InsulationTapered",
                           material_id: int = MaterialID.INSULATION):
    """
    Add tapered insulation (wedge shape).
    
    Orientation: Vertical wall, insulation on *right* of x_base? 
    No, usually external insulation is on the outside.
    Assuming x_base is the interface between Wall and Insulation.
    Direction: Insulation extends from x_base to x_base + thickness.
    
    Shape:
    1. Rectangular part from y_bottom to taper_start_y
    2. Wedge part from taper_start_y to y_top
    """
    
    # Points
    # Bottom (Rect)
    sketch.add_point(f"{name}_BL", x_base, y_bottom)
    sketch.add_point(f"{name}_BR", x_base + thick_main, y_bottom)
    
    # Taper Start (Rect top/Wedge bottom)
    sketch.add_point(f"{name}_MidL", x_base, taper_start_y)
    sketch.add_point(f"{name}_MidR", x_base + thick_main, taper_start_y)
    
    # Top (Wedge top)
    sketch.add_point(f"{name}_TL", x_base, y_top) # Assuming flush with wall at top?
    sketch.add_point(f"{name}_TR", x_base + thick_taper, y_top)
    
    # Shape
    # BL -> BR -> MidR -> TR -> TL -> MidL -> BL
    # Or split into 2 shapes? One shape is fine.
    
    pts = [
        f"{name}_BL",
        f"{name}_BR",
        f"{name}_MidR", 
        f"{name}_TR", 
        f"{name}_TL", 
        f"{name}_MidL"
    ]
    
    sketch.add_shape(pts, material_id, lambda_val, name)

def add_guard_rail(sketch: SketchGeometry,
                   x: float, y: float, 
                   width: float, height: float,
                   lambda_val: float = 50.0): # 50 = Steel (approx guide)
    """
    Add rolling shutter guard rail.
    """
    add_rect(sketch, "GuardRail", x, y, width, height, MaterialID.FRAME, lambda_val) # Use Frame ID for convenience/color

def add_rebate_corner(sketch: SketchGeometry,
                      x_corner: float, # The logical corner of the opening
                      y_corner: float, # The logical corner of the opening (reveal height)
                      rebate_depth: float, # How deep into the wall (horizontal overlap?)
                      rebate_height: float, # How high up the reveal (vertical overlap)
                      lambda_val=MAT_WALL):
    """
    Add a masonry rebate (nose) that extends into the opening.
    Usually modeled as a rectangle added on top of the wall corner.
    """
    if rebate_height <= 0 or rebate_depth <= 0:
        return

    # In WindowRevealGeometry, rebate sits on top of wall:
    # y_rebate_end = y_reveal + rebate
    # x extends from x_win_outer to x_wall_ext (width = rebate_depth?)
    # Wait, rebate_depth in this fn means width.
    # We assume caller provides correct width.
    
    add_rect(sketch, "Rebate", x_corner, y_corner, rebate_depth, rebate_height, MaterialID.WALL, lambda_val)

def add_window_detail(sketch: SketchGeometry,
                      x_frame_start: float, # Left edge of fixed frame
                      y_frame_start: float, # Bottom of fixed frame (sill/reveal)
                      frame_depth: float,
                      frame_width: float,
                      sash_depth: float,
                      sash_width: float,
                      sash_overlap: float,
                      sash_recess: float, # Distance from frame outer edge to sash outer edge
                      glass_thickness: float,
                      y_top: float, # Top of glass/domain
                      mat_frame_lambda=MAT_FRAME_EQ,
                      mat_glass_lambda=MAT_GLASS_UG11,
                      name="Window"):
    """
    Add detailed window assembly: Fixed Frame, Sash, Glass.
    Matches logic from WindowRevealGeometry.
    """
    # Coordinates Calculation
    x_f_end = x_frame_start + frame_depth
    y_f_end = y_frame_start + frame_width
    
    # Sash
    # x_sash_end = x_f_end - sash_recess
    # x_sash_start = x_sash_end - sash_depth
    x_sash_end = x_f_end - sash_recess
    x_sash_start = x_sash_end - sash_depth
    
    y_sash_start = y_f_end - sash_overlap
    y_sash_end = y_sash_start + sash_width
    
    # Glass
    glass_mid_x = (x_sash_start + x_sash_end) / 2
    x_glass_start = glass_mid_x - glass_thickness / 2
    x_glass_end = glass_mid_x + glass_thickness / 2
    y_glass_start = y_sash_start + 10 # Glass sits 10mm into sash?
    
    # 1. Fixed Frame
    add_rect(sketch, f"{name}_Fixed", x_frame_start, y_frame_start, 
             frame_depth, frame_width, MaterialID.FRAME, mat_frame_lambda)
             
    # 2. Sash
    add_rect(sketch, f"{name}_Sash", x_sash_start, y_sash_start,
             sash_depth, sash_width, MaterialID.FRAME, mat_frame_lambda)
             
    # 3. Glass
    glass_height = y_top - y_glass_start
    add_rect(sketch, f"{name}_Glass", x_glass_start, y_glass_start,
             glass_thickness, glass_height, MaterialID.GLASS, mat_glass_lambda)

    # Note: Does not create Air polygons. Callers responsibility.

def add_box_frame(sketch: SketchGeometry, x, y, w, h, mat_id=MaterialID.FRAME, lam=0.13, name="Frame"):
    add_rect(sketch, name, x, y, w, h, mat_id, lam)


class ElementBasedGeometry(SketchGeometry):
    """
    Geometry defined by a sequence of element factory functions.
    """
    def __init__(self, build_steps, canvas_bounds):
        super().__init__()
        
        # Execute build steps
        for step in build_steps:
            # step is a callable that takes (sketch)
            step(self)
            
        self.set_canvas(*canvas_bounds)


def add_air_cutout(sketch: SketchGeometry, x, y, width, height, name="AirCutout"):
    """
    Cut out a rectangular region by overwriting with External Air.
    Place this AFTER adding solid elements to effectively 'remove' material.
    """
    # Using 0.025 for air lambda to be safe, though usually handled by BCs
    add_rect(sketch, name, x, y, width, height, MaterialID.AIR_EXT, 0.025)


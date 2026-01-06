# Copyright (C) 2026 Thomas
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Element Library for Window Reveal Geometries

Provides factory functions and classes to add common building elements to a SketchGeometry.
Uses absolute coordinates (mm).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.core.geometry import SketchGeometry, MaterialID
from backend.core.config import (
    MAT_WALL, MAT_INSULATION, MAT_STYRODUR, 
    MAT_FRAME_EQ, MAT_GLASS_UG11, MAT_REVEAL_INSULATION,
    MAT_ALUMINUM, MAT_AIR_EXT, MAT_AIR_INT
)

# Base Class
class Element(ABC):
    def __init__(self, sketch: SketchGeometry, **params):
        self.sketch = sketch
        self.params = params
        self.name = params.get('name', f"{self.__class__.__name__}")
        self.material_id = params.get('material_id', MaterialID.WALL)
        self.lambda_val = float(params.get('lambda_val', 0.5))

    @abstractmethod
    def build(self):
        """Construct the element geometry on the sketch."""
        pass

    def _get_param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)


class RectElement(Element):
    def __init__(self, sketch: SketchGeometry, **params):
        super().__init__(sketch, **params)
        self.x = float(self._get_param('x', 0.0))
        self.y = float(self._get_param('y', 0.0))
        self.width = float(self._get_param('width', 0.0))
        self.height = float(self._get_param('height', 0.0))
        
    def build(self):
        p1 = f"{self.name}_BL"
        p2 = f"{self.name}_BR"
        p3 = f"{self.name}_TR"
        p4 = f"{self.name}_TL"
        
        self.sketch.add_point(p1, self.x, self.y)
        self.sketch.add_point(p2, self.x + self.width, self.y)
        self.sketch.add_point(p3, self.x + self.width, self.y + self.height)
        self.sketch.add_point(p4, self.x, self.y + self.height)
        
        self.sketch.add_shape([p1, p2, p3, p4], self.material_id, self.lambda_val, self.name)


class Wall(RectElement):
    def __init__(self, sketch: SketchGeometry, **params):
        params.setdefault('material_id', MaterialID.WALL)
        params.setdefault('lambda_val', MAT_WALL)
        super().__init__(sketch, **params)


class Insulation(RectElement):
    def __init__(self, sketch: SketchGeometry, **params):
        params.setdefault('material_id', MaterialID.INSULATION)
        params.setdefault('lambda_val', MAT_INSULATION)
        super().__init__(sketch, **params)


class Air(RectElement):
    def __init__(self, sketch: SketchGeometry, **params):
        # Default to AIR_EXT, but check 'type' or 'subtype' param for INT
        subtype = params.get('type', 'ext').lower()
        if subtype == 'int' or subtype == 'internal':
             params.setdefault('material_id', MaterialID.AIR_INT)
             params.setdefault('lambda_val', MAT_AIR_INT)
        else:
             params.setdefault('material_id', MaterialID.AIR_EXT)
             params.setdefault('lambda_val', MAT_AIR_EXT)
        super().__init__(sketch, **params)


class InsulationTapered(Element):
    def build(self):
        x_base = float(self._get_param('x_base', 0.0))
        y_bottom = float(self._get_param('y_bottom', 0.0))
        y_top = float(self._get_param('y_top', 0.0))
        thick_main = float(self._get_param('thick_main', 0.0))
        thick_taper = float(self._get_param('thick_taper', 0.0))
        taper_start_y = float(self._get_param('taper_start_y', 0.0))
        
        name = self.name
        
        # Points
        self.sketch.add_point(f"{name}_BL", x_base, y_bottom)
        self.sketch.add_point(f"{name}_BR", x_base + thick_main, y_bottom)
        
        self.sketch.add_point(f"{name}_MidL", x_base, taper_start_y)
        self.sketch.add_point(f"{name}_MidR", x_base + thick_main, taper_start_y)
        
        self.sketch.add_point(f"{name}_TR", x_base + thick_taper, y_top)
        self.sketch.add_point(f"{name}_TL", x_base, y_top)
        
        pts = [
            f"{name}_BL", f"{name}_BR",
            f"{name}_MidR", f"{name}_TR", 
            f"{name}_TL", f"{name}_MidL"
        ]
        
        self.sketch.add_shape(pts, self.material_id, self.lambda_val, name)


class WindowDetail(Element):
    def build(self):
        x_fs = float(self._get_param('x_frame_start', 0))
        y_fs = float(self._get_param('y_frame_start', 0))
        fd = float(self._get_param('frame_depth', 0))
        fw = float(self._get_param('frame_width', 0))
        sd = float(self._get_param('sash_depth', 0))
        sw = float(self._get_param('sash_width', 0))
        sov = float(self._get_param('sash_overlap', 0))
        srec = float(self._get_param('sash_recess', 0))
        gt = float(self._get_param('glass_thickness', 0))
        y_top = float(self._get_param('y_top', 0))
        
        mat_frame = self._get_param('mat_frame_lambda', MAT_FRAME_EQ)
        mat_glass = self._get_param('mat_glass_lambda', MAT_GLASS_UG11)
        name = self.name

        # Coordinates
        x_f_end = x_fs + fd
        y_f_end = y_fs + fw
        
        x_sash_end = x_f_end - srec
        x_sash_start = x_sash_end - sd
        
        y_sash_start = y_f_end - sov
        y_glass_start = y_sash_start + 10
        
        glass_mid_x = (x_sash_start + x_sash_end) / 2
        x_glass_start = glass_mid_x - gt / 2
        
        # 1. Fixed Frame
        self._add_rect(f"{name}_Fixed", x_fs, y_fs, fd, fw, MaterialID.FRAME, mat_frame)
             
        # 2. Sash
        self._add_rect(f"{name}_Sash", x_sash_start, y_sash_start, sd, sw, MaterialID.FRAME, mat_frame)
             
        # 3. Glass
        glass_height = y_top - y_glass_start
        self._add_rect(f"{name}_Glass", x_glass_start, y_glass_start, gt, glass_height, MaterialID.GLASS, mat_glass)

    def _add_rect(self, sub_name, x, y, w, h, mid, lam):
        RectElement(self.sketch, name=sub_name, x=x, y=y, width=w, height=h, material_id=mid, lambda_val=lam).build()


class CustomElement(Element):
    """Bridge for generic construction if needed."""
    def build(self):
        pass


# --- New Advanced Macros ---

class RollerShutterBox(RectElement):
    """
    Parametric Roller Shutter Box with insulation.
    Simplified representation: Box frame + Insulation wedge + Air cavity.
    """
    def __init__(self, sketch: SketchGeometry, **params):
        params.setdefault('material_id', MaterialID.CONCRETE) # or whatever the box is made of
        params.setdefault('lambda_val', 2.0) # Concrete-ish
        super().__init__(sketch, **params)
        
    def build(self):
        # Determine specific geometry from params
        # For now, just a placeholder box, but we can make it more detailed later
        # Example: 
        # - Box Shell
        # - Internal Insulation
        # - External Inspection Lid
        
        # Draw the main box (shell)
        super().build() 
        
        # If we want detailed internals, we would add them here as sub-shapes
        # For example, adding an insulation layer inside
        ins_thick = float(self._get_param('insulation_thickness', 0.0))
        if ins_thick > 0:
            RectElement(self.sketch, 
                name=f"{self.name}_Insulation",
                x=self.x + 10, # arbitrary offset for now
                y=self.y + 10,
                width=self.width - 20,
                height=ins_thick,
                material_id=MaterialID.INSULATION,
                lambda_val=MAT_INSULATION
            ).build()


class WindowSill(Element):
    """
    External Aluminum Sill and Internal Stone/Wood Sill.
    """
    def build(self):
        x = float(self._get_param('x', 0))
        y = float(self._get_param('y', 0))
        width = float(self._get_param('width', 0)) # Total width available
        
        # Internal params
        depth_int = float(self._get_param('depth_int', 200))
        thick_int = float(self._get_param('thick_int', 20))
        mat_int = self._get_param('material_int', 'stone') # stone or wood
        
        # External params
        depth_ext = float(self._get_param('depth_ext', 150))
        thick_ext = float(self._get_param('thick_ext', 2)) # Aluminum sheet
        
        lambda_int = 2.3 if mat_int == 'stone' else 0.13
        lambda_ext = MAT_ALUMINUM
        
        # Internal Sill
        RectElement(self.sketch, 
            name=f"{self.name}_Int",
            x=x - depth_int, 
            y=y, 
            width=depth_int, 
            height=thick_int, 
            material_id=MaterialID.CONCRETE, # Placeholder ID
            lambda_val=lambda_int
        ).build()
        
        # External Sill (sloped?) -> Simplified as rect for now
        RectElement(self.sketch, 
            name=f"{self.name}_Ext",
            x=x, # Starts at window face?
            y=y, # Starts at sill level
            width=depth_ext, 
            height=thick_ext, 
            material_id=MaterialID.ALUMINUM,
            lambda_val=lambda_ext
        ).build()


class VenetianBlindBox(RectElement):
    """
    Recessed box for Venetian Blinds (Raffstore).
    Usually taller and narrower than roller shutter boxes, open at bottom.
    """
    def build(self):
        # Base box
        super().build()
        
        # Add side insulation if requested
        ins_thick = float(self._get_param('insulation_thickness', 0.0))
        if ins_thick > 0:
            RectElement(self.sketch, 
                name=f"{self.name}_Insulation_Back",
                x=self.x, 
                y=self.y,
                width=self.width,
                height=ins_thick, # Insulation at top? Or back? assuming back means top or inner side
                material_id=MaterialID.INSULATION,
                lambda_val=MAT_INSULATION
            ).build()

class RoofJunction(Element):
    """
    Eaves detail: Wall meets Roof.
    Simplified: Wall continues up, Roof rafter angles down.
    """
    def build(self):
        x_wall = float(self._get_param('x_wall', 0))
        y_wall_top = float(self._get_param('y_wall_top', 3000))
        wall_width = float(self._get_param('wall_width', 360))
        
        # Add Wall segment
        RectElement(self.sketch,
            name=f"{self.name}_Wall",
            x=x_wall,
            y=y_wall_top - 500, # arbitrary start
            width=wall_width,
            height=500,
            material_id=MaterialID.WALL, 
            lambda_val=MAT_WALL
        ).build()
        
        # Add Rafter (wood)
        # Simplified as a generic block for now, angling requires Polygon
        # TODO: Implement angled rafter using PolygonShape when we have generic polygon support in Element
        pass

class PolygonElement(Element):
    """
    Generic Polygon Element.
    Expects 'points' parameter (list of point names).
    """
    def build(self):
        pt_names = self._get_param('points', [])
        if not pt_names:
            print(f"[WARNING] PolygonElement '{self.name}' has no points.")
            return
            
        self.sketch.add_shape(pt_names, self.material_id, self.lambda_val, self.name)


class Factory:
    @staticmethod
    def create(type_name: str, sketch: SketchGeometry, **params) -> Element:
        map_ = {
            'rect': RectElement,
            'wall': Wall,
            'insulation': Insulation,
            'air': Air,  # Added Air
            'insulation_tapered': InsulationTapered,
            'insulation_tapered': InsulationTapered,
            'window_detail': WindowDetail,
            'roller_shutter': RollerShutterBox,
            'window_sill': WindowSill,
            'venetian_blind': VenetianBlindBox,
            'roof_junction': RoofJunction,
            'polygon': PolygonElement,
        }
        
        cls = map_.get(type_name.lower())
        if cls:
            return cls(sketch, **params)
        else:
            # Fallback or error
            print(f"[WARNING] Unknown element type '{type_name}', using generic RectElement.")
            return RectElement(sketch, **params)


# --- Backward Compatibility Wrappers ---

def add_rect(sketch: SketchGeometry, name_prefix: str, x: float, y: float, width: float, height: float, material_id: int, lambda_val: float):
    RectElement(sketch, name=name_prefix, x=x, y=y, width=width, height=height, material_id=material_id, lambda_val=lambda_val).build()

def add_wall(sketch: SketchGeometry, x: float, y: float, width: float, height: float, lambda_val: float = MAT_WALL):
    Wall(sketch, x=x, y=y, width=width, height=height, lambda_val=lambda_val).build()

def add_insulation(sketch: SketchGeometry, x: float, y: float, width: float, height: float, lambda_val: float = MAT_INSULATION, name="Insulation", material_id: int = MaterialID.INSULATION):
    Insulation(sketch, x=x, y=y, width=width, height=height, lambda_val=lambda_val, name=name, material_id=material_id).build()

def add_insulation_tapered(sketch: SketchGeometry, x_base: float, y_bottom: float, y_top: float, thick_main: float, thick_taper: float, taper_start_y: float, lambda_val: float = MAT_INSULATION, name="InsulationTapered", material_id: int = MaterialID.INSULATION):
    InsulationTapered(sketch, x_base=x_base, y_bottom=y_bottom, y_top=y_top, thick_main=thick_main, thick_taper=thick_taper, taper_start_y=taper_start_y, lambda_val=lambda_val, name=name, material_id=material_id).build()

def add_window_detail(sketch, x_frame_start, y_frame_start, frame_depth, frame_width, sash_depth, sash_width, sash_overlap, sash_recess, glass_thickness, y_top, mat_frame_lambda=MAT_FRAME_EQ, mat_glass_lambda=MAT_GLASS_UG11, name="Window"):
    WindowDetail(sketch, x_frame_start=x_frame_start, y_frame_start=y_frame_start, frame_depth=frame_depth, frame_width=frame_width, sash_depth=sash_depth, sash_width=sash_width, sash_overlap=sash_overlap, sash_recess=sash_recess, glass_thickness=glass_thickness, y_top=y_top, mat_frame_lambda=mat_frame_lambda, mat_glass_lambda=mat_glass_lambda, name=name).build()

def add_guard_rail(sketch, x, y, width, height, lambda_val=50.0):
    RectElement(sketch, name="GuardRail", x=x, y=y, width=width, height=height, material_id=MaterialID.FRAME, lambda_val=lambda_val).build()

def add_rebate_corner(sketch, x_corner, y_corner, rebate_depth, rebate_height, lambda_val=MAT_WALL):
    if rebate_height <= 0 or rebate_depth <= 0: return
    RectElement(sketch, name="Rebate", x=x_corner, y=y_corner, width=rebate_depth, height=rebate_height, material_id=MaterialID.WALL, lambda_val=lambda_val).build()

def add_box_frame(sketch, x, y, w, h, mat_id=MaterialID.FRAME, lam=0.13, name="Frame"):
    RectElement(sketch, name=name, x=x, y=y, width=w, height=h, material_id=mat_id, lambda_val=lam).build()

def add_air_cutout(sketch, x, y, width, height, name="AirCutout"):
    RectElement(sketch, name=name, x=x, y=y, width=width, height=height, material_id=MaterialID.AIR_EXT, lambda_val=0.025).build()

# For legacy class support ??
class ElementBasedGeometry(SketchGeometry):
    def __init__(self, build_steps, canvas_bounds):
        super().__init__()
        for step in build_steps:
            step(self)
        self.set_canvas(*canvas_bounds)

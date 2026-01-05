"""
ISO 10211 Test Case 2: Multi-Material Bridge

Refactored to use Element Library (elements.py).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometry import SketchGeometry, RefinementZone, MaterialID
from elements import add_rect
from typing import List


# Material IDs for ISO Case 2
MAT_INSULATION = 200
MAT_CONCRETE = 201
MAT_WOOD = 202
MAT_ALUMINUM = 203
MAT_AIR_INT = 204
MAT_AIR_EXT = 205


class ISOCase2Geometry(SketchGeometry):
    """
    ISO 10211 Test Case 2: Multi-Material Thermal Bridge
    """
    
    def __init__(self, grid_mm: float = 0.25):
        super().__init__()
        self.grid_mm = grid_mm
        
        self.rsi = 0.11
        self.rse = 0.06
        
        # --- Define Geometry using Elements ---
        
        # 1. Base Insulation (Full Domain Background)
        # 0-500 x 0-47.5
        add_rect(self, "InsulationBase", 0.0, 0.0, 500.0, 47.5, MAT_INSULATION, 0.029)
        
        # 2. Concrete Top Layer (41.5mm - 47.5mm)
        # Height = 6.0 mm
        add_rect(self, "ConcreteLayer", 0.0, 41.5, 500.0, 6.0, MAT_CONCRETE, 1.15)
                       
        # 3. Wood Block (0-15mm x 36.5-41.5mm)
        # Height = 5.0 mm
        add_rect(self, "WoodBlock", 0.0, 36.5, 15.0, 5.0, MAT_WOOD, 0.12)
        
        # 4. Aluminum Head (0-15mm x 35.0-36.5mm)
        # Height = 1.5 mm
        add_rect(self, "AluminumHead", 0.0, 35.0, 15.0, 1.5, MAT_ALUMINUM, 230.0)
                       
        # 5. Aluminum Leg (0-1.5mm x 1.5-35.0mm)
        # Height = 33.5 mm
        add_rect(self, "AluminumLeg", 0.0, 1.5, 1.5, 33.5, MAT_ALUMINUM, 230.0)
                       
        # 6. Aluminum Plate (0-500mm x 0-1.5mm)
        # Height = 1.5 mm
        add_rect(self, "AluminumPlate", 0.0, 0.0, 500.0, 1.5, MAT_ALUMINUM, 230.0)
                       
        # Set Canvas
        self.set_canvas(0.0, 500.0, 0.0, 47.5, grid_mm=grid_mm)
        
    def get_refinement_zones(self) -> List[RefinementZone]:
        # Refine near the aluminum leg
        return [
            RefinementZone(
                x_min=0.0, x_max=20.0,
                y_min=0.0, y_max=47.5,
                target_dx=self.grid_mm,
                priority=1
            )
        ]
        
    def get_boundary_conditions(self) -> dict:
        return {
            'convective': {
                'bottom': {'T': 20.0, 'R': self.rsi},
                'top': {'T': 0.0, 'R': self.rse},
            },
            'adiabatic': ['left', 'right'],
            'surface_resistance': {
                MAT_AIR_INT: self.rsi,
                MAT_AIR_EXT: self.rse,
            }
        }


if __name__ == "__main__":
    # Quick test
    geom = ISOCase2Geometry(grid_mm=0.25)
    config = geom.get_canvas_config()
    print(f"Canvas: {config.width_mm} x {config.height_mm} mm")
    print(f"Shapes: {len(geom.shapes)}")
    for s in geom.shapes:
        print(f"  - {s.name}: {s.material_id}")

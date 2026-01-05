"""
ISO 10211 Test Case 1: 2D Half Column

Geometry specification from ISO 10211:
- Domain: 200mm (W) x 400mm (H)
- Material: Uniform k = 0.1 W/(m·K)
- Boundary conditions:
  - Top edge: T = 20°C (Dirichlet)
  - Right edge: T = 0°C (Dirichlet)
  - Bottom edge: T = 0°C (Dirichlet)
  - Left edge: Adiabatic (symmetry)
  
Validation point: T(150, 300) = 5.25°C ± 0.1K
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometry import SketchGeometry, CanvasConfig
from typing import List


# Material ID for the homogeneous solid
MAT_SOLID = 100


class ISOCase1Geometry(SketchGeometry):
    """
    ISO 10211 Test Case 1: 2D Half Column
    
    Refactored to use SketchGeometry (Points + Shapes).
    """
    
    def __init__(self, grid_mm: float = 1.0):
        super().__init__()
        self.grid_mm = grid_mm
        self.k_material = 0.1  # W/(m·K)
        
        # Define Points for 200x400 Rectangle
        self.add_point("A", 0.0, 0.0)
        self.add_point("B", 200.0, 0.0)
        self.add_point("C", 200.0, 400.0)
        self.add_point("D", 0.0, 400.0)
        
        # Define Shape
        self.add_shape(["A", "B", "C", "D"], 
                       material_id=MAT_SOLID, 
                       lambda_val=self.k_material,
                       name="SolidColumn")
        
        # Set Canvas
        self.set_canvas(0.0, 200.0, 0.0, 400.0, grid_mm=grid_mm)
        
    def get_boundary_conditions(self) -> dict:
        return {
            'dirichlet': {
                'top': 20.0,
                'right': 0.0,
                'bottom': 0.0,
            },
            'adiabatic': ['left'],
            'surface_resistance': {}
        }


if __name__ == "__main__":
    # Quick test
    geom = ISOCase1Geometry(grid_mm=1.0)
    config = geom.get_canvas_config()
    print(f"Canvas: {config.width_mm} x {config.height_mm} mm")
    print(f"Shapes: {len(geom.shapes)}")
    print(f"Critical X: {geom.get_critical_x_points()}")
    print(f"Critical Y: {geom.get_critical_y_points()}")

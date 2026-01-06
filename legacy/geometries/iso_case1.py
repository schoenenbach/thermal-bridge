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
ISO 10211 Test Case 1: 2D Half Column

Refactored to use Element Library (elements.py).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometry import SketchGeometry, CanvasConfig
from elements import add_rect
from typing import List


# Material ID for the homogeneous solid
MAT_SOLID = 100


class ISOCase1Geometry(SketchGeometry):
    """
    ISO 10211 Test Case 1: 2D Half Column
    """
    
    def __init__(self, grid_mm: float = 1.0):
        super().__init__()
        self.grid_mm = grid_mm
        self.k_material = 0.1  # W/(m·K)
        
        # Define Shape using Element Library
        add_rect(self, "SolidColumn", 0.0, 0.0, 200.0, 400.0, MAT_SOLID, self.k_material)
        
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

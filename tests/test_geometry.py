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

import pytest
import numpy as np
from backend.core.geometry import (
    CanvasConfig, 
    RectangularRegion, 
    PolygonShape, 
    Point, 
    build_material_grid,
    MaterialID
)

def test_canvas_config_dimensions():
    cfg = CanvasConfig(0, 100, 0, 50)
    assert cfg.width_mm == 100
    assert cfg.height_mm == 50

def test_rectangular_region_contains():
    # Rect from (10,10) to (20,20)
    rect = RectangularRegion(name="test", material_id=1, x_min=10, x_max=20, y_min=10, y_max=20)
    
    # Test points
    X = np.array([15, 5, 25])
    Y = np.array([15, 15, 15])
    
    mask = rect.contains(X, Y)
    assert mask[0] == True  # Inside
    assert mask[1] == False # Left
    assert mask[2] == False # Right

def test_polygon_shape_contains():
    # Triangle: (0,0), (10,0), (0,10)
    pts = [Point(0,0,'A'), Point(10,0,'B'), Point(0,10,'C')]
    poly = PolygonShape(name="test", material_id=1, points=pts)
    
    # Check simple points
    # (2,2) inside
    # (8,8) outside
    X = np.array([2, 8])
    Y = np.array([2, 8])
    
    mask = poly.contains(X, Y)
    assert mask[0] == True
    assert mask[1] == False

def test_build_material_grid():
    """Test material grid generation from backend.core.geometry."""
    # Mock geometry builder
    class MockBuilder:
        def __init__(self):
            # One region: 10x10 rect at bottom-left, Material 1
            self.rect = RectangularRegion(name="test", material_id=1, lambda_w_mk=0.5, x_min=0, x_max=10, y_min=0, y_max=10)
            
        def get_regions(self):
            return [self.rect]
            
        def get_material_conductivity(self, mid):
             return 0.5 if mid == 1 else 0.025 # Default air
        
        def get_canvas_config(self):
            # Used for default air material (?) 
            # Actually build_material_grid fills with AIR_EXT (0) or AIR_INT (1)?
            # It fills with AIR_EXT (0) by default usually.
            pass

    builder = MockBuilder()
    
    # 2x2 mesh grid points
    # (5,5) -> Inside rect
    # (15,15) -> Outside
    xc = np.array([5.0, 15.0])
    yc = np.array([5.0, 15.0])
    
    grid, cond = build_material_grid(builder, xc, yc)
    
    # Grid shape (ny, nx) -> (2, 2)
    assert grid.shape == (2, 2)
    
    # Check (0,0) which corresponds to y=5, x=5
    assert grid[0, 0] == 1
    assert cond[0, 0] == 0.5
    
    # Check (1,1) which corresponds to y=15, x=15
    # Should be AIR_EXT (0) with low conductivity
    assert grid[1, 1] == MaterialID.AIR_EXT

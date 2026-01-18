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
Tests for material averaging (anti-aliasing) functionality.
Tests compute_cell_coverage and build_material_grid_averaged functions.
"""

import pytest
import numpy as np
from backend.core.geometry import (
    RectangularRegion,
    PolygonShape,
    Point,
    GeometryBuilder,
    CanvasConfig,
    MaterialID,
    compute_cell_coverage,
    build_material_grid_averaged,
    build_material_grid,
)


class MockGeometryBuilder(GeometryBuilder):
    """Mock geometry builder for testing."""
    
    def __init__(self, regions, canvas=None):
        self._regions = regions
        self._canvas = canvas or CanvasConfig(0, 100, 0, 100)
    
    def get_canvas_config(self):
        return self._canvas
    
    def get_regions(self):
        return self._regions


# ============================================================================
# Tests for compute_cell_coverage
# ============================================================================

def test_coverage_fully_inside_rectangle():
    """Cell fully inside a rectangle should have 100% coverage."""
    rect = RectangularRegion(
        name="test_rect", 
        material_id=MaterialID.WALL,
        x_min=0, x_max=100, 
        y_min=0, y_max=100
    )
    
    # Cell at (50, 50) with size 10x10 - fully inside
    coverage = compute_cell_coverage(50, 50, 10, 10, [rect], n_samples=4)
    
    assert MaterialID.WALL in coverage
    assert coverage[MaterialID.WALL] == 1.0


def test_coverage_fully_outside():
    """Cell fully outside all regions should be 100% AIR_EXT."""
    rect = RectangularRegion(
        name="test_rect", 
        material_id=MaterialID.WALL,
        x_min=0, x_max=10, 
        y_min=0, y_max=10
    )
    
    # Cell at (50, 50) - far outside the rectangle
    coverage = compute_cell_coverage(50, 50, 10, 10, [rect], n_samples=4)
    
    assert MaterialID.AIR_EXT in coverage
    assert coverage[MaterialID.AIR_EXT] == 1.0
    assert MaterialID.WALL not in coverage


def test_coverage_on_horizontal_boundary():
    """Cell spanning horizontal material boundary should show partial coverage."""
    rect = RectangularRegion(
        name="test_rect", 
        material_id=MaterialID.WALL,
        x_min=0, x_max=100, 
        y_min=0, y_max=50  # Top edge at y=50
    )
    
    # Cell centered at y=50 (right on the boundary)
    coverage = compute_cell_coverage(50, 50, 10, 10, [rect], n_samples=4)
    
    # Should have partial coverage of both materials
    assert MaterialID.WALL in coverage
    assert MaterialID.AIR_EXT in coverage
    # Approximately 50% each (exact value depends on sub-sample positions)
    assert 0.25 <= coverage[MaterialID.WALL] <= 0.75


def test_coverage_diagonal_boundary():
    """Cell on a 45° diagonal boundary should have ~50% coverage."""
    # Triangle with diagonal from (0,0) to (100,100)
    # Points: (0,0), (100,0), (100,100)
    triangle = PolygonShape(
        name="diagonal",
        material_id=MaterialID.INSULATION,
        points=[
            Point(0, 0, 'A'),
            Point(100, 0, 'B'),
            Point(100, 100, 'C'),
        ]
    )
    
    # Cell at (50, 50) on the diagonal y=x
    coverage = compute_cell_coverage(50, 50, 10, 10, [triangle], n_samples=4)
    
    assert MaterialID.INSULATION in coverage
    assert MaterialID.AIR_EXT in coverage
    # Should be approximately 50% each for a 45° diagonal
    assert 0.25 <= coverage[MaterialID.INSULATION] <= 0.75


def test_coverage_higher_sample_count():
    """Higher sample count should give smoother coverage estimation."""
    triangle = PolygonShape(
        name="diagonal",
        material_id=MaterialID.INSULATION,
        points=[
            Point(0, 0, 'A'),
            Point(100, 0, 'B'),
            Point(100, 100, 'C'),
        ]
    )
    
    # With 8x8 samples, we should get a value closer to 50%
    coverage = compute_cell_coverage(50, 50, 10, 10, [triangle], n_samples=8)
    
    # With more samples, expect closer to 50%
    assert 0.4 <= coverage[MaterialID.INSULATION] <= 0.6


# ============================================================================
# Tests for build_material_grid_averaged
# ============================================================================

def test_averaged_grid_simple_rectangle():
    """Averaged grid should match standard grid for axis-aligned rectangles."""
    rect = RectangularRegion(
        name="wall",
        material_id=MaterialID.WALL,
        lambda_w_mk=0.81,
        x_min=0, x_max=50,
        y_min=0, y_max=50
    )
    
    builder = MockGeometryBuilder([rect])
    xc = np.array([25.0, 75.0])  # Inside and outside
    yc = np.array([25.0, 75.0])
    
    grid_map, cond, is_averaged = build_material_grid_averaged(builder, xc, yc)
    
    # Cell (0,0) = (x=25, y=25) fully inside rectangle
    assert grid_map[0, 0] == MaterialID.WALL
    assert cond[0, 0] == 0.81
    assert is_averaged[0, 0] == False
    
    # Cell (1,1) = (x=75, y=75) fully outside
    assert grid_map[1, 1] == MaterialID.AIR_EXT
    assert is_averaged[1, 1] == False


def test_averaged_grid_diagonal_boundary():
    """Cells on diagonal boundary should have averaged conductivity."""
    # Triangle: bottom-left half of a 100x100 square
    triangle = PolygonShape(
        name="insulation",
        material_id=MaterialID.INSULATION,
        lambda_w_mk=0.035,
        points=[
            Point(0, 0, 'A'),
            Point(100, 0, 'B'),
            Point(0, 100, 'C'),
        ]
    )
    
    builder = MockGeometryBuilder([triangle])
    
    # Create a 5x5 grid
    xc = np.linspace(10, 90, 5)
    yc = np.linspace(10, 90, 5)
    
    grid_map, cond, is_averaged = build_material_grid_averaged(builder, xc, yc)
    
    # Bottom-left corner should be insulation (fully inside)
    assert grid_map[0, 0] == MaterialID.INSULATION
    
    # Top-right corner should be AIR_EXT (fully outside)
    assert grid_map[-1, -1] == MaterialID.AIR_EXT
    
    # Diagonal cells should be averaged
    # At least one cell along the diagonal y = 100 - x should be averaged
    assert np.any(is_averaged)


def test_harmonic_mean_conductivity():
    """Verify harmonic mean is used for conductivity averaging."""
    # Two overlapping materials with known conductivities
    # If λ1=0.035 (insulation) and λ2=0.025 (air), 50/50 mix:
    # Harmonic mean = 2 / (1/0.035 + 1/0.025) = 2 / (28.57 + 40) = 0.0292
    
    rect1 = RectangularRegion(
        name="insulation",
        material_id=MaterialID.INSULATION,
        lambda_w_mk=0.035,
        x_min=0, x_max=50,
        y_min=0, y_max=100
    )
    
    builder = MockGeometryBuilder([rect1])
    
    # Cell right on the x=50 boundary
    xc = np.array([50.0])  # On boundary between insulation (x<50) and air (x>50)
    yc = np.array([50.0])
    
    _, cond, is_averaged = build_material_grid_averaged(builder, xc, yc, n_samples=4)
    
    # Should be averaged
    assert is_averaged[0, 0] == True
    
    # Harmonic mean of 0.035 and 0.025 with 50/50 coverage
    # 1/λ_eff = 0.5/0.035 + 0.5/0.025 = 14.286 + 20 = 34.286
    # λ_eff = 1/34.286 = 0.0292
    # Due to sub-sampling positions, coverage may not be exactly 50/50
    assert 0.025 < cond[0, 0] < 0.035  # Should be between the two values


def test_backward_compatibility():
    """Verify build_material_grid still works unchanged."""
    rect = RectangularRegion(
        name="wall",
        material_id=MaterialID.WALL,
        lambda_w_mk=0.5,
        x_min=0, x_max=10,
        y_min=0, y_max=10
    )
    
    builder = MockGeometryBuilder([rect])
    xc = np.array([5.0, 15.0])
    yc = np.array([5.0, 15.0])
    
    # Original function should still work
    grid, cond = build_material_grid(builder, xc, yc)
    
    assert grid.shape == (2, 2)
    assert grid[0, 0] == MaterialID.WALL
    assert cond[0, 0] == 0.5


def test_averaged_vs_discrete_comparison():
    """Compare discrete vs averaged for a diagonal shape."""
    # Triangle with 45° diagonal
    triangle = PolygonShape(
        name="wall",
        material_id=MaterialID.WALL,
        lambda_w_mk=0.81,
        points=[
            Point(0, 0, 'A'),
            Point(100, 0, 'B'),
            Point(100, 100, 'C'),
        ]
    )
    
    builder = MockGeometryBuilder([triangle])
    xc = np.linspace(5, 95, 10)
    yc = np.linspace(5, 95, 10)
    
    # Both methods should return valid grids
    grid_discrete, cond_discrete = build_material_grid(builder, xc, yc)
    grid_avg, cond_avg, is_avg = build_material_grid_averaged(builder, xc, yc)
    
    # Same shape
    assert grid_discrete.shape == grid_avg.shape
    assert cond_discrete.shape == cond_avg.shape
    
    # Averaged should have some boundary cells marked
    assert np.sum(is_avg) > 0
    
    # Conductivity values should differ at boundaries
    # but be the same in interior cells
    boundary_cells = is_avg
    interior_cells = ~is_avg
    
    # Interior cells should have same conductivity
    np.testing.assert_array_equal(
        cond_discrete[interior_cells], 
        cond_avg[interior_cells]
    )

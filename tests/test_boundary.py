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
Unit tests for the boundary condition assembly module.
"""

import pytest
import numpy as np
from numpy.testing import assert_array_almost_equal, assert_array_equal

from backend.core.boundary import (
    get_interface_mask,
    calculate_surface_conductance,
    apply_film_coefficients,
    pad_domain_for_convective_bc,
    apply_convective_boundary_conductances,
    BoundaryConditionAssembler,
)
from backend.core.geometry import MaterialID


class TestInterfaceDetection:
    """Tests for interface mask detection between air and solid materials."""
    
    def test_get_interface_mask_left_air(self):
        """Test detection of air-to-solid interfaces (air on left)."""
        # 3x3 grid: left column is air, rest is solid
        grid_map = np.array([
            [MaterialID.AIR_INT, MaterialID.WALL, MaterialID.WALL],
            [MaterialID.AIR_INT, MaterialID.WALL, MaterialID.WALL],
            [MaterialID.AIR_INT, MaterialID.WALL, MaterialID.WALL],
        ])
        air_mask = (grid_map == MaterialID.AIR_INT)
        
        y_idx, x_idx = get_interface_mask(grid_map, air_mask, 'left')
        
        # Should find 3 interfaces at column 0 (links to column 1)
        assert len(y_idx) == 3
        assert_array_equal(x_idx, [0, 0, 0])
        assert_array_equal(y_idx, [0, 1, 2])
    
    def test_get_interface_mask_right_air(self):
        """Test detection of solid-to-air interfaces (air on right)."""
        grid_map = np.array([
            [MaterialID.WALL, MaterialID.WALL, MaterialID.AIR_EXT],
            [MaterialID.WALL, MaterialID.WALL, MaterialID.AIR_EXT],
        ])
        air_mask = (grid_map == MaterialID.AIR_EXT)
        
        y_idx, x_idx = get_interface_mask(grid_map, air_mask, 'right')
        
        # Should find 2 interfaces at column 1 (links from column 1 to 2)
        assert len(y_idx) == 2
        assert_array_equal(x_idx, [1, 1])
    
    def test_get_interface_mask_vertical(self):
        """Test detection of vertical interfaces (up/down)."""
        # 3x3 grid: bottom row is air, rest is solid
        grid_map = np.array([
            [MaterialID.AIR_INT, MaterialID.AIR_INT, MaterialID.AIR_INT],
            [MaterialID.WALL, MaterialID.WALL, MaterialID.WALL],
            [MaterialID.WALL, MaterialID.WALL, MaterialID.WALL],
        ])
        air_mask = (grid_map == MaterialID.AIR_INT)
        
        y_idx, x_idx = get_interface_mask(grid_map, air_mask, 'down')
        
        # Should find 3 interfaces at row 0 (links to row 1)
        assert len(y_idx) == 3
        assert_array_equal(y_idx, [0, 0, 0])
        assert_array_equal(x_idx, [0, 1, 2])


class TestSurfaceConductance:
    """Tests for surface conductance calculation."""
    
    def test_calculate_surface_conductance_simple(self):
        """Test conductance formula with known values."""
        # k=1.0 W/mK, d=0.1m, R=0.13 m²K/W, Area=0.01 m²
        k_solid = np.array([1.0])
        d_solid = np.array([0.1])
        R_surface = 0.13
        area = np.array([0.01])
        
        G = calculate_surface_conductance(k_solid, d_solid, R_surface, area)
        
        # R_half = 0.1/(2*1.0) = 0.05
        # R_total = 0.05 + 0.13 = 0.18
        # G = 0.01 / 0.18 ≈ 0.0556
        expected = 0.01 / 0.18
        assert_array_almost_equal(G, [expected], decimal=6)
    
    def test_calculate_surface_conductance_array(self):
        """Test conductance with array inputs."""
        k_solid = np.array([1.0, 2.0, 0.5])
        d_solid = np.array([0.1, 0.1, 0.2])
        R_surface = 0.13
        area = np.array([0.01, 0.02, 0.01])
        
        G = calculate_surface_conductance(k_solid, d_solid, R_surface, area)
        
        # Manual calculation for each
        R_half = d_solid / (2 * k_solid)  # [0.05, 0.025, 0.2]
        R_total = R_half + R_surface      # [0.18, 0.155, 0.33]
        expected = area / R_total
        
        assert_array_almost_equal(G, expected, decimal=6)


class TestDomainPadding:
    """Tests for convective BC domain padding."""
    
    def test_pad_domain_bottom_top(self):
        """Test padding with top and bottom convective BCs."""
        cond = np.ones((3, 4)) * 1.5
        grid_map = np.full((3, 4), MaterialID.WALL, dtype=int)
        dx_array = np.array([10.0, 10.0, 10.0, 10.0])
        dy_array = np.array([5.0, 10.0, 5.0])
        
        conv_bcs = {
            'bottom': {'T': 20.0, 'R': 0.11},
            'top': {'T': 0.0, 'R': 0.06},
        }
        
        result = pad_domain_for_convective_bc(
            cond, grid_map, dx_array, dy_array, conv_bcs
        )
        cond_p, grid_p, dx_p, dy_p, y_off, x_off = result
        
        # Check dimensions: should add 1 row top and bottom
        assert cond_p.shape == (5, 4)
        assert grid_p.shape == (5, 4)
        assert len(dy_p) == 5
        assert len(dx_p) == 4  # No left/right padding
        
        # Check offsets
        assert y_off == 1  # Bottom padding
        assert x_off == 0  # No left padding
        
        # Check material assignment
        assert grid_p[0, 0] == MaterialID.AIR_INT  # Bottom (warm, T=20)
        assert grid_p[-1, 0] == MaterialID.AIR_EXT  # Top (cold, T=0)
        
        # Check original data preserved
        assert np.all(cond_p[1:4, :] == 1.5)
    
    def test_pad_domain_all_sides(self):
        """Test padding on all four sides."""
        cond = np.ones((2, 2))
        grid_map = np.full((2, 2), MaterialID.WALL, dtype=int)
        dx_array = np.array([10.0, 10.0])
        dy_array = np.array([10.0, 10.0])
        
        conv_bcs = {
            'bottom': {'T': 20.0, 'R': 0.13},
            'top': {'T': 0.0, 'R': 0.04},
            'left': {'T': 20.0, 'R': 0.13},
            'right': {'T': -5.0, 'R': 0.04},
        }
        
        result = pad_domain_for_convective_bc(
            cond, grid_map, dx_array, dy_array, conv_bcs
        )
        cond_p, grid_p, dx_p, dy_p, y_off, x_off = result
        
        assert cond_p.shape == (4, 4)
        assert y_off == 1
        assert x_off == 1
        assert len(dx_p) == 4
        assert len(dy_p) == 4


class TestBoundaryConditionAssembler:
    """Tests for the high-level BoundaryConditionAssembler class."""
    
    def test_assembler_initialization(self):
        """Test assembler can be initialized."""
        grid_map = np.full((5, 5), MaterialID.WALL, dtype=int)
        cond = np.ones((5, 5))
        dx = np.full(5, 10.0)
        dy = np.full(5, 10.0)
        
        assembler = BoundaryConditionAssembler(grid_map, cond, dx, dy)
        
        assert assembler.grid_map.shape == (5, 5)
        assert assembler.surface_resistances == {}
    
    def test_assembler_method_chaining(self):
        """Test fluent interface for setting resistances."""
        grid_map = np.full((5, 5), MaterialID.WALL, dtype=int)
        cond = np.ones((5, 5))
        dx = np.full(5, 10.0)
        dy = np.full(5, 10.0)
        
        assembler = BoundaryConditionAssembler(grid_map, cond, dx, dy)
        result = assembler.set_surface_resistances({MaterialID.AIR_INT: 0.13})
        
        assert result is assembler  # Method chaining
        assert assembler.surface_resistances[MaterialID.AIR_INT] == 0.13
    
    def test_detect_interior_boundaries(self):
        """Test detection of interior boundary cells."""
        # Grid with interior air on left
        grid_map = np.array([
            [MaterialID.AIR_INT, MaterialID.WALL, MaterialID.WALL],
            [MaterialID.AIR_INT, MaterialID.WALL, MaterialID.WALL],
            [MaterialID.AIR_INT, MaterialID.WALL, MaterialID.WALL],
        ])
        cond = np.ones((3, 3))
        dx = np.full(3, 10.0)
        dy = np.full(3, 10.0)
        
        assembler = BoundaryConditionAssembler(grid_map, cond, dx, dy)
        boundary_mask = assembler.detect_interior_boundaries()
        
        # Column 1 should be marked as boundary (adjacent to air)
        expected = np.array([
            [False, True, False],
            [False, True, False],
            [False, True, False],
        ])
        assert_array_equal(boundary_mask, expected)
    
    def test_detect_exterior_boundaries(self):
        """Test detection of exterior boundary cells."""
        # Grid with exterior air on right
        grid_map = np.array([
            [MaterialID.WALL, MaterialID.WALL, MaterialID.AIR_EXT],
            [MaterialID.WALL, MaterialID.WALL, MaterialID.AIR_EXT],
        ])
        cond = np.ones((2, 3))
        dx = np.full(3, 10.0)
        dy = np.full(2, 10.0)
        
        assembler = BoundaryConditionAssembler(grid_map, cond, dx, dy)
        boundary_mask = assembler.detect_exterior_boundaries()
        
        # Column 1 should be marked as exterior boundary
        expected = np.array([
            [False, True, False],
            [False, True, False],
        ])
        assert_array_equal(boundary_mask, expected)


class TestFilmCoefficientApplication:
    """Tests for apply_film_coefficients function."""
    
    def test_apply_film_coefficients_modifies_gh(self):
        """Test that Gh is modified at air-solid interfaces."""
        # Simple 1x3 grid: Air | Solid | Solid
        grid_map = np.array([[MaterialID.AIR_INT, MaterialID.WALL, MaterialID.WALL]])
        cond = np.array([[0.025, 0.81, 0.81]])
        dx_array = np.array([10.0, 10.0, 10.0])  # 10mm cells
        dy_array = np.array([10.0])
        
        # Initial conductances (will be overwritten)
        Gh = np.ones((1, 3)) * 0.1
        Gv = np.ones((1, 3)) * 0.1
        
        surface_resistances = {MaterialID.AIR_INT: 0.13}
        
        apply_film_coefficients(
            Gh, Gv, grid_map, cond, dx_array, dy_array, surface_resistances
        )
        
        # Gh[0,0] should now be calculated using surface conductance formula
        # k=0.81, dx=0.01m, R=0.13, dy=0.01m
        # R_half = 0.01 / (2*0.81) = 0.00617
        # R_total = 0.00617 + 0.13 = 0.1362
        # G = 0.01 / 0.1362 ≈ 0.0734
        expected_G = 0.01 / (0.01/(2*0.81) + 0.13)
        
        assert abs(Gh[0, 0] - expected_G) < 0.001

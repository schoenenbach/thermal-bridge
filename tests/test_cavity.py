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
Tests for ISO 10077-2 Air Cavity Module

Tests cavity detection, λ_eq calculation, and iterative solver.
"""

import pytest
import numpy as np

from backend.core.cavity import (
    CavityRegion,
    detect_cavities,
    calculate_lambda_eq,
    get_cavity_surface_temperatures,
    update_cavity_conductivities,
    _flood_fill,
    _create_cavity_region
)
from backend.core.geometry import MaterialID


class TestFloodFill:
    """Tests for flood-fill cavity detection."""
    
    def test_single_rectangular_cavity(self):
        """Detect a single rectangular cavity."""
        grid = np.zeros((10, 10), dtype=int)
        grid[3:6, 4:7] = MaterialID.CAVITY  # 3x3 cavity
        
        dx_m = 0.01  # 10mm
        dy_m = 0.01
        
        cavities = detect_cavities(grid, dx_m, dy_m, MaterialID.CAVITY)
        
        assert len(cavities) == 1
        assert len(cavities[0].cells) == 9
        assert cavities[0].d == 0.03  # 3 cells * 10mm
        assert cavities[0].b == 0.03
    
    def test_two_separate_cavities(self):
        """Detect two non-adjacent cavities."""
        grid = np.zeros((20, 20), dtype=int)
        grid[2:4, 2:4] = MaterialID.CAVITY  # Cavity 1 (2x2)
        grid[10:14, 10:14] = MaterialID.CAVITY  # Cavity 2 (4x4)
        
        cavities = detect_cavities(grid, 0.01, 0.01, MaterialID.CAVITY)
        
        assert len(cavities) == 2
        cell_counts = sorted([len(c.cells) for c in cavities])
        assert cell_counts == [4, 16]
    
    def test_L_shaped_cavity(self):
        """L-shaped cavity detected as single region."""
        grid = np.zeros((10, 10), dtype=int)
        grid[2:5, 2:4] = MaterialID.CAVITY  # Vertical part
        grid[4:5, 4:7] = MaterialID.CAVITY  # Horizontal part
        
        cavities = detect_cavities(grid, 0.01, 0.01, MaterialID.CAVITY)
        
        assert len(cavities) == 1
        assert len(cavities[0].cells) == 6 + 3  # 3x2 + 1x3
    
    def test_no_cavities(self):
        """No cavities in grid returns empty list."""
        grid = np.full((10, 10), MaterialID.WALL, dtype=int)
        
        cavities = detect_cavities(grid, 0.01, 0.01, MaterialID.CAVITY)
        
        assert len(cavities) == 0


class TestCavityDimensions:
    """Tests for cavity geometry calculation."""
    
    def test_horizontal_cavity(self):
        """Thin horizontal cavity (b > d)."""
        grid = np.zeros((20, 10), dtype=int)
        grid[5:15, 4:6] = MaterialID.CAVITY  # 10 high x 2 wide
        
        cavities = detect_cavities(grid, 0.02, 0.02, MaterialID.CAVITY)
        
        assert len(cavities) == 1
        c = cavities[0]
        assert c.d == pytest.approx(0.04)  # 2 cells * 20mm = 40mm
        assert c.b == pytest.approx(0.20)  # 10 cells * 20mm = 200mm
        assert c.aspect_ratio == pytest.approx(5.0)
    
    def test_vertical_slot_cavity(self):
        """Thin vertical slot (d > b)."""
        grid = np.zeros((5, 20), dtype=int)
        grid[1:3, 5:15] = MaterialID.CAVITY  # 2 high x 10 wide
        
        cavities = detect_cavities(grid, 0.01, 0.01, MaterialID.CAVITY)
        
        c = cavities[0]
        assert c.d == pytest.approx(0.10)  # width
        assert c.b == pytest.approx(0.02)  # height
        assert c.aspect_ratio == pytest.approx(0.2)


class TestLambdaEqCalculation:
    """Tests for ISO 10077-2 λ_eq formulas."""
    
    def test_still_air_limit(self):
        """Very thin cavity approaches still air conductivity."""
        # 5mm gap, small temperature difference
        lam = calculate_lambda_eq(d=0.005, T_hot=20, T_cold=18)
        
        # Should be close to λ_air * d * h_total
        # For small d, h_a ≈ 0.025/d = 5, h_r ≈ 5
        # λ_eq ≈ 0.005 * 10 = 0.05
        assert 0.03 < lam < 0.15
    
    def test_lambda_increases_with_thickness(self):
        """λ_eq increases with cavity thickness."""
        lam_5mm = calculate_lambda_eq(d=0.005, T_hot=20, T_cold=0)
        lam_20mm = calculate_lambda_eq(d=0.020, T_hot=20, T_cold=0)
        lam_50mm = calculate_lambda_eq(d=0.050, T_hot=20, T_cold=0)
        
        assert lam_5mm < lam_20mm < lam_50mm
    
    def test_lambda_increases_with_temperature_difference(self):
        """λ_eq increases with larger ΔT (more convection) for thicker cavities."""
        # For thicker cavities, convection becomes significant with higher ΔT
        lam_small = calculate_lambda_eq(d=0.05, T_hot=20, T_cold=18)
        lam_large = calculate_lambda_eq(d=0.05, T_hot=20, T_cold=0)
        
        assert lam_small < lam_large
    
    def test_low_emissivity_reduces_radiation(self):
        """Low emissivity (e.g., aluminum) reduces h_r."""
        lam_normal = calculate_lambda_eq(d=0.02, T_hot=20, T_cold=0, eps_1=0.9, eps_2=0.9)
        lam_low_e = calculate_lambda_eq(d=0.02, T_hot=20, T_cold=0, eps_1=0.05, eps_2=0.9)
        
        assert lam_low_e < lam_normal
    
    def test_symmetric_temperatures(self):
        """Zero temperature difference gives minimal convection."""
        lam = calculate_lambda_eq(d=0.02, T_hot=15, T_cold=15)
        
        # Only radiation and conduction contribute
        # Should still be reasonable (0.15-0.3 W/mK)
        assert 0.1 < lam < 0.4
    
    def test_typical_window_cavity(self):
        """Typical 12mm window cavity gives reasonable λ_eq."""
        # ISO 10077-2 / EN 673 values for 12mm vertical cavity
        # With high emissivity surfaces, expect ~0.05-0.15 W/mK
        lam = calculate_lambda_eq(d=0.012, T_hot=15, T_cold=5, eps_1=0.9, eps_2=0.9)
        
        # For thin 12mm gap: h_a ≈ max(0.025/0.012, 0.73*10^0.25) = max(2.08, 1.30) = 2.08
        # h_r ≈ 4 * 5.67e-8 * 283^3 * 0.82 ≈ 4.2 W/m²K
        # λ_eq ≈ 0.012 * (2.08 + 4.2) ≈ 0.075 W/mK
        assert 0.05 < lam < 0.15


class TestSurfaceTemperatures:
    """Tests for extracting cavity surface temperatures."""
    
    def test_simple_gradient(self):
        """Extract temperatures from linear gradient."""
        temp = np.linspace(20, 0, 10).reshape(1, 10).repeat(10, axis=0)
        
        cavity = CavityRegion(
            cells=[(r, c) for r in range(3, 7) for c in range(4, 6)],
            d=0.02,
            b=0.04,
            aspect_ratio=2.0,
            bounds=(3, 6, 4, 5)
        )
        
        T_hot, T_cold = get_cavity_surface_temperatures(temp, cavity)
        
        # Hot side at column 3, cold side at column 6
        assert T_hot > T_cold
        assert T_hot > 10
        assert T_cold < 15


class TestIterativeUpdate:
    """Tests for iterative λ_eq update."""
    
    def test_conductivity_update(self):
        """Conductivities are updated in-place."""
        cond = np.ones((10, 10)) * 0.5
        cond[3:6, 4:7] = 0.25  # Initial cavity λ
        
        grid = np.zeros((10, 10), dtype=int)
        grid[3:6, 4:7] = MaterialID.CAVITY
        
        # Create temperature field with gradient
        temp = np.tile(np.linspace(20, 0, 10), (10, 1))
        
        cavities = detect_cavities(grid, 0.01, 0.01, MaterialID.CAVITY)
        initial_lambda = cond[4, 5]
        
        cond, lambdas = update_cavity_conductivities(cond, cavities, temp)
        
        # Cavity cells should have updated λ
        new_lambda = cond[4, 5]
        assert new_lambda != initial_lambda
        assert len(lambdas) == 1
        assert lambdas[0] == new_lambda


class TestMaterialRegistry:
    """Tests for emissivity in material registry."""
    
    def test_emissivity_loaded(self):
        """Emissivity values are loaded from JSON."""
        from library.material_registry import MaterialRegistry
        
        reg = MaterialRegistry.get()
        
        # Aluminum should have low emissivity
        eps_al = reg.get_emissivity("aluminum_generic")
        assert eps_al < 0.1
        
        # Masonry should have high emissivity  
        eps_wall = reg.get_emissivity("wall_generic")
        assert eps_wall > 0.8
    
    def test_default_emissivity(self):
        """Unknown materials get default emissivity."""
        from library.material_registry import MaterialRegistry
        
        reg = MaterialRegistry.get()
        eps = reg.get_emissivity("nonexistent_material", default=0.85)
        assert eps == 0.85


class TestIterativeSolver:
    """Integration tests for iterative cavity solver."""
    
    @pytest.mark.slow
    def test_cavity_solver_convergence(self):
        """Iterative solver converges for simple case."""
        from backend.core.solver import solve_with_cavity_iteration
        
        # Create simple domain: wall with embedded cavity
        rows, cols = 20, 30
        dx_m = 0.01  # 10mm
        dy_m = 0.01
        
        grid = np.full((rows, cols), MaterialID.WALL, dtype=int)
        grid[:, 0:2] = MaterialID.AIR_INT
        grid[:, -2:] = MaterialID.AIR_EXT
        grid[8:12, 12:18] = MaterialID.CAVITY  # 4x6 cavity in center
        
        cond = np.full((rows, cols), 0.81)  # Wall
        cond[:, 0:2] = 0.025  # Air
        cond[:, -2:] = 0.025
        cond[8:12, 12:18] = 0.25  # Initial cavity λ
        
        fixed_mask = np.zeros((rows, cols), dtype=bool)
        fixed_values = np.zeros((rows, cols))
        fixed_mask[:, 0] = True
        fixed_values[:, 0] = 20.0
        fixed_mask[:, -1] = True
        fixed_values[:, -1] = -5.0
        
        temp, history = solve_with_cavity_iteration(
            cond, grid, dx_m, dy_m, fixed_mask, fixed_values,
            max_cavity_iterations=10,
            verbose=False
        )
        
        # Should converge in a few iterations
        assert len(history) >= 1
        assert len(history) <= 10
        
        # Temperature should be reasonable
        assert np.min(temp) >= -5.0
        assert np.max(temp) <= 20.0

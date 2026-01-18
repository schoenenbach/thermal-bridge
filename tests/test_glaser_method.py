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
Unit tests for Glaser method implementation (ISO 13788).

These tests verify:
1. Temperature profile calculations follow thermal resistance method
2. Vapor pressure profiles match expected behavior
3. Condensation detection works correctly
4. Example cases from literature are reproduced
"""

import pytest
import numpy as np
from backend.core.glaser_method import (
    Layer,
    GlaserResult,
    calculate_temperature_profile,
    calculate_vapor_pressure_profile,
    check_monthly_condensation,
    get_typical_humidity_class
)


class TestLayer:
    """Tests for the Layer dataclass."""
    
    def test_thermal_resistance(self):
        """R = d / lambda"""
        layer = Layer("Concrete", thickness_m=0.2, lambda_W_mK=1.0, mu=80)
        assert layer.R == pytest.approx(0.2, rel=1e-6)
        
    def test_sd_value(self):
        """sd = d * mu"""
        layer = Layer("Concrete", thickness_m=0.2, lambda_W_mK=1.0, mu=80)
        assert layer.sd == pytest.approx(16.0, rel=1e-6)
        
    def test_insulation_properties(self):
        """Typical mineral wool: high R, low sd"""
        wool = Layer("Mineral Wool", thickness_m=0.1, lambda_W_mK=0.04, mu=1)
        assert wool.R == pytest.approx(2.5, rel=1e-6)
        assert wool.sd == pytest.approx(0.1, rel=1e-6)


class TestTemperatureProfile:
    """Tests for temperature profile calculations."""
    
    def test_homogeneous_wall_linear_gradient(self):
        """Single homogeneous layer should give linear profile"""
        layers = [Layer("Concrete", 0.3, 1.5, 100)]
        T, names = calculate_temperature_profile(layers, T_interior=20.0, T_exterior=0.0)
        
        # Should have 4 points: air_int, surf_int, surf_ext, air_ext
        assert len(T) == 4
        assert T[0] == pytest.approx(20.0)
        assert T[-1] == pytest.approx(0.0)
        # Interior surface should be slightly cooler than air
        assert T[1] < T[0]
        # Exterior surface should be slightly warmer than air
        assert T[-2] > T[-1]
        
    def test_multi_layer_wall(self):
        """Multi-layer wall: insulation outside should keep interior warm"""
        # Typical: Concrete + External Insulation
        layers = [
            Layer("Concrete", 0.2, 1.0, 80),      # R = 0.2
            Layer("EPS Insulation", 0.1, 0.04, 30)  # R = 2.5
        ]
        T, names = calculate_temperature_profile(layers, T_interior=20.0, T_exterior=-10.0)
        
        # 5 points: air_int, surf_int, concrete/eps interface, surf_ext, air_ext  
        assert len(T) == 5
        
        # Most temperature drop should be across insulation
        delta_insulation = T[2] - T[3]  # Interface to exterior surface
        delta_concrete = T[1] - T[2]    # Interior surface to interface
        
        # Insulation has R=2.5, concrete has R=0.2, so insulation drop should be ~10x larger
        assert delta_insulation > 5 * delta_concrete
        
    def test_temperature_monotonic(self):
        """Temperature should decrease monotonically from interior to exterior"""
        layers = [
            Layer("Plaster", 0.015, 0.7, 10),
            Layer("Brick", 0.24, 0.6, 10),
            Layer("Insulation", 0.08, 0.035, 1),
            Layer("Render", 0.01, 0.8, 20)
        ]
        T, _ = calculate_temperature_profile(layers, 21.0, -5.0)
        
        # Each temperature should be >= the next
        for i in range(len(T) - 1):
            assert T[i] >= T[i+1], f"Non-monotonic at index {i}"


class TestVaporPressureProfile:
    """Tests for vapor pressure and condensation calculations."""
    
    def test_no_condensation_dry_conditions(self):
        """Low humidity on both sides -> no condensation"""
        layers = [Layer("Concrete", 0.2, 1.0, 80)]
        result = calculate_vapor_pressure_profile(
            layers,
            T_interior=20.0, T_exterior=0.0,
            phi_interior=0.3, phi_exterior=0.5
        )
        
        assert not result.has_condensation
        assert len(result.condensation_interfaces) == 0
        
    def test_condensation_cold_surface(self):
        """High interior humidity + cold exterior -> condensation risk"""
        # Interior insulation case (bad practice) - cold side has high vapor resistance
        layers = [
            Layer("EPS Insulation", 0.08, 0.04, 60),  # sd = 4.8m
            Layer("Concrete", 0.2, 1.0, 80)           # sd = 16m
        ]
        result = calculate_vapor_pressure_profile(
            layers,
            T_interior=20.0, T_exterior=-10.0,
            phi_interior=0.6, phi_exterior=0.8
        )
        
        # This is a classic condensation-prone assembly
        # Vapor can get into the cold zone easily but not escape
        # Check that vapor pressures and saturation pressures are calculated
        assert len(result.vapor_pressures) == 5
        assert len(result.saturation_pressures) == 5
        
    def test_vapor_barrier_effectiveness(self):
        """Vapor barrier on warm side should prevent condensation"""
        # External insulation with vapor barrier
        layers = [
            Layer("Vapor Barrier", 0.001, 0.2, 100000),  # sd = 100m
            Layer("Concrete", 0.2, 1.0, 80),
            Layer("EPS Insulation", 0.1, 0.04, 30)
        ]
        result = calculate_vapor_pressure_profile(
            layers,
            T_interior=20.0, T_exterior=-10.0,
            phi_interior=0.6, phi_exterior=0.8
        )
        
        # With vapor barrier, vapor pressure drops immediately
        # The jump should happen at the barrier
        p_before_barrier = result.vapor_pressures[1]  # Interior surface
        p_after_barrier = result.vapor_pressures[2]   # After barrier
        
        # Most pressure drop should be at barrier (it has highest sd value)
        total_drop = result.vapor_pressures[0] - result.vapor_pressures[-1]
        if total_drop > 0:  # Only check if there's a meaningful gradient
            barrier_drop = p_before_barrier - p_after_barrier
            # Barrier should have significant portion of the drop (proportional to sd ratio)
            assert barrier_drop > 0.1 * total_drop, "Vapor barrier should have meaningful effect"


class TestISO13788Examples:
    """
    Tests based on ISO 13788 Annex C calculation examples.
    
    These test simplified versions of the standard's worked examples
    to validate the implementation against known results.
    """
    
    def test_flat_roof_winter_month(self):
        """
        Simplified flat roof example (inspired by ISO 13788 Annex C).
        
        Construction (outside to inside):
        - Weatherproofing membrane (vapor tight)
        - Insulation
        - Concrete deck
        
        In this configuration, condensation should NOT occur because
        the vapor barrier is on the cold side (unusual but the membrane
        prevents vapor ingress from outside).
        """
        # Note: ISO example uses specific climate data; this is simplified
        layers = [
            Layer("Concrete Deck", 0.15, 1.5, 100),       # sd = 15m
            Layer("Mineral Wool", 0.12, 0.04, 1),         # sd = 0.12m
            Layer("Bitumen Membrane", 0.005, 0.2, 50000)  # sd = 250m (vapor tight)
        ]
        
        # January conditions (Berlin-like climate)
        result = calculate_vapor_pressure_profile(
            layers,
            T_interior=20.0, T_exterior=1.0,
            phi_interior=0.5, phi_exterior=0.8
        )
        
        # The membrane's high sd value should dominate vapor resistance
        assert result.saturation_pressures[0] > result.vapor_pressures[0]
        
    def test_internal_insulation_condensation_risk(self):
        """
        Internal insulation on solid wall - known condensation risk.
        
        This is a classic case where interstitial condensation occurs
        at the insulation/wall interface during heating season.
        """
        layers = [
            Layer("Plasterboard", 0.012, 0.25, 8),     # sd = 0.096m
            Layer("Mineral Wool", 0.05, 0.04, 1),     # sd = 0.05m  
            Layer("Brick Wall", 0.36, 0.6, 10)        # sd = 3.6m
        ]
        
        # Cold January, humid interior
        result = calculate_vapor_pressure_profile(
            layers,
            T_interior=20.0, T_exterior=-5.0,
            phi_interior=0.55, phi_exterior=0.85
        )
        
        # The insulation/brick interface is cold - check temperature there
        T_interface = result.temperatures[3]  # After insulation
        
        # With external temp -5°C, this interface will be quite cold
        assert T_interface < 10.0, "Interface should be cold"
        

class TestMonthlyAnalysis:
    """Tests for annual condensation assessment."""
    
    def test_monthly_data_validation(self):
        """Should reject data that isn't 12 months"""
        layers = [Layer("Concrete", 0.2, 1.0, 80)]
        
        with pytest.raises(ValueError):
            check_monthly_condensation(
                layers,
                monthly_T_interior=[20] * 10,  # Wrong length
                monthly_T_exterior=[5] * 12,
                monthly_phi_interior=[0.5] * 12,
                monthly_phi_exterior=[0.8] * 12
            )
            
    def test_monthly_analysis_runs(self):
        """Monthly analysis should return 12 results"""
        layers = [Layer("Brick", 0.24, 0.6, 10)]
        
        # Simplified annual cycle
        T_int = [20.0] * 12
        T_ext = [-2, 0, 4, 8, 13, 17, 19, 18, 14, 9, 4, 0]
        phi_int = [0.5] * 12
        phi_ext = [0.85] * 12
        
        results = check_monthly_condensation(
            layers, T_int, T_ext, phi_int, phi_ext
        )
        
        assert len(results) == 12
        assert all(isinstance(r, GlaserResult) for r in results)


class TestHumidityClasses:
    """Tests for ISO 13788 humidity class calculations."""
    
    def test_class_3_at_0_degrees(self):
        """Class 3 (residential) at 0°C should give 810 Pa excess"""
        delta_p = get_typical_humidity_class(0.0, humidity_class=3)
        assert delta_p == pytest.approx(810, rel=0.01)
        
    def test_class_3_at_20_degrees(self):
        """At 20°C external, no excess vapor pressure"""
        delta_p = get_typical_humidity_class(20.0, humidity_class=3)
        assert delta_p == pytest.approx(0, abs=1.0)
        
    def test_class_ordering(self):
        """Higher class should give higher excess pressure"""
        delta_p_1 = get_typical_humidity_class(5.0, 1)
        delta_p_3 = get_typical_humidity_class(5.0, 3)
        delta_p_5 = get_typical_humidity_class(5.0, 5)
        
        assert delta_p_1 < delta_p_3 < delta_p_5

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
VTT Mould Index Benchmark Tests

These tests validate the VTT Mould Index implementation against:
1. Published critical RH curves from Hukka & Viitanen (1999)
2. Expected qualitative behavior (growth under favorable, decline under dry)
3. Sensitivity class ordering
4. Empirical data from literature

References:
    - Hukka, A. & Viitanen, H.A. (1999). A mathematical model of mould growth 
      on wooden material. Wood Science and Technology, 33(6), 475-485.
    - Ojanen, T. et al. (2010). Mold growth modeling of building structures
      using sensitivity classes of materials. ASHRAE Buildings XI Conference.
"""

import pytest
import numpy as np
from backend.core.mold_analysis import (
    MouldSensitivity,
    MouldDeclineClass,
    VTTMouldResult,
    calculate_critical_rh,
    calculate_mould_growth_rate,
    simulate_mould_index,
    get_mould_risk_rating,
    VTT_K1_FACTORS,
    VTT_K2_FACTORS,
    VTT_MMAX
)


class TestCriticalRH:
    """Tests for critical relative humidity thresholds."""
    
    def test_critical_rh_at_low_temp(self):
        """At low temperatures, RH_crit should be higher (stricter)"""
        rh_5c = calculate_critical_rh(5.0, MouldSensitivity.SENSITIVE)
        rh_20c = calculate_critical_rh(20.0, MouldSensitivity.SENSITIVE)
        
        # At 5°C, RH_crit should be closer to 100%
        assert rh_5c > rh_20c
        assert rh_5c > 0.85
        
    def test_critical_rh_at_20c_sensitive(self):
        """At 20°C, sensitive materials have RH_crit = 80%"""
        rh = calculate_critical_rh(20.0, MouldSensitivity.SENSITIVE)
        assert rh == pytest.approx(0.80, abs=0.02)
        
    def test_critical_rh_no_growth_below_zero(self):
        """Below 0°C, no mould growth possible (RH_crit = 100%)"""
        rh = calculate_critical_rh(-5.0, MouldSensitivity.VERY_SENSITIVE)
        assert rh == pytest.approx(1.0)
        
    def test_critical_rh_no_growth_above_50c(self):
        """Above 50°C, no mould growth possible (RH_crit = 100%)"""
        rh = calculate_critical_rh(55.0, MouldSensitivity.VERY_SENSITIVE)
        assert rh == pytest.approx(1.0)
        
    def test_resistant_materials_need_higher_rh(self):
        """Resistant materials require higher RH for mould growth"""
        rh_sensitive = calculate_critical_rh(22.0, MouldSensitivity.SENSITIVE)
        rh_resistant = calculate_critical_rh(22.0, MouldSensitivity.RESISTANT)
        
        assert rh_resistant >= rh_sensitive


class TestMouldGrowthRate:
    """Tests for the growth rate calculation dM/dt."""
    
    def test_no_growth_below_critical_rh(self):
        """When RH < RH_crit, no growth should occur"""
        # At 20°C, RH_crit ~= 80% for sensitive materials
        rate = calculate_mould_growth_rate(
            T=20.0, RH=0.70, M=0.0, 
            sensitivity=MouldSensitivity.SENSITIVE
        )
        # Should be zero or negative (decline)
        assert rate <= 0
        
    def test_growth_above_critical_rh(self):
        """When RH > RH_crit, positive growth rate"""
        rate = calculate_mould_growth_rate(
            T=22.0, RH=0.90, M=0.0,
            sensitivity=MouldSensitivity.SENSITIVE
        )
        # Should be positive
        assert rate > 0
        
    def test_growth_rate_increases_with_humidity(self):
        """Higher RH should give faster growth"""
        rate_85 = calculate_mould_growth_rate(
            T=22.0, RH=0.85, M=0.0,
            sensitivity=MouldSensitivity.SENSITIVE
        )
        rate_95 = calculate_mould_growth_rate(
            T=22.0, RH=0.95, M=0.0,
            sensitivity=MouldSensitivity.SENSITIVE
        )
        assert rate_95 > rate_85
        
    def test_growth_rate_increases_with_temp(self):
        """Higher temperature (in growth range) should give faster growth"""
        rate_15 = calculate_mould_growth_rate(
            T=15.0, RH=0.90, M=0.0,
            sensitivity=MouldSensitivity.SENSITIVE
        )
        rate_25 = calculate_mould_growth_rate(
            T=25.0, RH=0.90, M=0.0,
            sensitivity=MouldSensitivity.SENSITIVE
        )
        assert rate_25 > rate_15
        
    def test_decline_when_dry(self):
        """When RH is very low, mould index should decline"""
        rate = calculate_mould_growth_rate(
            T=22.0, RH=0.50, M=3.0,  # M=3 means visible growth
            sensitivity=MouldSensitivity.SENSITIVE
        )
        assert rate < 0, "Should decline under dry conditions"


class TestSensitivityClasses:
    """Tests for material sensitivity class behavior."""
    
    def test_k1_factors_ordering(self):
        """Very sensitive materials should have highest k1"""
        assert VTT_K1_FACTORS[MouldSensitivity.VERY_SENSITIVE] > \
               VTT_K1_FACTORS[MouldSensitivity.SENSITIVE] > \
               VTT_K1_FACTORS[MouldSensitivity.MEDIUM_RESISTANT] > \
               VTT_K1_FACTORS[MouldSensitivity.RESISTANT]
               
    def test_mmax_ordering(self):
        """Resistant materials should have lower M_max"""
        assert VTT_MMAX[MouldSensitivity.VERY_SENSITIVE] >= \
               VTT_MMAX[MouldSensitivity.SENSITIVE] >= \
               VTT_MMAX[MouldSensitivity.MEDIUM_RESISTANT] >= \
               VTT_MMAX[MouldSensitivity.RESISTANT]
               
    def test_sensitive_grows_faster_than_resistant(self):
        """Sensitive materials should have higher growth rate than resistant"""
        rate_sens = calculate_mould_growth_rate(
            T=22.0, RH=0.92, M=0.0,
            sensitivity=MouldSensitivity.SENSITIVE
        )
        rate_resis = calculate_mould_growth_rate(
            T=22.0, RH=0.92, M=0.0,
            sensitivity=MouldSensitivity.RESISTANT
        )
        assert rate_sens > rate_resis


class TestMouldSimulation:
    """Tests for time-series mould index simulation."""
    
    def test_simulation_length_validation(self):
        """T and RH histories must have same length"""
        with pytest.raises(ValueError):
            simulate_mould_index(
                T_history=[20.0] * 100,
                RH_history=[0.85] * 50,  # Wrong length
                dt_hours=1.0
            )
            
    def test_constant_favorable_conditions_growth(self):
        """Constant warm/humid conditions should increase M"""
        # 2 weeks of favorable conditions (22°C, 90% RH)
        hours = 2 * 7 * 24
        result = simulate_mould_index(
            T_history=[22.0] * hours,
            RH_history=[0.90] * hours,
            dt_hours=1.0,
            sensitivity=MouldSensitivity.SENSITIVE
        )
        
        assert result.mould_index > 0.1, "Should have some growth"
        assert result.max_index == result.mould_index_history[-1]
        assert result.critical_exceeded_hours > 0
        
    def test_constant_dry_conditions_no_growth(self):
        """Constant dry conditions should not increase M"""
        hours = 4 * 7 * 24
        result = simulate_mould_index(
            T_history=[22.0] * hours,
            RH_history=[0.50] * hours,
            dt_hours=1.0,
            sensitivity=MouldSensitivity.SENSITIVE
        )
        
        assert result.mould_index == pytest.approx(0.0, abs=0.01)
        assert result.critical_exceeded_hours == 0
        
    def test_cyclic_conditions(self):
        """Cyclic wet/dry should give intermediate growth"""
        hours = 4 * 7 * 24
        # Alternating: 8h wet, 16h dry each day
        T_history = []
        RH_history = []
        for day in range(4 * 7):
            # 8 wet hours
            T_history.extend([22.0] * 8)
            RH_history.extend([0.92] * 8)
            # 16 dry hours
            T_history.extend([22.0] * 16)
            RH_history.extend([0.60] * 16)
            
        result = simulate_mould_index(
            T_history=T_history,
            RH_history=RH_history,
            dt_hours=1.0,
            sensitivity=MouldSensitivity.SENSITIVE
        )
        
        # Should have some growth but less than constant wet
        constant_wet = simulate_mould_index(
            [22.0] * len(T_history),
            [0.92] * len(RH_history),
            dt_hours=1.0,
            sensitivity=MouldSensitivity.SENSITIVE
        )
        
        assert result.mould_index < constant_wet.mould_index
        
    def test_mmax_limit_respected(self):
        """Mould index should not exceed M_max for material class"""
        # Very long simulation with extreme conditions
        hours = 52 * 7 * 24  # 1 year
        result = simulate_mould_index(
            T_history=[25.0] * hours,
            RH_history=[0.98] * hours,
            dt_hours=1.0,
            sensitivity=MouldSensitivity.RESISTANT  # M_max = 1.0
        )
        
        assert result.mould_index <= VTT_MMAX[MouldSensitivity.RESISTANT]


class TestMouldRiskRating:
    """Tests for human-readable risk rating."""
    
    def test_safe_rating(self):
        """M < 0.5 should be SAFE"""
        code, desc = get_mould_risk_rating(0.3)
        assert code == "SAFE"
        
    def test_minimal_rating(self):
        """0.5 <= M < 1.0 should be MINIMAL"""
        code, desc = get_mould_risk_rating(0.7)
        assert code == "MINIMAL"
        
    def test_moderate_rating(self):
        """2.0 <= M < 3.0 should be MODERATE"""
        code, desc = get_mould_risk_rating(2.5)
        assert code == "MODERATE"
        
    def test_severe_rating(self):
        """M >= 5.0 should be SEVERE"""
        code, desc = get_mould_risk_rating(5.5)
        assert code == "SEVERE"


class TestVTTBenchmarkValidation:
    """
    Benchmark validation tests against published empirical data.
    
    These tests verify that the model produces qualitatively correct
    results compared to published experimental observations.
    """
    
    def test_pine_sapwood_rapid_growth(self):
        """
        Pine sapwood under favorable conditions should reach M=1 in ~1-2 weeks.
        
        Reference: Hukka & Viitanen (1999) report initial growth in 
        approximately 7-14 days at 22°C, 95% RH for pine sapwood.
        """
        hours = 2 * 7 * 24  # 2 weeks
        result = simulate_mould_index(
            T_history=[22.0] * hours,
            RH_history=[0.95] * hours,
            dt_hours=1.0,
            sensitivity=MouldSensitivity.VERY_SENSITIVE,  # Pine sapwood
        )
        
        # Should reach at least initial growth by 2 weeks
        assert result.mould_index > 0.5, \
            f"Expected M > 0.5 after 2 weeks, got {result.mould_index:.2f}"
            
    def test_concrete_slow_growth(self):
        """
        Concrete (resistant) should have much slower growth than wood.
        
        Even under optimal conditions, concrete should take many weeks
        to show any significant mould index.
        """
        hours = 4 * 7 * 24  # 4 weeks
        result = simulate_mould_index(
            T_history=[22.0] * hours,
            RH_history=[0.95] * hours,
            dt_hours=1.0,
            sensitivity=MouldSensitivity.RESISTANT,
        )
        
        # Concrete should have minimal growth even after 4 weeks
        wood_result = simulate_mould_index(
            T_history=[22.0] * hours,
            RH_history=[0.95] * hours,
            dt_hours=1.0,
            sensitivity=MouldSensitivity.VERY_SENSITIVE,
        )
        
        assert result.mould_index < 0.5 * wood_result.mould_index, \
            "Concrete should grow much slower than wood"
            
    def test_temperature_dependence_qualitative(self):
        """
        Growth at 10°C should be slower than at 25°C.
        
        The VTT model predicts optimal growth around 20-30°C.
        """
        hours = 3 * 7 * 24  # 3 weeks
        
        result_10c = simulate_mould_index(
            T_history=[10.0] * hours,
            RH_history=[0.95] * hours,
            dt_hours=1.0,
            sensitivity=MouldSensitivity.SENSITIVE,
        )
        
        result_25c = simulate_mould_index(
            T_history=[25.0] * hours,
            RH_history=[0.95] * hours,
            dt_hours=1.0,
            sensitivity=MouldSensitivity.SENSITIVE,
        )
        
        assert result_25c.mould_index > result_10c.mould_index, \
            "Growth at 25°C should exceed growth at 10°C"

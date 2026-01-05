import pytest
import numpy as np
from backend.core.mold_analysis import calculate_saturation_pressure, calculate_surface_humidity

def test_saturation_pressure():
    # Test values based on standard tables or online calculators
    # 0C -> ~611 Pa
    # 20C -> ~2337 Pa
    # 100C -> ~101325 Pa (approximated by Magnus, it diverges at high T but valid for building physics range)
    
    p0 = calculate_saturation_pressure(0)
    assert 610 < p0 < 612
    
    p20 = calculate_saturation_pressure(20)
    assert 2330 < p20 < 2345
    
def test_surface_humidity():
    # Case 1: Surface = Air
    # T_surf = 20, T_air = 20, RH_air = 0.5
    # RH_surf should be 0.5
    rh = calculate_surface_humidity(20, 20, 0.5)
    assert np.isclose(rh, 0.5)
    
    # Case 2: Dew point (approx)
    # T_air = 20, RH = 50% => Psat=2339, Pv=1169
    # T_surf that gives Psat=1169 is approx 9.3C
    rh_dew = calculate_surface_humidity(9.3, 20.0, 0.5)
    # Should be close to 1.0
    assert 0.98 < rh_dew < 1.02
    
def test_surface_humidity_array():
    # Verify it works with arrays
    t_surf = np.array([20.0, 9.3])
    rh = calculate_surface_humidity(t_surf, 20.0, 0.5)
    assert rh.shape == (2,)
    assert np.isclose(rh[0], 0.5)
    assert rh[1] > 0.9

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
Glaser Method for Interstitial Condensation Analysis (ISO 13788)

This module implements the simplified steady-state Glaser method for assessing
the risk of interstitial condensation due to water vapor diffusion, compliant
with ISO 13788:2012.

The method calculates temperature and vapor pressure profiles through a 
multi-layer building component and identifies interfaces where condensation
may occur (where vapor pressure exceeds saturation pressure).

References:
    - ISO 13788:2012 - Hygrothermal performance of building components
    - DIN 4108-3:2018 - Wärmeschutz im Hochbau (German national annex)
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np

from backend.core.mold_analysis import calculate_saturation_pressure


@dataclass
class Layer:
    """
    Represents a single layer in a building component for Glaser analysis.
    
    Attributes:
        name: Descriptive name of the material
        thickness_m: Layer thickness in meters
        lambda_W_mK: Thermal conductivity in W/(m·K)
        mu: Water vapor diffusion resistance factor (dimensionless)
        
    The sd-value (equivalent air layer thickness for diffusion) is calculated as:
        sd = thickness_m * mu
    """
    name: str
    thickness_m: float
    lambda_W_mK: float
    mu: float  # Water vapor diffusion resistance factor
    
    @property
    def R(self) -> float:
        """Thermal resistance in (m²·K)/W"""
        return self.thickness_m / self.lambda_W_mK
    
    @property
    def sd(self) -> float:
        """Equivalent air layer thickness for water vapor diffusion in meters"""
        return self.thickness_m * self.mu


@dataclass 
class GlaserResult:
    """
    Results from Glaser analysis.
    
    Attributes:
        interfaces: Names of interfaces (n+1 for n layers, including surfaces)
        temperatures: Temperature at each interface [°C]
        vapor_pressures: Actual vapor pressure at each interface [Pa]
        saturation_pressures: Saturation vapor pressure at each interface [Pa]
        condensation_risk: Boolean indicating if condensation occurs at each interface
        condensation_interfaces: List of interface indices where condensation occurs
    """
    interfaces: List[str]
    temperatures: np.ndarray
    vapor_pressures: np.ndarray
    saturation_pressures: np.ndarray
    condensation_risk: np.ndarray
    
    @property
    def condensation_interfaces(self) -> List[int]:
        """Indices of interfaces where condensation risk exists"""
        return list(np.where(self.condensation_risk)[0])
    
    @property
    def has_condensation(self) -> bool:
        """True if any interface has condensation risk"""
        return bool(np.any(self.condensation_risk))


def calculate_temperature_profile(
    layers: List[Layer],
    T_interior: float,
    T_exterior: float,
    R_si: float = 0.13,
    R_se: float = 0.04
) -> Tuple[np.ndarray, List[str]]:
    """
    Calculate steady-state temperature profile through a multi-layer component.
    
    Uses the thermal resistance method: temperature drop across each layer is
    proportional to its thermal resistance relative to total resistance.
    
    Args:
        layers: List of Layer objects from interior to exterior
        T_interior: Interior air temperature [°C]
        T_exterior: Exterior air temperature [°C]  
        R_si: Interior surface resistance [(m²·K)/W], default 0.13 (horizontal heat flow)
        R_se: Exterior surface resistance [(m²·K)/W], default 0.04
        
    Returns:
        Tuple of (temperatures array, interface names list)
        
        Temperatures array has n+3 elements for n layers:
        [T_interior, T_surface_int, T_interface_1, ..., T_interface_n-1, T_surface_ext, T_exterior]
        
    Example:
        >>> layers = [Layer("Concrete", 0.2, 1.0, 80)]
        >>> T, names = calculate_temperature_profile(layers, 20.0, -5.0)
        >>> print(f"Surface temps: interior={T[1]:.1f}°C, exterior={T[-2]:.1f}°C")
    """
    # Build resistance array: [R_si, R_layer1, R_layer2, ..., R_se]
    resistances = [R_si] + [layer.R for layer in layers] + [R_se]
    R_total = sum(resistances)
    
    # Temperature difference
    delta_T = T_interior - T_exterior
    
    # Calculate temperatures at each interface
    # n layers -> n+1 material interfaces + 2 air boundaries = n+3 points
    n_interfaces = len(layers) + 3
    temperatures = np.zeros(n_interfaces)
    temperatures[0] = T_interior
    
    cumulative_R = 0.0
    for i, R in enumerate(resistances):
        cumulative_R += R
        temperatures[i + 1] = T_interior - (cumulative_R / R_total) * delta_T
    
    # Generate interface names
    names = ["Interior Air", "Interior Surface"]
    for i, layer in enumerate(layers[:-1]):
        names.append(f"{layer.name} / {layers[i+1].name}")
    if layers:
        names.append("Exterior Surface")
    names.append("Exterior Air")
    
    return temperatures, names


def calculate_vapor_pressure_profile(
    layers: List[Layer],
    T_interior: float,
    T_exterior: float,
    phi_interior: float,
    phi_exterior: float,
    R_si: float = 0.13,
    R_se: float = 0.04
) -> GlaserResult:
    """
    Calculate vapor pressure profile and identify condensation risk.
    
    Implements the Glaser method (ISO 13788) assuming:
    - Steady-state conditions
    - 1D moisture transport by vapor diffusion only
    - Linear vapor pressure gradient within each layer
    
    Args:
        layers: List of Layer objects from interior to exterior
        T_interior: Interior air temperature [°C]
        T_exterior: Exterior air temperature [°C]
        phi_interior: Interior relative humidity [0.0-1.0]
        phi_exterior: Exterior relative humidity [0.0-1.0]
        R_si: Interior surface resistance [(m²·K)/W]
        R_se: Exterior surface resistance [(m²·K)/W]
        
    Returns:
        GlaserResult with temperature/pressure profiles and condensation analysis
        
    Note:
        The vapor pressure at air boundaries equals p_sat * phi.
        At material interfaces, pressure is interpolated based on sd-values.
    """
    # Get temperature profile
    temperatures, interface_names = calculate_temperature_profile(
        layers, T_interior, T_exterior, R_si, R_se
    )
    
    # Calculate saturation pressure at each interface
    saturation_pressures = calculate_saturation_pressure(temperatures)
    
    # Calculate actual vapor pressure profile
    # Boundary conditions: interior and exterior air
    p_interior = saturation_pressures[0] * phi_interior
    p_exterior = saturation_pressures[-1] * phi_exterior
    
    # For internal interfaces, vapor pressure follows linear profile based on sd-values
    # sd-values: [0 (interior air), layer1.sd, layer2.sd, ..., 0 (exterior air)]
    sd_values = [0.0] + [layer.sd for layer in layers] + [0.0]
    sd_total = sum(sd_values)
    
    if sd_total == 0:
        # Degenerate case - no vapor resistance
        vapor_pressures = np.linspace(p_interior, p_exterior, len(temperatures))
    else:
        vapor_pressures = np.zeros(len(temperatures))
        vapor_pressures[0] = p_interior
        vapor_pressures[-1] = p_exterior
        
        delta_p = p_interior - p_exterior
        cumulative_sd = 0.0
        
        for i in range(1, len(temperatures) - 1):
            cumulative_sd += sd_values[i]
            vapor_pressures[i] = p_interior - (cumulative_sd / sd_total) * delta_p
    
    # Check for condensation: vapor pressure > saturation pressure
    # Use small tolerance to avoid floating point issues
    condensation_risk = vapor_pressures > (saturation_pressures + 1e-6)
    
    return GlaserResult(
        interfaces=interface_names,
        temperatures=temperatures,
        vapor_pressures=vapor_pressures,
        saturation_pressures=saturation_pressures,
        condensation_risk=condensation_risk
    )


def check_monthly_condensation(
    layers: List[Layer],
    monthly_T_interior: List[float],
    monthly_T_exterior: List[float],
    monthly_phi_interior: List[float],
    monthly_phi_exterior: List[float],
    R_si: float = 0.13,
    R_se: float = 0.04
) -> List[GlaserResult]:
    """
    Perform month-by-month Glaser analysis for annual assessment.
    
    ISO 13788 requires checking condensation for each month using monthly
    mean temperatures and humidities to assess annual accumulation/drying.
    
    Args:
        layers: List of Layer objects
        monthly_T_interior: 12 monthly interior temperatures [°C]
        monthly_T_exterior: 12 monthly exterior temperatures [°C]  
        monthly_phi_interior: 12 monthly interior relative humidities [0-1]
        monthly_phi_exterior: 12 monthly exterior relative humidities [0-1]
        R_si, R_se: Surface resistances
        
    Returns:
        List of 12 GlaserResult objects, one per month
        
    Raises:
        ValueError: If input lists don't have exactly 12 elements
    """
    if not all(len(lst) == 12 for lst in [
        monthly_T_interior, monthly_T_exterior,
        monthly_phi_interior, monthly_phi_exterior
    ]):
        raise ValueError("All monthly data lists must have exactly 12 elements")
    
    results = []
    for month in range(12):
        result = calculate_vapor_pressure_profile(
            layers,
            monthly_T_interior[month],
            monthly_T_exterior[month],
            monthly_phi_interior[month],
            monthly_phi_exterior[month],
            R_si,
            R_se
        )
        results.append(result)
    
    return results


def get_typical_humidity_class(
    T_exterior: float,
    humidity_class: int = 3
) -> float:
    """
    Calculate typical interior humidity based on EN ISO 13788 humidity classes.
    
    For maritime climates, ISO 13788 defines 5 humidity classes based on
    excess vapor pressure above external conditions.
    
    Args:
        T_exterior: Monthly mean external temperature [°C]
        humidity_class: 1-5, where:
            1: Storage/warehouse
            2: Office/shop 
            3: Residential (normal occupancy)
            4: High occupancy (sports hall, kitchen)
            5: Special (swimming pool, laundry)
            
    Returns:
        Excess vapor pressure delta_p [Pa]
        
    Note:
        Interior vapor pressure = exterior vapor pressure + delta_p
    """
    # ISO 13788 Table 2 - Excess vapor pressure for maritime climate
    # Varies linearly from T_e = 0°C to T_e = 20°C
    if T_exterior <= 0:
        delta_p_max = [270, 540, 810, 1080, 1350][humidity_class - 1]
    elif T_exterior >= 20:
        delta_p_max = [0, 0, 0, 0, 0][humidity_class - 1]  # No excess at 20°C
    else:
        # Linear interpolation
        delta_p_0 = [270, 540, 810, 1080, 1350][humidity_class - 1]
        delta_p_max = delta_p_0 * (1 - T_exterior / 20)
    
    return delta_p_max

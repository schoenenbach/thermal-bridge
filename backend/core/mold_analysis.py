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
Mold & Condensation Risk Analysis Module

This module provides functions to calculate surface relative humidity and identify
areas at risk of mold growth, compliant with ISO 13788 principles.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from typing import Union, BinaryIO
from io import BytesIO

def calculate_saturation_pressure(temp_c: np.ndarray) -> np.ndarray:
    """
    Calculate saturation vapor pressure using the Magnus formula.
    
    Args:
        temp_c: Temperature in degrees Celsius (scalar or array)
        
    Returns:
        Saturation pressure in Pascals [Pa]
        
    Reference:
        Alduchov, O.A. and Eskridge, R.E., 1996. Improved Magnus form approximation 
        of saturation vapor pressure. Journal of Applied Meteorology and Climatology.
        
    Formula:
        610.94 * exp( (17.625 * T) / (T + 243.04) )
    """
    return 610.94 * np.exp((17.625 * temp_c) / (temp_c + 243.04))


def calculate_surface_humidity(temp_surf: np.ndarray, 
                               temp_air: float, 
                               rh_air: float) -> np.ndarray:
    """
    Calculate surface relative humidity.
    
    Assumes constant vapor pressure across the boundary layer (p_surf = p_air).
    
    Args:
        temp_surf: Surface temperature field [°C]
        temp_air: Indoor air temperature [°C]
        rh_air: Indoor relative humidity [0.0 - 1.0] (e.g. 0.5 for 50%)
        
    Returns:
        Surface relative humidity [0.0 - 1.0]
    """
    # 1. Partial vapor pressure of indoor air
    p_sat_air = calculate_saturation_pressure(temp_air)
    p_vapor = p_sat_air * rh_air
    
    # 2. Saturation pressure at surface
    p_sat_surf = calculate_saturation_pressure(temp_surf)
    
    # 3. Surface RH = p_vapor / p_sat_surf
    # Avoid division by zero (unlikely with kelvin-like range, but good practice)
    rh_surf = p_vapor / (p_sat_surf + 1e-9)
    
    # Clamp to physical limits (can't exceed 100% physically without condensation/rainout)
    # But for risk analysis, values > 1.0 indicate condensation
    return rh_surf


def plot_mold_risk_map(rh_grid: np.ndarray,
                       width_mm: float,
                       height_mm: float,
                       filename: Union[str, BinaryIO, None],
                       x_coords: np.ndarray = None,
                       y_coords: np.ndarray = None):
    """
    Plot Mold Risk Map using a traffic light scheme.
    
    Schemes (based on ISO 13788 / DIN 4108):
    - Green: RH < 0.70 (Safe)
    - Yellow: 0.70 <= RH <= 0.80 (Critical)
    - Red: RH > 0.80 (Mold Risk)
    
    Args:
        rh_grid: 2D array of Relative Humidity [0.0 - 1.xx]
        width_mm: Domain width
        height_mm: Domain height
        filename: Output path, BytesIO buffer, or None (creates new buffer)
        x_coords, y_coords: Optional adaptive mesh coordinates
        
    Returns:
        The filename (str) or buffer (BytesIO).
    """
    plt.figure(figsize=(10, 8))
    
    # Strictly Discrete Traffic Light Scheme
    # Green: [0, 0.7)
    # Yellow: [0.7, 0.8)
    # Red: [0.8, 2.0]
    
    colors = ['#2ecc71', '#f1c40f', '#e74c3c'] # Green, Yellow, Red
    bounds = [0.0, 0.7, 0.8, 2.0] 
    cmap = mcolors.ListedColormap(colors)
    norm = mcolors.BoundaryNorm(bounds, cmap.N)
    
    # Use pcolormesh for both Adaptive and Uniform mesh (construct coords if missing)
    if x_coords is None:
        x_coords = np.linspace(0, width_mm, rh_grid.shape[1] + 1)
    if y_coords is None:
        y_coords = np.linspace(0, height_mm, rh_grid.shape[0] + 1)
    
    # Ensure coords match grid shape for flat shading (grid is N, M; coords N+1, M+1)
    # If coords provided are cell centers, adjustments might be needed, but usually mesh.x_coords are nodes.
    # AdaptiveMesh.x_coords are node positions.
    
    X, Y = np.meshgrid(x_coords, y_coords)
    
    # Main Colored Plot
    im = plt.pcolormesh(X, Y, rh_grid, cmap=cmap, norm=norm, shading='flat', alpha=0.9)
    plt.colorbar(im, label='Surface RH Classification', ticks=[0.35, 0.75, 0.9])
    
    # Overlay Hatches for emphasis
    # We do this by plotting transparent layers with hatches where conditions are met
    
    # Critical Zone (Yellow) - Diagonal Hatch
    rh_yellow = np.ma.masked_outside(rh_grid, 0.7, 0.7999)
    plt.pcolormesh(X, Y, rh_yellow, hatch='//', alpha=0.0, shading='flat') # Alpha 0 for color, but hatch remains? No, pcolor hatch follows alpha often.
    # Actually, contourf is better for hatching specific regions over a pcolormesh base
    
    xc = (x_coords[:-1] + x_coords[1:]) / 2.0
    yc = (y_coords[:-1] + y_coords[1:]) / 2.0
    Xc, Yc = np.meshgrid(xc, yc)
    
    # Contourf for Hatches (Yellow)
    plt.contourf(Xc, Yc, rh_grid, levels=[0.7, 0.8], colors='none', hatches=['///'])
    
    # Contourf for Hatches (Red) - Cross Hatch
    # Use a large upper bound
    plt.contourf(Xc, Yc, rh_grid, levels=[0.8, 10.0], colors='none', hatches=['XX'])

    # Isoline at 0.8
    if np.min(rh_grid) < 0.8 < np.max(rh_grid):
        CS = plt.contour(Xc, Yc, rh_grid, levels=[0.8], colors='black', linewidths=2.0)
        plt.clabel(CS, inline=True, fmt='RH=0.8', fontsize=12)

    plt.title('Mold Risk Analysis (ISO 13788)\nGreen: Safe (<70%) | Yellow: Critical (70-80%) | Red: Risk (>80%)')
    plt.xlabel('Depth [mm]')
    plt.ylabel('Facade Length [mm]')
    
    # Ensure aspect ratio is equal so geometry isn't distorted
    plt.gca().set_aspect('equal', adjustable='box')
    
    plt.tight_layout()
    plt.tight_layout()
    
    if filename is None:
        buf = BytesIO()
        plt.savefig(buf, dpi=150)
        plt.close()
        buf.seek(0)
        return buf
    elif isinstance(filename, str):
        plt.savefig(filename, dpi=150)
        plt.close()
        return filename
    else:
        plt.savefig(filename, dpi=150)
        plt.close()
        return filename


# =============================================================================
# VTT Mould Index Model (Hukka & Viitanen, 1999)
# =============================================================================

from enum import IntEnum
from typing import List, Tuple
from dataclasses import dataclass


class MouldSensitivity(IntEnum):
    """
    Material sensitivity classes for VTT Mould Index model.
    
    Based on Ojanen et al. (2010) extension of the original VTT model.
    Higher values indicate more resistance to mold growth.
    """
    VERY_SENSITIVE = 0   # Untreated wood (pine/spruce sapwood)
    SENSITIVE = 1        # Planed wood, paper-faced products
    MEDIUM_RESISTANT = 2 # Cement board, glass wool, some plastics
    RESISTANT = 3        # Concrete, brick, ceramic


class MouldDeclineClass(IntEnum):
    """
    Decline rate classes for unfavorable conditions.
    
    How quickly the mould index decreases when T/RH drop below critical.
    """
    SIGNIFICANT_DECLINE = 0  # Wood materials - fast decline
    MODERATE_DECLINE = 1     # Paper, some boards
    LOW_DECLINE = 2          # Concrete, mineral materials


@dataclass
class VTTMouldResult:
    """
    Results from VTT Mould Index simulation.
    
    Attributes:
        mould_index: Final mould index value [0-6]
        mould_index_history: Time series of M values
        time_weeks: Time points in weeks
        max_index: Maximum index reached
        critical_exceeded_hours: Hours where RH > RH_crit
    """
    mould_index: float
    mould_index_history: List[float]
    time_weeks: List[float]
    max_index: float
    critical_exceeded_hours: float


# VTT Model coefficients (Ojanen et al., 2010)
# k1 and k2 factors for different sensitivity classes
VTT_K1_FACTORS = {
    MouldSensitivity.VERY_SENSITIVE: 1.0,
    MouldSensitivity.SENSITIVE: 0.578,
    MouldSensitivity.MEDIUM_RESISTANT: 0.072,
    MouldSensitivity.RESISTANT: 0.033,
}

VTT_K2_FACTORS = {
    MouldSensitivity.VERY_SENSITIVE: 1.0,
    MouldSensitivity.SENSITIVE: 0.386,
    MouldSensitivity.MEDIUM_RESISTANT: 0.097,
    MouldSensitivity.RESISTANT: 0.014,
}

# Maximum mould index for each sensitivity class
VTT_MMAX = {
    MouldSensitivity.VERY_SENSITIVE: 6.0,
    MouldSensitivity.SENSITIVE: 6.0,
    MouldSensitivity.MEDIUM_RESISTANT: 3.0,
    MouldSensitivity.RESISTANT: 1.0,
}


def calculate_critical_rh(
    T: float, 
    sensitivity: MouldSensitivity = MouldSensitivity.SENSITIVE
) -> float:
    """
    Calculate critical relative humidity below which no mould growth occurs.
    
    Uses the VTT model formula from Hukka & Viitanen (1999):
    RH_crit = min(100, max(RH_min, -0.00267*T^3 + 0.160*T^2 - 3.13*T + 100))
    
    For temperatures outside 0-50°C range, mould growth stops regardless of RH.
    
    Args:
        T: Temperature in °C
        sensitivity: Material sensitivity class
        
    Returns:
        Critical RH as fraction [0.0-1.0]
        
    Note:
        Returns 1.0 (100%) for temperatures outside growth range,
        meaning growth is impossible regardless of humidity.
    """
    # No growth outside 0-50°C range
    if T <= 0 or T >= 50:
        return 1.0
    
    # RH_min depends on sensitivity class
    if sensitivity in (MouldSensitivity.VERY_SENSITIVE, MouldSensitivity.SENSITIVE):
        rh_min = 0.80
    else:
        rh_min = 0.85
    
    # Polynomial approximation for RH_crit(T)
    # Valid for T in range [0, 50]°C
    if T < 20:
        rh_crit = (-0.00267 * T**3 + 0.160 * T**2 - 3.13 * T + 100) / 100.0
    else:
        # For T >= 20°C, RH_crit is constant at RH_min
        rh_crit = rh_min
    
    return max(rh_min, min(1.0, rh_crit))


def calculate_mould_growth_rate(
    T: float,
    RH: float,
    M: float,
    sensitivity: MouldSensitivity = MouldSensitivity.SENSITIVE,
    surface_quality: int = 0
) -> float:
    """
    Calculate instantaneous mould growth rate dM/dt.
    
    Based on Hukka & Viitanen (1999) with extensions from Ojanen et al. (2010).
    
    The rate depends on:
    - Temperature and humidity (favorable conditions)
    - Current mould index (growth slows as M approaches M_max)
    - Material sensitivity class
    - Surface quality (0 = sawn, 1 = kiln-dried quality)
    
    Args:
        T: Surface temperature [°C]
        RH: Surface relative humidity [0.0-1.0]
        M: Current mould index [0-6]
        sensitivity: Material sensitivity class
        surface_quality: 0 for rough, 1 for smooth (affects wood only)
        
    Returns:
        Growth rate dM/dt in [index units per week]
        Negative values indicate decline.
    """
    # Check if conditions are favorable for growth
    RH_crit = calculate_critical_rh(T, sensitivity)
    
    # No growth if RH < RH_crit or T outside range
    if RH < RH_crit or T <= 0 or T >= 50:
        # Return decline rate
        return _calculate_decline_rate(M, T, RH, sensitivity)
    
    # Get sensitivity factors
    k1 = VTT_K1_FACTORS[sensitivity]
    k2 = VTT_K2_FACTORS[sensitivity]
    M_max = VTT_MMAX[sensitivity]
    
    # Time to reach M=1 under favorable conditions (weeks)
    # From Hukka & Viitanen (1999), Eq. 4
    RH_pct = RH * 100
    
    # Avoid log of zero or negative
    if RH_pct <= RH_crit * 100:
        return 0.0
    
    log_term = np.log(RH_pct - RH_crit * 100 + 1e-6)
    
    # t_1 = weeks to reach M=1
    # Simplified from original complex formula
    W = 0 if sensitivity in (MouldSensitivity.VERY_SENSITIVE, MouldSensitivity.SENSITIVE) else 0
    SQ = surface_quality
    
    t_1 = np.exp(-0.68 * np.log(T + 1e-6) - 13.9 * np.log(RH_pct + 1e-6) + 
                  0.14 * W - 0.33 * SQ + 66.02)
    
    # Prevent extreme values
    t_1 = max(0.001, min(t_1, 1e6))
    
    # Base growth rate
    dM_dt_base = 1.0 / t_1
    
    # Apply sensitivity factor k1
    dM_dt = k1 * dM_dt_base
    
    # Apply moderation factor as M approaches M_max
    # Growth slows down as mould index increases
    if M > 1:
        k2_mod = max(0, 1 - (M / M_max)**2) * k2
        dM_dt *= (1 + k2_mod)
    
    return dM_dt


def _calculate_decline_rate(
    M: float,
    T: float,
    RH: float,
    sensitivity: MouldSensitivity
) -> float:
    """
    Calculate mould index decline rate under unfavorable conditions.
    
    When T or RH drop below growth thresholds, the mould index decreases.
    The rate depends on how unfavorable conditions are and material class.
    
    Returns:
        Negative rate in [index units per week]
    """
    if M <= 0:
        return 0.0
    
    # Determine decline class from sensitivity
    if sensitivity == MouldSensitivity.VERY_SENSITIVE:
        C_decline = -0.032  # Fast decline
    elif sensitivity == MouldSensitivity.SENSITIVE:
        C_decline = -0.032
    elif sensitivity == MouldSensitivity.MEDIUM_RESISTANT:
        C_decline = -0.016
    else:
        C_decline = -0.008  # Slow decline
    
    # Decline is faster at very low RH or freezing temps
    if T < 0:
        C_decline *= 2.0
    if RH < 0.5:
        C_decline *= 1.5
    
    return C_decline


def simulate_mould_index(
    T_history: List[float],
    RH_history: List[float],
    dt_hours: float = 1.0,
    sensitivity: MouldSensitivity = MouldSensitivity.SENSITIVE,
    M_initial: float = 0.0
) -> VTTMouldResult:
    """
    Integrate mould index over a time series of T and RH conditions.
    
    This is the main entry point for VTT model simulation with real
    temperature and humidity data (e.g., from transient thermal simulation).
    
    Args:
        T_history: List of surface temperatures [°C], one per timestep
        RH_history: List of surface relative humidities [0-1], one per timestep
        dt_hours: Time step size in hours
        sensitivity: Material sensitivity class
        M_initial: Starting mould index (default 0 = no mould)
        
    Returns:
        VTTMouldResult with mould index history and statistics
        
    Example:
        >>> # 4 weeks of constant warm/humid conditions
        >>> T = [22.0] * (4 * 7 * 24)  # 4 weeks hourly
        >>> RH = [0.85] * len(T)
        >>> result = simulate_mould_index(T, RH, dt_hours=1.0)
        >>> print(f"Final M = {result.mould_index:.2f}")
    """
    if len(T_history) != len(RH_history):
        raise ValueError("T_history and RH_history must have same length")
    
    dt_weeks = dt_hours / (7 * 24)  # Convert hours to weeks
    
    M = M_initial
    M_max = VTT_MMAX[sensitivity]
    
    mould_history = [M]
    time_weeks = [0.0]
    critical_exceeded = 0.0
    
    for i, (T, RH) in enumerate(zip(T_history, RH_history)):
        # Check if critical RH is exceeded
        RH_crit = calculate_critical_rh(T, sensitivity)
        if RH > RH_crit and 0 < T < 50:
            critical_exceeded += dt_hours
        
        # Calculate growth rate
        dM_dt = calculate_mould_growth_rate(T, RH, M, sensitivity)
        
        # Euler integration
        M += dM_dt * dt_weeks
        
        # Clamp to valid range
        M = max(0.0, min(M_max, M))
        
        mould_history.append(M)
        time_weeks.append((i + 1) * dt_weeks)
    
    return VTTMouldResult(
        mould_index=M,
        mould_index_history=mould_history,
        time_weeks=time_weeks,
        max_index=max(mould_history),
        critical_exceeded_hours=critical_exceeded
    )


def get_mould_risk_rating(mould_index: float) -> Tuple[str, str]:
    """
    Convert mould index to human-readable rating.
    
    VTT Mould Index Scale:
    0 - No growth
    1 - Initial growth, microscopic
    2 - Moderate growth, microscopic (10% coverage)
    3 - Visible growth, visual detection possible
    4 - Visible growth, >10% coverage
    5 - Abundant growth, >50% coverage
    6 - Very heavy growth, ~100% coverage
    
    Args:
        mould_index: Calculated mould index [0-6]
        
    Returns:
        Tuple of (rating_code, description)
    """
    if mould_index < 0.5:
        return ("SAFE", "No mould growth")
    elif mould_index < 1.0:
        return ("MINIMAL", "Trace/initial growth (microscopic)")
    elif mould_index < 2.0:
        return ("LOW", "Some growth visible under microscope")
    elif mould_index < 3.0:
        return ("MODERATE", "Visual detection becoming possible")
    elif mould_index < 4.0:
        return ("ELEVATED", "Clearly visible growth (<10% coverage)")
    elif mould_index < 5.0:
        return ("HIGH", "Significant coverage (10-50%)")
    else:
        return ("SEVERE", "Heavy to complete coverage (>50%)")


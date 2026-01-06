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

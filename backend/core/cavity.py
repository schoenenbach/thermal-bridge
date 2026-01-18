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
ISO 10077-2 Air Cavity Thermal Analysis Module

Implements iterative equivalent thermal conductivity (λ_eq) calculation for
unventilated air cavities per ISO 10077-2 and EN 673.

The equivalent conductivity depends on:
- Cavity dimensions (thickness d, breadth b)
- Surface temperatures (affects convection and radiation)
- Surface emissivities

This module provides:
- Cavity detection via flood-fill algorithm
- λ_eq calculation per ISO 10077-2 formulas
- Iterative solver wrapper for temperature-dependent conductivity
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set
import numpy as np
from collections import deque

# Physical constants
STEFAN_BOLTZMANN = 5.67e-8  # W/(m²·K⁴)
T_KELVIN_OFFSET = 273.15    # K


@dataclass
class CavityRegion:
    """
    Represents a detected air cavity region in the grid.
    
    Attributes:
        cells: List of (row, col) tuples identifying cavity cells
        d: Cavity thickness perpendicular to heat flow (m)
        b: Cavity breadth parallel to heat flow (m)
        aspect_ratio: b/d ratio
        bounds: (row_min, row_max, col_min, col_max) bounding box
        lambda_eq: Currently assigned equivalent conductivity (W/mK)
    """
    cells: List[Tuple[int, int]]
    d: float
    b: float
    aspect_ratio: float
    bounds: Tuple[int, int, int, int]
    lambda_eq: float = 0.25  # Initial estimate per ISO 6946


def detect_cavities(
    grid_map: np.ndarray,
    dx_m: float,
    dy_m: float,
    cavity_material_id: int = 8  # MaterialID.CAVITY
) -> List[CavityRegion]:
    """
    Detect all connected air cavity regions using flood-fill.
    
    Args:
        grid_map: 2D array of material IDs
        dx_m: Grid cell width (m)
        dy_m: Grid cell height (m)
        cavity_material_id: Material ID for cavity cells (default: 8)
        
    Returns:
        List of CavityRegion objects, one per distinct cavity
    """
    rows, cols = grid_map.shape
    visited = np.zeros_like(grid_map, dtype=bool)
    cavities = []
    
    # Find all cavity cells
    cavity_mask = (grid_map == cavity_material_id)
    
    for start_r in range(rows):
        for start_c in range(cols):
            if cavity_mask[start_r, start_c] and not visited[start_r, start_c]:
                # Flood-fill from this cell
                cells = _flood_fill(cavity_mask, visited, start_r, start_c)
                if cells:
                    cavity = _create_cavity_region(cells, dx_m, dy_m)
                    cavities.append(cavity)
    
    return cavities


def _flood_fill(
    mask: np.ndarray,
    visited: np.ndarray,
    start_r: int,
    start_c: int
) -> List[Tuple[int, int]]:
    """
    Perform 4-connected flood-fill starting from (start_r, start_c).
    
    Args:
        mask: Boolean mask of cavity cells
        visited: Boolean array tracking visited cells (modified in-place)
        start_r, start_c: Starting coordinates
        
    Returns:
        List of (row, col) tuples in this connected region
    """
    rows, cols = mask.shape
    cells = []
    queue = deque([(start_r, start_c)])
    visited[start_r, start_c] = True
    
    while queue:
        r, c = queue.popleft()
        cells.append((r, c))
        
        # Check 4-connected neighbors
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if mask[nr, nc] and not visited[nr, nc]:
                    visited[nr, nc] = True
                    queue.append((nr, nc))
    
    return cells


def _create_cavity_region(
    cells: List[Tuple[int, int]],
    dx_m: float,
    dy_m: float
) -> CavityRegion:
    """
    Create a CavityRegion from a list of cell coordinates.
    
    Calculates cavity dimensions assuming heat flows primarily in x-direction
    (typical for wall cavities with interior on left, exterior on right).
    
    Args:
        cells: List of (row, col) cavity cell coordinates
        dx_m: Cell width (m)
        dy_m: Cell height (m)
        
    Returns:
        CavityRegion with calculated geometry
    """
    if not cells:
        raise ValueError("Cannot create CavityRegion from empty cell list")
    
    rows = [c[0] for c in cells]
    cols = [c[1] for c in cells]
    
    row_min, row_max = min(rows), max(rows)
    col_min, col_max = min(cols), max(cols)
    
    # Cavity dimensions
    # d = thickness (x-direction, across heat flow)
    # b = breadth (y-direction, along heat flow)
    d = (col_max - col_min + 1) * dx_m
    b = (row_max - row_min + 1) * dy_m
    
    # For thin horizontal cavities, b > d
    # For thin vertical cavities (slots), d > b
    aspect_ratio = b / d if d > 0 else 1.0
    
    return CavityRegion(
        cells=cells,
        d=d,
        b=b,
        aspect_ratio=aspect_ratio,
        bounds=(row_min, row_max, col_min, col_max)
    )


def calculate_lambda_eq(
    d: float,
    T_hot: float,
    T_cold: float,
    eps_1: float = 0.9,
    eps_2: float = 0.9,
    b: Optional[float] = None
) -> float:
    """
    Calculate equivalent thermal conductivity for an air cavity per ISO 10077-2.
    
    λ_eq = d × (h_a + h_r)
    
    where:
    - h_a: Convective heat transfer coefficient
    - h_r: Radiative heat transfer coefficient
    
    Args:
        d: Cavity thickness (m) - perpendicular to heat flow
        T_hot: Temperature of warm surface (°C)
        T_cold: Temperature of cold surface (°C)
        eps_1: Emissivity of hot surface (0-1)
        eps_2: Emissivity of cold surface (0-1)
        b: Cavity breadth (m) - parallel to heat flow (optional, for aspect ratio correction)
        
    Returns:
        Equivalent thermal conductivity λ_eq (W/mK)
    """
    if d <= 0:
        return 0.025  # Very thin gap, treat as still air
    
    # Temperature difference
    delta_T = abs(T_hot - T_cold)
    
    # Mean temperature (convert to Kelvin for radiation calc)
    T_mean_C = (T_hot + T_cold) / 2
    T_mean_K = T_mean_C + T_KELVIN_OFFSET
    
    # --- Convective coefficient h_a ---
    # ISO 10077-2 / EN 673 formula for vertical cavities
    # h_a = max(0.025/d, C × (ΔT)^n)
    # For vertical cavity: C = 0.73, n = 0.25 (simplified Rayleigh correlation)
    
    if delta_T > 0.01:  # Avoid division by zero
        # Grashof-based correlation (simplified)
        h_a_convection = 0.73 * (delta_T ** 0.25)
    else:
        h_a_convection = 0.0
    
    # Pure conduction limit for still air
    h_a_conduction = 0.025 / d  # λ_air ≈ 0.025 W/mK
    
    h_a = max(h_a_conduction, h_a_convection)
    
    # --- Radiative coefficient h_r ---
    # h_r = 4 × σ × T_m³ × E_eff
    # E_eff = 1 / (1/ε₁ + 1/ε₂ - 1)  (effective emissivity for parallel plates)
    
    E_eff = 1.0 / (1.0 / eps_1 + 1.0 / eps_2 - 1.0)
    h_r = 4.0 * STEFAN_BOLTZMANN * (T_mean_K ** 3) * E_eff
    
    # --- Total equivalent conductivity ---
    h_total = h_a + h_r
    lambda_eq = d * h_total
    
    # Reasonable bounds
    lambda_eq = max(0.025, min(lambda_eq, 5.0))
    
    return lambda_eq


def get_cavity_surface_temperatures(
    temp_field: np.ndarray,
    cavity: CavityRegion
) -> Tuple[float, float]:
    """
    Extract average hot and cold surface temperatures for a cavity.
    
    Assumes heat flows from left (internal/hot) to right (external/cold),
    so hot surface is at col_min-1, cold surface is at col_max+1.
    
    Args:
        temp_field: 2D temperature array
        cavity: CavityRegion object
        
    Returns:
        (T_hot, T_cold) average surface temperatures in °C
    """
    row_min, row_max, col_min, col_max = cavity.bounds
    rows, cols = temp_field.shape
    
    # Hot side (left boundary of cavity)
    if col_min > 0:
        hot_temps = temp_field[row_min:row_max+1, col_min-1]
        T_hot = np.mean(hot_temps)
    else:
        # Cavity at domain edge - use cavity interior temp
        T_hot = np.mean([temp_field[r, c] for r, c in cavity.cells])
    
    # Cold side (right boundary of cavity)
    if col_max < cols - 1:
        cold_temps = temp_field[row_min:row_max+1, col_max+1]
        T_cold = np.mean(cold_temps)
    else:
        T_cold = np.mean([temp_field[r, c] for r, c in cavity.cells])
    
    return float(T_hot), float(T_cold)


def update_cavity_conductivities(
    cond: np.ndarray,
    cavities: List[CavityRegion],
    temp_field: np.ndarray,
    eps_hot: float = 0.9,
    eps_cold: float = 0.9
) -> Tuple[np.ndarray, List[float]]:
    """
    Update conductivity array with new λ_eq values based on temperature field.
    
    Args:
        cond: 2D conductivity array (modified in-place)
        cavities: List of CavityRegion objects
        temp_field: Current temperature solution
        eps_hot: Emissivity of hot (inner) surface
        eps_cold: Emissivity of cold (outer) surface
        
    Returns:
        (updated_cond, lambda_eq_list) - conductivity array and list of new λ_eq values
    """
    lambda_eq_list = []
    
    for cavity in cavities:
        T_hot, T_cold = get_cavity_surface_temperatures(temp_field, cavity)
        
        new_lambda = calculate_lambda_eq(
            d=cavity.d,
            T_hot=T_hot,
            T_cold=T_cold,
            eps_1=eps_hot,
            eps_2=eps_cold,
            b=cavity.b
        )
        
        # Update all cells in this cavity
        for r, c in cavity.cells:
            cond[r, c] = new_lambda
        
        cavity.lambda_eq = new_lambda
        lambda_eq_list.append(new_lambda)
    
    return cond, lambda_eq_list

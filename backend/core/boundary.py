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
Boundary Condition Assembly Module

This module provides functions for assembling boundary conditions in thermal
simulations, including:
- Surface resistance (film coefficient) application per ISO 10211
- Convective boundary condition support via domain padding
- Interface detection between air and solid materials

The goal is to centralize all boundary condition logic that was previously
scattered across run_iso_tests.py and simulation_engine.py.
"""

import numpy as np
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass

from backend.core.geometry import MaterialID


@dataclass
class ConvectiveBoundary:
    """Defines a convective boundary condition for one side of the domain."""
    temperature: float  # Air temperature [°C]
    resistance: float   # Surface thermal resistance [m²K/W]
    

def get_interface_mask(
    grid_map: np.ndarray,
    air_mask: np.ndarray,
    direction: str
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Find interfaces between air cells and solid cells.
    
    Args:
        grid_map: Material ID grid
        air_mask: Boolean mask of air cells (interior or exterior)
        direction: One of 'left', 'right', 'up', 'down'
        
    Returns:
        Tuple of (row_indices, col_indices) for interface links in Gh/Gv
    """
    # Solid = anything that's not AIR_INT or AIR_EXT
    is_solid = (grid_map != MaterialID.AIR_INT) & (grid_map != MaterialID.AIR_EXT)
    
    if direction == 'left':
        # Air at left (j), Solid at right (j+1)
        # Links in Gh at index j
        mask = air_mask[:, :-1] & is_solid[:, 1:]
        return np.where(mask)
    elif direction == 'right':
        # Solid at left (j), Air at right (j+1)
        mask = is_solid[:, :-1] & air_mask[:, 1:]
        return np.where(mask)
    elif direction == 'down':
        # Air below (i), Solid above (i+1)
        mask = air_mask[:-1, :] & is_solid[1:, :]
        return np.where(mask)
    elif direction == 'up':
        # Solid below (i), Air above (i+1)
        mask = is_solid[:-1, :] & air_mask[1:, :]
        return np.where(mask)
    else:
        raise ValueError(f"Unknown direction: {direction}")


def calculate_surface_conductance(
    k_solid: np.ndarray,
    d_solid: np.ndarray,
    R_surface: float,
    area: np.ndarray
) -> np.ndarray:
    """
    Calculate surface conductance for air-solid interface per ISO 10211.
    
    The total thermal resistance at the interface is:
        R_total = R_half_cell + R_surface
        R_half_cell = d/2 / k
        
    Conductance G = Area / R_total
    
    Args:
        k_solid: Thermal conductivity of solid cells [W/(m·K)]
        d_solid: Thickness of solid cells in heat flow direction [m]
        R_surface: Surface thermal resistance [m²K/W]
        area: Cross-sectional area of heat flow [m²]
        
    Returns:
        Conductance array [W/K]
    """
    R_half_cell = d_solid / (2.0 * k_solid)
    R_total = R_half_cell + R_surface
    return area / R_total


def apply_film_coefficients(
    Gh: np.ndarray,
    Gv: np.ndarray,
    grid_map: np.ndarray,
    cond: np.ndarray,
    dx_array: np.ndarray,
    dy_array: np.ndarray,
    surface_resistances: Dict[int, float]
) -> None:
    """
    Apply surface film coefficients (h = 1/R) to conductance matrices.
    
    This modifies Gh and Gv in-place to correctly model the thermal resistance
    at air-solid interfaces according to ISO 10211 methodology.
    
    Args:
        Gh: Horizontal conductance matrix [W/K] - modified in place
        Gv: Vertical conductance matrix [W/K] - modified in place
        grid_map: Material ID grid (ny, nx)
        cond: Thermal conductivity grid [W/(m·K)]
        dx_array: Cell widths in x-direction [mm]
        dy_array: Cell heights in y-direction [mm]
        surface_resistances: Dict mapping MaterialID -> R_surface [m²K/W]
            e.g., {MaterialID.AIR_INT: 0.13, MaterialID.AIR_EXT: 0.04}
    """
    dx_m = dx_array / 1000.0  # Convert to meters
    dy_m = dy_array / 1000.0
    
    for air_material, R_surface in surface_resistances.items():
        air_mask = (grid_map == air_material)
        
        if not np.any(air_mask):
            continue
        
        # --- Horizontal interfaces ---
        
        # Air at left, solid at right
        y_idx, x_idx = get_interface_mask(grid_map, air_mask, 'left')
        if len(y_idx) > 0:
            # Solid is at x_idx + 1
            k_s = cond[y_idx, x_idx + 1]
            dx_s = dx_m[x_idx + 1]
            dy = dy_m[y_idx]
            Gh[y_idx, x_idx] = calculate_surface_conductance(k_s, dx_s, R_surface, dy)
        
        # Solid at left, air at right
        y_idx, x_idx = get_interface_mask(grid_map, air_mask, 'right')
        if len(y_idx) > 0:
            # Solid is at x_idx
            k_s = cond[y_idx, x_idx]
            dx_s = dx_m[x_idx]
            dy = dy_m[y_idx]
            Gh[y_idx, x_idx] = calculate_surface_conductance(k_s, dx_s, R_surface, dy)
        
        # --- Vertical interfaces ---
        
        # Air below, solid above
        y_idx, x_idx = get_interface_mask(grid_map, air_mask, 'down')
        if len(y_idx) > 0:
            # Solid is at y_idx + 1
            k_s = cond[y_idx + 1, x_idx]
            dy_s = dy_m[y_idx + 1]
            dx = dx_m[x_idx]
            Gv[y_idx, x_idx] = calculate_surface_conductance(k_s, dy_s, R_surface, dx)
        
        # Solid above, air below
        y_idx, x_idx = get_interface_mask(grid_map, air_mask, 'up')
        if len(y_idx) > 0:
            # Solid is at y_idx
            k_s = cond[y_idx, x_idx]
            dy_s = dy_m[y_idx]
            dx = dx_m[x_idx]
            Gv[y_idx, x_idx] = calculate_surface_conductance(k_s, dy_s, R_surface, dx)


def pad_domain_for_convective_bc(
    cond: np.ndarray,
    grid_map: np.ndarray,
    dx_array: np.ndarray,
    dy_array: np.ndarray,
    conv_bcs: Dict[str, Dict[str, float]]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, int]:
    """
    Extend domain with air layers for convective boundary conditions.
    
    This implements the ISO 10211 Case 2 methodology where convective boundaries
    are modeled by adding a 1-cell air layer and setting explicit surface 
    conductances.
    
    Args:
        cond: Original conductivity grid (ny, nx)
        grid_map: Original material ID grid (ny, nx)
        dx_array: Original cell widths [mm]
        dy_array: Original cell heights [mm]
        conv_bcs: Dict of convective BCs per side
            e.g., {'bottom': {'T': 20.0, 'R': 0.11}, 'top': {'T': 0.0, 'R': 0.06}}
            
    Returns:
        Tuple of:
        - cond_padded: Extended conductivity grid
        - grid_map_padded: Extended material ID grid
        - dx_array_padded: Extended cell widths
        - dy_array_padded: Extended cell heights
        - y_offset: Row offset for original data
        - x_offset: Column offset for original data
    """
    original_ny, original_nx = cond.shape
    
    pad_top = 'top' in conv_bcs
    pad_bottom = 'bottom' in conv_bcs
    pad_left = 'left' in conv_bcs
    pad_right = 'right' in conv_bcs
    
    # Calculate new dimensions
    ny_new = original_ny + (1 if pad_top else 0) + (1 if pad_bottom else 0)
    nx_new = original_nx + (1 if pad_left else 0) + (1 if pad_right else 0)
    
    # Calculate offsets
    y_off = 1 if pad_bottom else 0
    x_off = 1 if pad_left else 0
    
    # Pad conductivity (air default)
    cond_padded = np.ones((ny_new, nx_new)) * 0.025
    cond_padded[y_off:y_off + original_ny, x_off:x_off + original_nx] = cond
    
    # Pad grid_map
    grid_map_padded = np.full((ny_new, nx_new), MaterialID.AIR_EXT, dtype=int)
    grid_map_padded[y_off:y_off + original_ny, x_off:x_off + original_nx] = grid_map
    
    # Set air material based on temperature (warm = INT, cold = EXT)
    def classify_air(T: float) -> int:
        return MaterialID.AIR_INT if T > 10.0 else MaterialID.AIR_EXT
    
    if pad_bottom:
        T_val = float(conv_bcs['bottom'].get('T', 20.0))
        grid_map_padded[0, :] = classify_air(T_val)
    if pad_top:
        T_val = float(conv_bcs['top'].get('T', 0.0))
        grid_map_padded[-1, :] = classify_air(T_val)
    if pad_left:
        T_val = float(conv_bcs['left'].get('T', 20.0))
        grid_map_padded[:, 0] = classify_air(T_val)
    if pad_right:
        T_val = float(conv_bcs['right'].get('T', 0.0))
        grid_map_padded[:, -1] = classify_air(T_val)
    
    # Pad dx/dy arrays (1mm dummy size for air layers)
    dx_padded = dx_array.copy()
    dy_padded = dy_array.copy()
    
    if pad_left:
        dx_padded = np.insert(dx_padded, 0, 1.0)
    if pad_right:
        dx_padded = np.append(dx_padded, 1.0)
    if pad_bottom:
        dy_padded = np.insert(dy_padded, 0, 1.0)
    if pad_top:
        dy_padded = np.append(dy_padded, 1.0)
    
    return cond_padded, grid_map_padded, dx_padded, dy_padded, y_off, x_off


def apply_convective_boundary_conductances(
    Gh: np.ndarray,
    Gv: np.ndarray,
    dx_array: np.ndarray,
    conv_bcs: Dict[str, Dict[str, float]],
    ny: int
) -> None:
    """
    Set explicit boundary conductances for convective BC layers.
    
    This is called AFTER pad_domain_for_convective_bc and calculates G = A/R
    for the links between the air layer and the first solid layer.
    
    Also disables lateral heat flow in air layers to prevent short circuits.
    
    Args:
        Gh: Horizontal conductance matrix [W/K] - modified in place
        Gv: Vertical conductance matrix [W/K] - modified in place
        dx_array: Cell widths including padding [mm]
        conv_bcs: Dict of convective BCs per side
        ny: Number of rows in the padded domain
    """
    dx_m = dx_array / 1000.0  # Convert to meters
    
    # Bottom boundary
    if 'bottom' in conv_bcs:
        R_bottom = float(conv_bcs['bottom'].get('R', 0.13))
        # Link index 0 connects row 0 (air) and row 1 (surface)
        Gv[0, :] = dx_m / R_bottom
        # Disable lateral flow in air layer
        Gh[0, :] = 0.0
    
    # Top boundary
    if 'top' in conv_bcs:
        R_top = float(conv_bcs['top'].get('R', 0.04))
        # Link at ny-2 connects row (ny-2) and row (ny-1 = top air)
        Gv[ny - 2, :] = dx_m / R_top
        # Disable lateral flow in air layer
        Gh[ny - 1, :] = 0.0
    
    # Left boundary (similar logic for horizontal)
    if 'left' in conv_bcs:
        R_left = float(conv_bcs['left'].get('R', 0.13))
        dy_m = np.ones(ny) * 0.001  # Placeholder, we'd need dy_array
        # For now just disable lateral flow
        Gv[:, 0] = 0.0
    
    # Right boundary
    if 'right' in conv_bcs:
        R_right = float(conv_bcs['right'].get('R', 0.04))
        # Disable lateral flow
        Gv[:, -1] = 0.0


class BoundaryConditionAssembler:
    """
    High-level class for assembling boundary conditions for thermal simulations.
    
    This class provides a unified interface for:
    1. Detecting boundary cells at air-solid interfaces
    2. Applying surface film coefficients (h = 1/R)
    3. Setting up convective boundary conditions via domain padding
    
    Usage:
        assembler = BoundaryConditionAssembler(grid_map, cond, dx_array, dy_array)
        assembler.set_surface_resistances({MaterialID.AIR_INT: 0.13, MaterialID.AIR_EXT: 0.04})
        Gh, Gv = assembler.apply_to_conductances(Gh, Gv)
    """
    
    def __init__(
        self,
        grid_map: np.ndarray,
        cond: np.ndarray,
        dx_array: np.ndarray,
        dy_array: np.ndarray
    ):
        """
        Initialize the assembler with mesh and material data.
        
        Args:
            grid_map: Material ID grid (ny, nx)
            cond: Thermal conductivity grid [W/(m·K)]
            dx_array: Cell widths [mm]
            dy_array: Cell heights [mm]
        """
        self.grid_map = grid_map
        self.cond = cond
        self.dx_array = dx_array
        self.dy_array = dy_array
        self.surface_resistances: Dict[int, float] = {}
        
    def set_surface_resistances(self, resistances: Dict[int, float]) -> 'BoundaryConditionAssembler':
        """
        Set surface thermal resistances for air materials.
        
        Args:
            resistances: Dict mapping MaterialID -> R_surface [m²K/W]
            
        Returns:
            self for method chaining
        """
        self.surface_resistances = resistances
        return self
    
    def apply_to_conductances(
        self,
        Gh: np.ndarray,
        Gv: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply boundary conditions to conductance matrices.
        
        Modifies Gh and Gv in-place to correctly model surface resistances
        at all air-solid interfaces.
        
        Args:
            Gh: Horizontal conductance matrix [W/K]
            Gv: Vertical conductance matrix [W/K]
            
        Returns:
            Tuple of (Gh, Gv) - same objects, modified in place
        """
        if self.surface_resistances:
            apply_film_coefficients(
                Gh, Gv,
                self.grid_map, self.cond,
                self.dx_array, self.dy_array,
                self.surface_resistances
            )
        return Gh, Gv
    
    def detect_interior_boundaries(self) -> np.ndarray:
        """
        Detect cells at the interior (warm) air-solid interface.
        
        Returns:
            Boolean mask of cells adjacent to AIR_INT
        """
        mask_int = (self.grid_map == MaterialID.AIR_INT)
        
        # Find solid cells adjacent to interior air
        is_solid = (self.grid_map != MaterialID.AIR_INT) & (self.grid_map != MaterialID.AIR_EXT)
        
        # Shift mask in all directions
        adj_left = np.zeros_like(is_solid)
        adj_right = np.zeros_like(is_solid)
        adj_up = np.zeros_like(is_solid)
        adj_down = np.zeros_like(is_solid)
        
        adj_left[:, 1:] = mask_int[:, :-1]
        adj_right[:, :-1] = mask_int[:, 1:]
        adj_up[:-1, :] = mask_int[1:, :]
        adj_down[1:, :] = mask_int[:-1, :]
        
        return is_solid & (adj_left | adj_right | adj_up | adj_down)
    
    def detect_exterior_boundaries(self) -> np.ndarray:
        """
        Detect cells at the exterior (cold) air-solid interface.
        
        Returns:
            Boolean mask of cells adjacent to AIR_EXT
        """
        mask_ext = (self.grid_map == MaterialID.AIR_EXT)
        
        is_solid = (self.grid_map != MaterialID.AIR_INT) & (self.grid_map != MaterialID.AIR_EXT)
        
        adj_left = np.zeros_like(is_solid)
        adj_right = np.zeros_like(is_solid)
        adj_up = np.zeros_like(is_solid)
        adj_down = np.zeros_like(is_solid)
        
        adj_left[:, 1:] = mask_ext[:, :-1]
        adj_right[:, :-1] = mask_ext[:, 1:]
        adj_up[:-1, :] = mask_ext[1:, :]
        adj_down[1:, :] = mask_ext[:-1, :]
        
        return is_solid & (adj_left | adj_right | adj_up | adj_down)

"""
Unified Solver Module for Thermal Bridge Calculations

Consolidates all solver logic:
- C++ library loading
- Conductance calculation
- Temperature field solving
- Psi-value / fRsi calculation
- Result plotting
"""

import os
import ctypes
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Optional

from config import TEMP_INT, TEMP_EXT, RSI_WALL, RSE, RSI_CORNER
from geometry import MaterialID

# --- C++ Library Loading ---
SO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "thermal_solver_core.so"))
_lib = None


def get_solver_lib():
    """Load and return the C++ solver library (singleton pattern)."""
    global _lib
    if _lib is not None:
        return _lib
    
    try:
        _lib = ctypes.CDLL(SO_PATH)
        
        # solve_general_conductance signature
        _lib.solve_general_conductance.argtypes = [
            ctypes.POINTER(ctypes.c_double),  # temp (in/out)
            ctypes.POINTER(ctypes.c_double),  # Gh
            ctypes.POINTER(ctypes.c_double),  # Gv
            ctypes.POINTER(ctypes.c_int),     # fixed_mask
            ctypes.POINTER(ctypes.c_double),  # fixed_values
            ctypes.c_int,                     # rows
            ctypes.c_int,                     # cols
            ctypes.c_int,                     # iterations
            ctypes.c_double,                  # omega (SOR)
            ctypes.c_double                   # tol
        ]
        _lib.solve_general_conductance.restype = ctypes.c_double
        
        # Legacy uniform grid solvers (if needed)
        if hasattr(_lib, 'solve_red_black'):
            _lib.solve_red_black.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_double
            ]
            _lib.solve_red_black.restype = ctypes.c_double
            
        print("[INFO] C++ Accelerated Solver Loaded.")
        return _lib
        
    except Exception as e:
        print(f"[ERROR] Failed to load C++ solver: {e}")
        raise


# --- Conductance Calculation ---
def calculate_conductances(cond: np.ndarray, 
                           dx_array: np.ndarray, 
                           dy_array: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate horizontal (Gh) and vertical (Gv) conductance matrices.
    
    Uses harmonic mean for interface conductivity, suitable for variable mesh.
    
    Args:
        cond: 2D array of thermal conductivities [W/(m·K)]
        dx_array: 1D array of cell widths (nx elements) [mm]
        dy_array: 1D array of cell heights (ny elements) [mm]
        
    Returns:
        Tuple of (Gh, Gv) conductance matrices [W/(m·K)]
    """
    # Handle uniform grid case
    if np.isscalar(dx_array) or dx_array.ndim == 0:
        dx_array = np.full(cond.shape[1], float(dx_array))
    if np.isscalar(dy_array) or dy_array.ndim == 0:
        dy_array = np.full(cond.shape[0], float(dy_array))
    
    # Horizontal Conductance (between (i,j) and (i,j+1))
    k_right = np.roll(cond, -1, axis=1)
    k_harm_h = 2 * cond * k_right / (cond + k_right + 1e-12)
    
    dx_dist_h = (dx_array[:-1] + dx_array[1:]) / 2.0
    dx_dist_h = np.append(dx_dist_h, dx_array[-1])
    
    Gh = k_harm_h * dy_array[:, None] / dx_dist_h[None, :]
    
    # Vertical Conductance (between (i,j) and (i+1,j))
    k_down = np.roll(cond, -1, axis=0)
    k_harm_v = 2 * cond * k_down / (cond + k_down + 1e-12)
    
    dy_dist_v = (dy_array[:-1] + dy_array[1:]) / 2.0
    dy_dist_v = np.append(dy_dist_v, dy_array[-1])
    
    Gv = k_harm_v * dx_array[None, :] / dy_dist_v[:, None]
    
    return Gh, Gv


def calculate_conductances_uniform(cond: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simplified conductance calculation for uniform grids.
    
    For uniform dx=dy grids, G = k_harmonic (geometric factors cancel).
    
    Args:
        cond: 2D array of thermal conductivities
        
    Returns:
        Tuple of (Gh, Gv) conductance matrices
    """
    k_right = np.roll(cond, -1, axis=1)
    Gh = 2 * cond * k_right / (cond + k_right + 1e-12)
    
    k_down = np.roll(cond, -1, axis=0)
    Gv = 2 * cond * k_down / (cond + k_down + 1e-12)
    
    return Gh, Gv


# --- Solving ---
def solve(temp: np.ndarray,
          Gh: np.ndarray,
          Gv: np.ndarray,
          fixed_mask: np.ndarray,
          fixed_values: np.ndarray,
          max_iter: int = 100000,
          tol: float = 1e-7,
          omega: float = 1.90,
          batch_size: int = 5000,
          verbose: bool = True) -> np.ndarray:
    """
    Solve the temperature field using C++ accelerated SOR solver.
    
    Args:
        temp: Initial temperature field (modified in place)
        Gh: Horizontal conductance matrix
        Gv: Vertical conductance matrix
        fixed_mask: Boolean mask of fixed temperature nodes
        fixed_values: Fixed temperature values
        max_iter: Maximum iterations
        tol: Convergence tolerance
        omega: SOR relaxation factor (1.85-1.95 typical)
        batch_size: Iterations per batch for progress checking
        verbose: Print progress updates
        
    Returns:
        Solved temperature field
    """
    lib = get_solver_lib()
    
    # Prepare contiguous arrays for C++
    temp_c = np.ascontiguousarray(temp, dtype=np.float64)
    gh_c = np.ascontiguousarray(Gh, dtype=np.float64)
    gv_c = np.ascontiguousarray(Gv, dtype=np.float64)
    mask_c = np.ascontiguousarray(fixed_mask.astype(np.int32))
    val_c = np.ascontiguousarray(fixed_values, dtype=np.float64)
    
    rows, cols = temp.shape
    
    p_temp = temp_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gh = gh_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gv = gv_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_mask = mask_c.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
    p_val = val_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    
    for k in range(0, max_iter, batch_size):
        diff = lib.solve_general_conductance(
            p_temp, p_gh, p_gv, p_mask, p_val,
            rows, cols, batch_size, omega, tol
        )
        
        step = k + batch_size
        if verbose and step % 10000 == 0:
            print(f"  Iteration {step}/{max_iter}: Diff={diff:.2e}")
        
        if diff < tol:
            if verbose:
                print(f"  Converged in {step} iterations (diff={diff:.2e})")
            break
    
    return temp_c


# --- Psi / fRsi Calculation ---
def calculate_thermal_results(temp: np.ndarray,
                               Gh: np.ndarray,
                               Gv: np.ndarray,
                               grid_map: np.ndarray,
                               mask_int: np.ndarray,
                               dx_m: float,
                               rsi: float = RSI_WALL) -> Dict:
    """
    Calculate thermal bridge metrics from solved temperature field.
    
    Args:
        temp: Solved temperature field
        Gh, Gv: Conductance matrices
        grid_map: Material ID grid
        mask_int: Interior air mask
        dx_m: Grid cell size in meters
        rsi: Interior surface resistance for fRsi calculation
        
    Returns:
        Dictionary with L2D, fRsi, MinT values
    """
    # Total flux from interior air
    dt_h = temp[:, :-1] - temp[:, 1:]
    flow_h = Gh[:, :-1] * dt_h
    m_curr = mask_int[:, :-1]
    m_next = mask_int[:, 1:]
    
    flux = np.sum(flow_h[m_curr & (~m_next)]) + np.sum(flow_h[(~m_curr) & m_next])
    
    dt_v = temp[:-1, :] - temp[1:, :]
    flow_v = Gv[:-1, :] * dt_v
    m_curr_v = mask_int[:-1, :]
    m_next_v = mask_int[1:, :]
    
    flux += np.sum(flow_v[m_curr_v & (~m_next_v)]) + np.sum(flow_v[(~m_curr_v) & m_next_v])
    
    l2d = flux / (TEMP_INT - TEMP_EXT)
    
    # Minimum surface temperature
    padded = np.pad(mask_int, 1)
    boundary = (
        (padded[:-2, 1:-1] | padded[2:, 1:-1] | padded[1:-1, :-2] | padded[1:-1, 2:])
        & (~mask_int) 
        & (grid_map != MaterialID.AIR_EXT)
    )
    y, x = np.where(boundary)
    
    min_temp = TEMP_INT
    if len(y) > 0:
        # Get conductivity from nearest solid (approximation)
        # For accurate calculation, use actual material conductivity
        t_node = temp[y, x]
        # Simple approximation: assume k ~ 0.5 for mixed materials
        k_est = 0.5
        r1 = dx_m / (2 * k_est)
        r2 = rsi
        t_si = (TEMP_INT * r1 + t_node * r2) / (r1 + r2)
        min_temp = np.min(t_si)
    
    frsi = (min_temp - TEMP_EXT) / (TEMP_INT - TEMP_EXT)
    
    return {
        'L2D': l2d,
        'fRsi': frsi,
        'MinT': min_temp
    }


# --- Plotting ---
def plot_temperature_map(temp_grid: np.ndarray,
                         width_mm: float,
                         height_mm: float,
                         filename: str,
                         title: str,
                         wall_thick_mm: Optional[float] = None,
                         grid_size_mm: Optional[float] = None,
                         x_coords: Optional[np.ndarray] = None,
                         y_coords: Optional[np.ndarray] = None):
    """
    Plot temperature distribution with isotherm contour lines.
    Supports both uniform (imshow) and adaptive (pcolormesh) grids.
    """
    plt.figure(figsize=(10, 8))
    
    if x_coords is not None and y_coords is not None:
        # Adaptive Mesh: Use pcolormesh
        # x_coords, y_coords are face coordinates (len+1)
        X, Y = np.meshgrid(x_coords, y_coords)
        im = plt.pcolormesh(X, Y, temp_grid, cmap='jet', shading='flat')
    else:
        # Uniform Mesh: Use imshow
        im = plt.imshow(temp_grid, cmap='jet', origin='lower',
                        extent=[0, width_mm, 0, height_mm])
                        
    plt.colorbar(im, label='Temperature [°C]')
    
    # Add isotherms
    min_t = np.min(temp_grid)
    max_t = np.max(temp_grid)
    step = 2.0
    
    if max_t > min_t:
        levels = np.arange(np.ceil(min_t), np.floor(max_t) + 1, step)
        if min_t < 12.6 < max_t:
            levels = np.sort(np.append(levels, 12.6))
        
        if len(levels) > 0:
            if x_coords is not None and y_coords is not None:
                # Contour needs centers for accurate lines, or it can handle X, Y faces?
                # Contour X, Y must match Z shape usually.
                # If Z is (ny, nx), X, Y should be centers (ny, nx) or dimensions.
                xc = (x_coords[:-1] + x_coords[1:]) / 2.0
                yc = (y_coords[:-1] + y_coords[1:]) / 2.0
                X_cen, Y_cen = np.meshgrid(xc, yc)
                CS = plt.contour(X_cen, Y_cen, temp_grid, levels=levels, 
                                 colors='black', linewidths=0.5, alpha=0.7)
            else:
                CS = plt.contour(temp_grid, levels=levels, origin='lower',
                                 extent=[0, width_mm, 0, height_mm],
                                 colors='black', linewidths=0.5, alpha=0.7)
            
            plt.clabel(CS, inline=True, fontsize=8, fmt='%1.1f')
    
    # Title
    full_title = title
    extras = []
    if wall_thick_mm is not None:
        extras.append(f"Thick: {wall_thick_mm}mm")
    if grid_size_mm is not None:
        extras.append(f"Grid: {grid_size_mm}mm")
    if extras:
        full_title += f"\n({', '.join(extras)})"
    
    plt.title(full_title)
    plt.xlabel('Depth [mm]')
    plt.ylabel('Facade Length [mm]')
    
    # Set axis limits to match domain (pcolormesh doesn't auto-set tight??)
    plt.xlim(0, width_mm)
    plt.ylim(0, height_mm)
    
    plt.savefig(filename, dpi=150)
    plt.close()


def plot_geometry(grid_map: np.ndarray,
                  width_mm: float,
                  height_mm: float,
                  filename: str = "geometry_debug.png",
                  x_coords: Optional[np.ndarray] = None,
                  y_coords: Optional[np.ndarray] = None):
    """
    Plot material ID map for geometry verification.
    """
    plt.figure(figsize=(12, 10))
    
    cmap = plt.get_cmap('tab10', 10)
    
    if x_coords is not None and y_coords is not None:
        X, Y = np.meshgrid(x_coords, y_coords)
        im = plt.pcolormesh(X, Y, grid_map, cmap=cmap, shading='flat', vmin=0, vmax=9)
    else:
        im = plt.imshow(grid_map, cmap=cmap, origin='lower',
                        extent=[0, width_mm, 0, height_mm], 
                        interpolation='nearest', vmin=0, vmax=9)
                        
    plt.colorbar(im, label='Material ID')
    plt.title(f'Geometry: {filename}')
    plt.xlabel('Depth [mm]')
    plt.ylabel('Facade Length [mm]')
    
    plt.xlim(0, width_mm)
    plt.ylim(0, height_mm)
    
    plt.grid(True, color='white', alpha=0.3)
    plt.savefig(filename, dpi=150)
    plt.close()

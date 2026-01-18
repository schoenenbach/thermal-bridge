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
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
from typing import Tuple, Dict, Optional, Union, BinaryIO

from backend.core.config import TEMP_INT, TEMP_EXT, RSI_WALL, RSE, RSI_CORNER
from backend.core.geometry import MaterialID

# --- C++ Library Loading ---
SO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "solver", "thermal_solver_core.so"))
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
    # Series resistance: R_tot = R_left + R_right = (dx_L/2)/(k_L*dy) + (dx_R/2)/(k_R*dy)
    # G = 1/R_tot = (2*dy) / (dx_L/k_L + dx_R/k_R)
    
    k_curr = cond
    k_right = np.roll(cond, -1, axis=1)
    
    dx_curr = dx_array # (nx,)
    dx_right = np.roll(dx_array, -1)
    
    # Broadcast dx to 2D
    dx_curr_2d = dx_curr[None, :]
    dx_right_2d = dx_right[None, :]
    
    # Denominator term: (dx_L/k_L + dx_R/k_R)
    # Add epsilon to k to avoid div by zero (though k shouldn't be 0)
    denom_h = (dx_curr_2d / (k_curr + 1e-12)) + (dx_right_2d / (k_right + 1e-12))
    
    Gh = (2 * dy_array[:, None]) / (denom_h + 1e-12)

    # Vertical Conductance (between (i,j) and (i+1,j))
    # Series resistance: R_tot = R_up + R_down = (dy_U/2)/(k_U*dx) + (dy_D/2)/(k_D*dx)
    # G = 1/R_tot = (2*dx) / (dy_U/k_U + dy_D/k_D)
    
    k_down = np.roll(cond, -1, axis=0)
    
    dy_curr = dy_array # (ny,)
    dy_down = np.roll(dy_array, -1)
    
    dy_curr_2d = dy_curr[:, None]
    dy_down_2d = dy_down[:, None]
    
    denom_v = (dy_curr_2d / (k_curr + 1e-12)) + (dy_down_2d / (k_down + 1e-12))
    
    Gv = (2 * dx_array[None, :]) / (denom_v + 1e-12)
    
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


# --- Sparse Matrix Assembly ---
from scipy import sparse
from scipy.sparse.linalg import spsolve


def build_sparse_system(Gh: np.ndarray, 
                        Gv: np.ndarray, 
                        fixed_mask: np.ndarray, 
                        fixed_values: np.ndarray) -> Tuple[sparse.csr_matrix, np.ndarray]:
    """
    Build sparse matrix system Ax = b for steady-state heat equation.
    
    The discretized equation for node (i,j) is:
        Sum(G_neighbor * (T_neighbor - T_ij)) = 0
    
    Rearranging:
        T_ij * Sum(G_neighbors) = Sum(G_neighbor * T_neighbor)
    
    For Dirichlet (fixed) nodes: row is identity, RHS is fixed value.
    
    Args:
        Gh: Horizontal conductance matrix (i,j) -> (i,j+1)
        Gv: Vertical conductance matrix (i,j) -> (i+1,j)
        fixed_mask: Boolean mask of fixed temperature nodes
        fixed_values: Fixed temperature values
        
    Returns:
        Tuple of (A, b) where A is sparse CSR matrix, b is RHS vector
    """
    rows, cols = Gh.shape
    n = rows * cols
    
    # Prepare sparse matrix entries using COO format
    row_idx = []
    col_idx = []
    data = []
    
    b = np.zeros(n)
    
    def idx(r, c):
        return r * cols + c
    
    for r in range(rows):
        for c in range(cols):
            i = idx(r, c)
            
            if fixed_mask[r, c]:
                # Dirichlet condition: T_i = fixed_value
                row_idx.append(i)
                col_idx.append(i)
                data.append(1.0)
                b[i] = fixed_values[r, c]
            else:
                # Interior/adiabatic node: balance equation
                # Collect conductances to neighbors
                g_sum = 0.0
                
                # Left neighbor (c-1)
                if c > 0:
                    g_left = Gh[r, c-1]  # Conductance from (r,c-1) to (r,c)
                    g_sum += g_left
                    row_idx.append(i)
                    col_idx.append(idx(r, c-1))
                    data.append(-g_left)
                
                # Right neighbor (c+1)
                if c < cols - 1:
                    g_right = Gh[r, c]  # Conductance from (r,c) to (r,c+1)
                    g_sum += g_right
                    row_idx.append(i)
                    col_idx.append(idx(r, c+1))
                    data.append(-g_right)
                
                # Bottom neighbor (r-1)
                if r > 0:
                    g_bottom = Gv[r-1, c]  # Conductance from (r-1,c) to (r,c)
                    g_sum += g_bottom
                    row_idx.append(i)
                    col_idx.append(idx(r-1, c))
                    data.append(-g_bottom)
                
                # Top neighbor (r+1)
                if r < rows - 1:
                    g_top = Gv[r, c]  # Conductance from (r,c) to (r+1,c)
                    g_sum += g_top
                    row_idx.append(i)
                    col_idx.append(idx(r+1, c))
                    data.append(-g_top)
                
                # Diagonal entry (sum of conductances)
                row_idx.append(i)
                col_idx.append(i)
                data.append(g_sum if g_sum > 0 else 1.0)  # Avoid zero diagonal
                
                b[i] = 0.0
    
    # Build sparse matrix in COO format, then convert to CSR for efficient solving
    A = sparse.coo_matrix((data, (row_idx, col_idx)), shape=(n, n)).tocsr()
    
    return A, b


def solve_sparse(Gh: np.ndarray,
                 Gv: np.ndarray,
                 fixed_mask: np.ndarray,
                 fixed_values: np.ndarray,
                 verbose: bool = True) -> np.ndarray:
    """
    Solve steady-state heat equation using sparse direct solver (spsolve).
    
    This is faster and more robust than iterative SOR for stiff systems.
    
    Args:
        Gh: Horizontal conductance matrix
        Gv: Vertical conductance matrix
        fixed_mask: Boolean mask of fixed temperature nodes
        fixed_values: Fixed temperature values
        verbose: Print timing info
        
    Returns:
        2D temperature field
    """
    import time
    
    rows, cols = Gh.shape
    
    if verbose:
        print(f"  Building sparse system ({rows}x{cols} = {rows*cols} nodes)...")
    
    t0 = time.perf_counter()
    A, b = build_sparse_system(Gh, Gv, fixed_mask, fixed_values)
    t_build = time.perf_counter() - t0
    
    if verbose:
        print(f"  Matrix assembly: {t_build*1000:.1f}ms, nnz={A.nnz}")
    
    t0 = time.perf_counter()
    T_flat = spsolve(A, b)
    t_solve = time.perf_counter() - t0
    
    if verbose:
        print(f"  Direct solve: {t_solve*1000:.1f}ms")
    
    return T_flat.reshape(rows, cols)


def solve_with_cavity_iteration(
    cond: np.ndarray,
    grid_map: np.ndarray,
    dx_m: float,
    dy_m: float,
    fixed_mask: np.ndarray,
    fixed_values: np.ndarray,
    cavity_material_id: int = 8,
    max_cavity_iterations: int = 10,
    cavity_tol: float = 0.01,
    eps_hot: float = 0.9,
    eps_cold: float = 0.9,
    verbose: bool = True
) -> Tuple[np.ndarray, list]:
    """
    Solve with iterative λ_eq recalculation for air cavities per ISO 10077-2.
    
    The solver performs the following iteration:
    1. Detect all cavity regions via flood-fill
    2. Solve temperature field with current λ_eq values
    3. Calculate new λ_eq from surface temperatures for each cavity
    4. Update conductivity array with new λ_eq
    5. Repeat 2-4 until max surface temperature change < cavity_tol
    
    Args:
        cond: Initial conductivity array (will be modified)
        grid_map: Material ID array
        dx_m: Grid cell width (m)
        dy_m: Grid cell height (m)
        fixed_mask: Boolean mask of fixed temperature nodes
        fixed_values: Fixed temperature values
        cavity_material_id: Material ID for cavity cells (default: 8 = CAVITY)
        max_cavity_iterations: Maximum outer iterations (default: 10)
        cavity_tol: Convergence tolerance for temperature change (K)
        eps_hot: Emissivity of hot (interior) cavity surface
        eps_cold: Emissivity of cold (exterior) cavity surface
        verbose: Print iteration progress
        
    Returns:
        Tuple of (temperature_field, lambda_eq_history) where lambda_eq_history
        is a list of λ_eq values per iteration for each cavity
    """
    from backend.core.cavity import (
        detect_cavities,
        update_cavity_conductivities,
        get_cavity_surface_temperatures
    )
    
    # Detect cavities
    cavities = detect_cavities(grid_map, dx_m, dy_m, cavity_material_id)
    
    if not cavities:
        if verbose:
            print("[cavity] No cavities detected, using standard solve")
        Gh, Gv = calculate_conductances(cond, 
                                        np.full(cond.shape[1], dx_m * 1000),  # Convert to mm
                                        np.full(cond.shape[0], dy_m * 1000))
        temp = solve_sparse(Gh, Gv, fixed_mask, fixed_values, verbose=verbose)
        return temp, []
    
    if verbose:
        print(f"[cavity] Detected {len(cavities)} cavity region(s)")
        for i, cav in enumerate(cavities):
            print(f"  Cavity {i+1}: d={cav.d*1000:.1f}mm, b={cav.b*1000:.1f}mm, cells={len(cav.cells)}")
    
    lambda_history = []
    temp_prev = None
    
    for iteration in range(max_cavity_iterations):
        # Calculate conductances with current λ values
        dx_mm = np.full(cond.shape[1], dx_m * 1000)
        dy_mm = np.full(cond.shape[0], dy_m * 1000)
        Gh, Gv = calculate_conductances(cond, dx_mm, dy_mm)
        
        # Solve temperature field
        temp = solve_sparse(Gh, Gv, fixed_mask, fixed_values, verbose=False)
        
        # Update cavity conductivities based on new temperatures
        cond, lambda_list = update_cavity_conductivities(
            cond, cavities, temp, eps_hot, eps_cold
        )
        lambda_history.append(lambda_list)
        
        if verbose:
            lambda_str = ", ".join([f"{l:.4f}" for l in lambda_list])
            print(f"  Iter {iteration+1}: λ_eq = [{lambda_str}] W/mK")
        
        # Check convergence (max temperature change)
        if temp_prev is not None:
            max_delta_T = np.max(np.abs(temp - temp_prev))
            if verbose:
                print(f"    ΔT_max = {max_delta_T:.4f}K")
            if max_delta_T < cavity_tol:
                if verbose:
                    print(f"[cavity] Converged in {iteration+1} iterations")
                break
        
        temp_prev = temp.copy()
    else:
        if verbose:
            print(f"[cavity] Warning: Did not converge in {max_cavity_iterations} iterations")
    
    return temp, lambda_history


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
          verbose: bool = True,
          progress_callback=None,
          backend: str = "sparse") -> np.ndarray:
    """
    Solve the temperature field for steady-state heat conduction.
    
    Args:
        temp: Initial temperature field (used as initial guess for SOR, ignored for sparse)
        Gh: Horizontal conductance matrix
        Gv: Vertical conductance matrix
        fixed_mask: Boolean mask of fixed temperature nodes
        fixed_values: Fixed temperature values
        max_iter: Maximum iterations (SOR only)
        tol: Convergence tolerance (SOR only)
        omega: SOR relaxation factor 1.85-1.95 typical (SOR only)
        batch_size: Iterations per batch for progress checking (SOR only)
        verbose: Print progress updates
        progress_callback: Optional callable(step, max_iter, diff) (SOR only)
        backend: Solver backend - "sparse" (default, direct solve) or "sor" (legacy iterative)
        
    Returns:
        Solved temperature field
    """
    # Use sparse direct solver by default
    if backend == "sparse":
        return solve_sparse(Gh, Gv, fixed_mask, fixed_values, verbose=verbose)
    
    # Legacy SOR solver path
    if backend != "sor":
        import warnings
        warnings.warn(f"Unknown backend '{backend}', falling back to 'sor'")
    
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
            
        if progress_callback:
            progress_callback(step, max_iter, diff)
        
        if diff < tol:
            if verbose:
                print(f"  Converged in {step} iterations (diff={diff:.2e})")
            break
    

    return temp_c


def solve_transient(temp_current: np.ndarray,
                    temp_prev: np.ndarray,
                    Gh: np.ndarray,
                    Gv: np.ndarray,
                    capacitance: np.ndarray,
                    fixed_mask: np.ndarray,
                    fixed_values: np.ndarray,
                    dt: float,
                    steps: int = 1,
                    max_iter: int = 100,
                    tol: float = 1e-4,
                    omega: float = 1.0) -> np.ndarray:
    """
    Solve for the next time step(s) using Implicit Euler.
    
    Args:
        temp_current: Current temperature field (initial guess for new step)
        temp_prev: Temperature field at previous time step
        Gh, Gv: Conductance matrices
        capacitance: Node heat capacity [J/K]
        fixed_mask: Fixed node mask
        fixed_values: Fixed node values
        dt: Time step [s]
        steps: Number of time steps to perform (usually 1)
        max_iter: Max SOR iterations per step
        tol: Convergence tolerance
        omega: SOR relaxation factor
        
    Returns:
        Updated temperature field (new time step)
    """
    lib = get_solver_lib()
    
    # Prepare types
    temp_sol_c = np.ascontiguousarray(temp_current, dtype=np.float64)
    temp_prev_c = np.ascontiguousarray(temp_prev, dtype=np.float64)
    gh_c = np.ascontiguousarray(Gh, dtype=np.float64)
    gv_c = np.ascontiguousarray(Gv, dtype=np.float64)
    cap_c = np.ascontiguousarray(capacitance, dtype=np.float64)
    mask_c = np.ascontiguousarray(fixed_mask.astype(np.int32))
    val_c = np.ascontiguousarray(fixed_values, dtype=np.float64)
    
    rows, cols = temp_current.shape
    
    p_temp = temp_sol_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_prev = temp_prev_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gh = gh_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_gv = gv_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_cap = cap_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_mask = mask_c.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
    p_val = val_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))

    # Note: solve_transient_step signature:
    # double solve_transient_step(double *temp_sol, const double *temp_prev,
    #                             const double *cond_h, const double *cond_v,
    #                             const double *capacitance, const int *fixed_mask,
    #                             const double *fixed_values, int rows, int cols,
    #                             int iterations, double dt, double omega)
    
    if not hasattr(lib, 'solve_transient_step'):
         # Bind it if not done
         lib.solve_transient_step.argtypes = [
            ctypes.POINTER(ctypes.c_double), # temp_sol
            ctypes.POINTER(ctypes.c_double), # temp_prev
            ctypes.POINTER(ctypes.c_double), # Gh
            ctypes.POINTER(ctypes.c_double), # Gv
            ctypes.POINTER(ctypes.c_double), # Cap
            ctypes.POINTER(ctypes.c_int),    # Mask
            ctypes.POINTER(ctypes.c_double), # Values
            ctypes.c_int, ctypes.c_int,      # rows, cols
            ctypes.c_int,                    # iterations
            ctypes.c_double,                 # dt
            ctypes.c_double                  # omega
         ]
         lib.solve_transient_step.restype = ctypes.c_double

    # Perform time steps
    # Note: For multiple steps, we would need to ping-pong buffers. 
    # For now, we assume 1 step at a time is managed by the caller, 
    # OR we update temp_prev internally if steps > 1 (not implemented for simplicity)
    
    diff = lib.solve_transient_step(
        p_temp, p_prev, p_gh, p_gv, p_cap, p_mask, p_val,
        ctypes.c_int(rows), ctypes.c_int(cols), ctypes.c_int(max_iter), 
        ctypes.c_double(dt), ctypes.c_double(omega)
    )
    
    return temp_sol_c


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
                         filename: Union[str, BinaryIO, None],
                         title: str,
                         wall_thick_mm: Optional[float] = None,
                         grid_size_mm: Optional[float] = None,
                         x_coords: Optional[np.ndarray] = None,
                         y_coords: Optional[np.ndarray] = None):
    """
    Plot temperature distribution with isotherm contour lines.
    Supports both uniform (imshow) and adaptive (pcolormesh) grids.
    
    If filename is None, returns a BytesIO buffer containing the PNG.
    If filename is str, saves to that path and returns filename.
    If filename is a file-like object, saves to it and returns it.
    """
    plt.figure(figsize=(10, 8))
    
    if x_coords is not None and y_coords is not None:
        # Adaptive Mesh: Use pcolormesh
        # x_coords, y_coords are face coordinates (len+1)
        X, Y = np.meshgrid(x_coords, y_coords)
        im = plt.pcolormesh(X, Y, temp_grid, cmap='jet', shading='flat')
    else:
        # Uniform Mesh: Use imshow
        # We need to correctly set extent if coordinates are shifted
        x_min, y_min = 0, 0
        if x_coords is not None and y_coords is not None:
             x_min, y_min = x_coords[0], y_coords[0]
             
        im = plt.imshow(temp_grid, cmap='jet', origin='lower',
                        extent=[x_min, x_min + width_mm, y_min, y_min + height_mm])
                        
    plt.colorbar(im, label='Temperature [°C]')
    
    # Add isotherms
    min_t = np.min(temp_grid)
    max_t = np.max(temp_grid)
    step = 2.0
    
    def add_boundary_labels(cs):
        for i, level in enumerate(cs.levels):
            # In newer matplotlib, collections might be different, but this is traditional
            # Use allsegs to get vertices directly (works in older and newer MPL)
            segments = cs.allsegs[i] 
            for v in segments:
                if len(v) < 2: continue
                # Find all boundary intersections for this path
                boundary_pts = []
                for pt in [v[0], v[-1]]:
                    x, y = pt
                    on_bottom = abs(y - yc[0]) < 0.5
                    on_left = abs(x - xc[0]) < 0.5
                    on_right = abs(x - xc[-1]) < 0.5
                    on_top = abs(y - yc[-1]) < 0.5
                    
                    if on_bottom: boundary_pts.append((x, y, 'bottom'))
                    if on_left: boundary_pts.append((x, y, 'left'))
                    if on_right: boundary_pts.append((x, y, 'right'))
                    if on_top: boundary_pts.append((x, y, 'top'))
                
                if not boundary_pts:
                    continue
                
                # Heuristic for "most space": 
                # Prioritize Left and Bottom as they usually converge less in this geometry.
                # If both ends hit boundaries, prefer the one on Left or Bottom.
                best_pt = None
                for pt in boundary_pts:
                    if pt[2] in ['left', 'bottom']:
                        best_pt = pt
                        break
                if not best_pt:
                    best_pt = boundary_pts[0]
                
                x, y, side = best_pt
                
                # Position label INSIDE the plot to avoid axis conflict
                # Use a small offset proportional to domain size
                off_x = width_mm * 0.015
                off_y = height_mm * 0.015
                
                dx, dy = 0, 0
                ha, va = 'center', 'center'
                
                if side == 'bottom':
                    dy, va = off_y, 'bottom'
                elif side == 'left':
                    dx, ha = off_x, 'left'
                elif side == 'right':
                    dx, ha = -off_x, 'right'
                elif side == 'top':
                    dy, va = -off_y, 'top'
                
                plt.annotate(f"{level:.1f}°C", (x, y), 
                             xytext=(dx, dy), textcoords='offset points',
                             fontsize=7, color='black', fontweight='normal',
                             ha=ha, va=va, alpha=0.9, clip_on=True,
                             bbox=dict(boxstyle='round,pad=0.1', fc='white', ec='none', alpha=0.6))

    if max_t > min_t:
        # Regular levels (excluding 12.6)
        levels = np.arange(np.ceil(min_t), np.floor(max_t) + 1, step)
        levels = levels[np.abs(levels - 12.6) > 0.05]
        
        if len(levels) > 0 or (min_t < 12.6 < max_t):
            # Setup coordinates for contour
            if x_coords is not None and y_coords is not None:
                xc = (x_coords[:-1] + x_coords[1:]) / 2.0
                yc = (y_coords[:-1] + y_coords[1:]) / 2.0
                X_cen, Y_cen = np.meshgrid(xc, yc)
            else:
                xc = np.linspace(0, width_mm, temp_grid.shape[1])
                yc = np.linspace(0, height_mm, temp_grid.shape[0])
                X_cen, Y_cen = np.meshgrid(xc, yc)

            # 1. Plot regular isotherms
            if len(levels) > 0:
                CS = plt.contour(X_cen, Y_cen, temp_grid, levels=levels, 
                                 colors='black', linewidths=0.5, alpha=0.6, linestyles='solid')
                add_boundary_labels(CS)
            
            # 2. Plot critical 12.6 isotherm
            if min_t < 12.6 < max_t:
                CS126 = plt.contour(X_cen, Y_cen, temp_grid, levels=[12.6], 
                                    colors='black', linewidths=0.8, alpha=0.8, linestyles='dashed')
                add_boundary_labels(CS126)
    
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
    # Set axis limits to match domain
    if x_coords is not None and y_coords is not None:
        plt.xlim(x_coords[0], x_coords[-1])
        plt.ylim(y_coords[0], y_coords[-1])
    else:
        plt.xlim(0, width_mm)
        plt.ylim(0, height_mm)
    
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
        # Assume file-like
        plt.savefig(filename, dpi=150)
        plt.close()
        return filename


def plot_geometry(grid_map: np.ndarray,
                  width_mm: float,
                  height_mm: float,
                  filename: Union[str, BinaryIO, None] = "geometry_debug.png",
                  x_coords: Optional[np.ndarray] = None,
                  y_coords: Optional[np.ndarray] = None,
                  equal_aspect: bool = False,
                  highlight_bbox: Optional[Tuple[float, float, float, float]] = None,
                  material_names: Optional[Dict[int, str]] = None,
                  material_colors: Optional[Dict[int, str]] = None):
    """
    Plot material ID map for geometry verification.
    
    Args:
        grid_map: Material ID grid
        width_mm: Domain width in mm
        height_mm: Domain height in mm
        filename: Output filename
        x_coords: X face coordinates (for adaptive mesh)
        y_coords: Y face coordinates (for adaptive mesh)
        equal_aspect: If True, use equal aspect ratio (shows true proportions)
        highlight_bbox: Optional bounding box to highlight (x, y, w, h)
        material_names: Optional mapping of material ID to name for legend
        material_colors: Optional mapping of material ID to hex color string
    """
    # Adjust figure size based on aspect ratio
    aspect = width_mm / height_mm
    if equal_aspect:
        fig_width = 12
        fig_height = max(3, fig_width / aspect)  # Minimum height for readability
    else:
        fig_width, fig_height = 12, 10
    
    plt.figure(figsize=(fig_width, fig_height))
    
    # Derive color range from actual material IDs
    unique_mats = np.unique(grid_map)
    n_materials = len(unique_mats)
    
    # Construct a custom colormap that matches the unique materials in order
    from matplotlib.colors import ListedColormap
    
    # Default fallback palette
    fallback_cmap = plt.get_cmap('tab20' if n_materials > 10 else 'tab10', max(n_materials, 10))
    
    color_list = []
    for i, m_id in enumerate(unique_mats):
        if material_colors and m_id in material_colors:
            color_list.append(material_colors[m_id])
        else:
            # Fallback to standard palette
            color_list.append(fallback_cmap(i))
            
    cmap = ListedColormap(color_list)
    
    # Create normalized version for proper coloring
    # Map unique materials to sequential indices 0..N-1
    mat_to_idx = {m: i for i, m in enumerate(unique_mats)}
    grid_normalized = np.vectorize(lambda x: mat_to_idx[x])(grid_map)
    
    if x_coords is not None and y_coords is not None:
        X, Y = np.meshgrid(x_coords, y_coords)
        # vmin/vmax range matches 0..N-1 indices
        im = plt.pcolormesh(X, Y, grid_normalized, cmap=cmap, shading='flat', 
                           vmin=0, vmax=n_materials-1)
        
        # Set limits based on coords
        plt.xlim(x_coords[0], x_coords[-1])
        plt.ylim(y_coords[0], y_coords[-1])
    else:
        im = plt.imshow(grid_normalized, cmap=cmap, origin='lower',
                        extent=[0, width_mm, 0, height_mm], 
                        interpolation='nearest', vmin=0, vmax=n_materials-1)
        # Default limits
        plt.xlim(0, width_mm)
        plt.ylim(0, height_mm)
    
    # Create patches for legend instead of colorbar for clear categorical labeling
    from matplotlib.patches import Patch
    
    legend_handles = []
    
    # Helper to clean up labels
    def get_label(m_id):
        if material_names and m_id in material_names:
            return material_names[m_id]
        return str(m_id)

    # For each material index (0..N-1), use the explicit color from our list
    for i, m_id in enumerate(unique_mats):
        color = color_list[i]
        label = get_label(int(m_id))
        legend_handles.append(Patch(color=color, label=label))
    
    # Place legend outside: upper left anchored to the right of the plot
    plt.legend(handles=legend_handles, bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., title="Materials")
    
    if equal_aspect:
        plt.gca().set_aspect('equal', adjustable='box')
                        
    plt.title(f'Geometry: {filename}')
    plt.xlabel('Depth [mm]')
    plt.ylabel('Facade Length [mm]')
    
    # Draw highlight box if specified
    if highlight_bbox is not None:
        from matplotlib.patches import Rectangle
        ax = plt.gca()
        x, y, w, h = highlight_bbox
        rect = Rectangle((x, y), w, h, linewidth=2.5, 
                          edgecolor='red', facecolor='none', linestyle='--')
        ax.add_patch(rect)
    
    plt.grid(True, color='white', alpha=0.3)
    
    # Adjust layout to accommodate external legend
    plt.tight_layout()
    # Adjust layout to accommodate external legend
    plt.tight_layout()
    
    if filename is None:
        buf = BytesIO()
        plt.savefig(buf, dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf
    elif isinstance(filename, str):
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        return filename
    else:
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        return filename

#include <algorithm>
#include <cmath>
#include <omp.h>
#include <vector>

// Build command:
// g++ -O3 -shared -fPIC -fopenmp thermal_solver_core.cpp -o
// thermal_solver_core.so

extern "C" {

/**
 * Performs multiple iterations of the Jacobi solver for the steady-state heat
 * equation.
 *
 * @param temp Pointer to the temperature grid (flattened 2D array, row-major)
 * @param cond Pointer to the conductivity grid (flattened 2D array, row-major)
 * @param rows Number of rows (NY)
 * @param cols Number of columns (NX)
 * @param iterations Number of iterations to perform in this call
 * @return Max temperature difference in the last iteration (for convergence
 * checking)
 */
double solve_step(double *temp, const double *cond, int rows, int cols,
                  int iterations) {

  // We need double buffering for Jacobi
  // However, allocating memory on every call is slow.
  // Better if the caller provides the buffer, but for now specific alloc is
  // safer. Actually, we can just use a local vector.
  std::vector<double> temp_new(rows * cols);

  double max_diff = 0.0;

  // Helper lambda for harmonic mean
  auto harm = [](double k1, double k2) {
    return 2.0 * k1 * k2 / (k1 + k2 + 1e-12);
  };

  for (int iter = 0; iter < iterations; ++iter) {
    max_diff = 0.0;

#pragma omp parallel for reduction(max : max_diff)
    for (int r = 1; r < rows - 1; ++r) {
      for (int c = 1; c < cols - 1; ++c) {
        int idx = r * cols + c;

        int idx_up = (r - 1) * cols + c;
        int idx_dn = (r + 1) * cols + c;
        int idx_lf = r * cols + (c - 1);
        int idx_rt = r * cols + (c + 1);

        double tc = temp[idx];
        double kc = cond[idx];

        double g_up = harm(kc, cond[idx_up]);
        double g_dn = harm(kc, cond[idx_dn]);
        double g_lf = harm(kc, cond[idx_lf]);
        double g_rt = harm(kc, cond[idx_rt]);

        double g_sum = g_up + g_dn + g_lf + g_rt;

        double ft_up = g_up * temp[idx_up];
        double ft_dn = g_dn * temp[idx_dn];
        double ft_lf = g_lf * temp[idx_lf];
        double ft_rt = g_rt * temp[idx_rt];

        double t_new_val = (ft_up + ft_dn + ft_lf + ft_rt) / (g_sum + 1e-12);

        temp_new[idx] = t_new_val;

        double diff = std::abs(t_new_val - tc);
        if (diff > max_diff) {
          max_diff = diff;
        }
      }
    }

    // Boundary Conditions (Naive copy for now, caller handles sophisticated BCs
    // or we do it here) Python code does:
    // 1. Adiabatic Top/Bottom/Left
    // 2. Dirichlet (Air)
    // The Python code applies BCs *after* the update.
    // But we need to update the `temp` array with `temp_new` values for the
    // inner nodes. AND we need to preserve the fixed values (Dirichlet).
    // Actually, the Python code updates *everything* and then resets the Air
    // nodes. To match Python logic EXACTLY without passing mask: passing mask
    // is better.

    // Wait, simply updating the inner nodes 1..N-1 is what we did above.
    // But we need to write back to `temp`.

#pragma omp parallel for
    for (int r = 1; r < rows - 1; ++r) {
      for (int c = 1; c < cols - 1; ++c) {
        int idx = r * cols + c;
        temp[idx] = temp_new[idx];
      }
    }

    // Apply Adiabatic Boundaries (Top, Bottom, Left)
    // Top (Row = rows-1) = Row below
    // Bottom (Row = 0) = Row above
    // Left (Col = 0) = Col right

    // Note: Parallelizing tiny loops might be overhead, do serial

    // Left (c=0)
    for (int r = 0; r < rows; ++r) {
      temp[r * cols + 0] = temp[r * cols + 1]; // Adiabatic
    }

    // Bottom (r=0)
    for (int c = 0; c < cols; ++c) {
      temp[0 * cols + c] = temp[1 * cols + c];
    }

    // Top (r=rows-1)
    for (int c = 0; c < cols; ++c) {
      temp[(rows - 1) * cols + c] = temp[(rows - 2) * cols + c];
    }

    // Note: We are NOT handling the "Reset Air to Fixed Temp" here because we
    // don't have the mask. If we don't do it, the "Air" temperature will drift.
    // But conductivities in Air are set.
    // In Python:
    // t_new[mask_int] = TEMP_INT
    // t_new[mask_ext] = TEMP_EXT
    // Effectively, these are Dirichlet conditions.
    // If we don't enforce them, they become floating nodes with K=K_air.
    // The Python solver ENFORCES them every step.
    // We need to pass the mask or the original temps to reset?
    // Actually, if K is correct, it diffuses. But Python forces it.
    // Let's rely on the Python side to reset boundaries?
    // No, that would require crossing the language barrier every iteration. Too
    // slow. We MUST handle Dirichlet boundaries in C++.
  }
  return max_diff;
}

/**
 * Optimized solver that handles Dirichlet boundaries internally
 *
 * @param temp Pointer to temperature grid (Input/Output)
 * @param cond Pointer to conductivity grid
 * @param fixed_mask Pointer to integer mask (1 = Fixed/Dirichlet, 0 = Variable)
 * @param fixed_values Pointer to values to enforce where mask is 1
 *
 */
double solve_optimized(double *temp, const double *cond, const int *fixed_mask,
                       const double *fixed_values, int rows, int cols,
                       int iterations) {
  std::vector<double> temp_new(rows * cols);
  double max_diff = 0.0;

  auto harm = [](double k1, double k2) {
    return 2.0 * k1 * k2 / (k1 + k2 + 1e-12);
  };

  for (int iter = 0; iter < iterations; ++iter) {
    max_diff = 0.0;

// Update Inner Nodes
#pragma omp parallel for reduction(max : max_diff)
    for (int r = 1; r < rows - 1; ++r) {
      for (int c = 1; c < cols - 1; ++c) {
        int idx = r * cols + c;

        // Skip if fixed
        if (fixed_mask[idx]) {
          // Ensure it keeps its value (optional, but good for consistency)
          // temp_new[idx] = fixed_values[idx];
          continue;
        }

        int idx_up = (r - 1) * cols + c;
        int idx_dn = (r + 1) * cols + c;
        int idx_lf = r * cols + (c - 1);
        int idx_rt = r * cols + (c + 1);

        double kc = cond[idx];
        double g_up = harm(kc, cond[idx_up]);
        double g_dn = harm(kc, cond[idx_dn]);
        double g_lf = harm(kc, cond[idx_lf]);
        double g_rt = harm(kc, cond[idx_rt]);
        double g_sum = g_up + g_dn + g_lf + g_rt;

        double val = (g_up * temp[idx_up] + g_dn * temp[idx_dn] +
                      g_lf * temp[idx_lf] + g_rt * temp[idx_rt]) /
                     (g_sum + 1e-12);

        temp_new[idx] = val;

        double diff = std::abs(val - temp[idx]);
        if (diff > max_diff)
          max_diff = diff;
      }
    }

    // Write Back & Apply BCs
    // Parallel write back for inner nodes
#pragma omp parallel for
    for (int r = 1; r < rows - 1; ++r) {
      for (int c = 1; c < cols - 1; ++c) {
        int idx = r * cols + c;
        if (!fixed_mask[idx]) {
          temp[idx] = temp_new[idx];
        } else {
          temp[idx] = fixed_values[idx]; // Enforce Dirichlet
        }
      }
    }

    // Apply Boundaries strictly

    // Left (c=0)
    for (int r = 0; r < rows; ++r) {
      int idx = r * cols + 0;
      if (!fixed_mask[idx])
        temp[idx] = temp[r * cols + 1]; // Adiabatic
      else
        temp[idx] = fixed_values[idx];
    }

    // Right (c=cols-1)
    for (int r = 0; r < rows; ++r) {
      int idx = r * cols + (cols - 1);
      if (!fixed_mask[idx])
        temp[idx] = temp[r * cols + (cols - 2)]; // Adiabatic
      else
        temp[idx] = fixed_values[idx];
    }

    // Bottom (r=0)
    for (int c = 0; c < cols; ++c) {
      int idx = 0 * cols + c;
      if (!fixed_mask[idx])
        temp[idx] = temp[1 * cols + c]; // Adiabatic
      else
        temp[idx] = fixed_values[idx];
    }

    // Top (r=rows-1)
    for (int c = 0; c < cols; ++c) {
      int idx = (rows - 1) * cols + c;
      if (!fixed_mask[idx])
        temp[idx] = temp[(rows - 2) * cols + c]; // Adiabatic
      else
        temp[idx] = fixed_values[idx];
    }
  }
  return max_diff;
}

/**
 * Red-Black Gauss-Seidel Solver with SOR (Successive Over-Relaxation)
 *
 * @param temp Pointer to temperature grid (Input/Output)
 * @param cond Pointer to conductivity grid
 * @param fixed_mask Pointer to integer mask (1 = Fixed/Dirichlet, 0 = Variable)
 * @param fixed_values Pointer to values to enforce where mask is 1
 * @param rows Number of rows
 * @param cols Number of columns
 * @param iterations Number of iterations to perform
 * @param omega Relaxation factor (1.0 = Gauss-Seidel, 1.0 < omega < 2.0 = SOR)
 */
double solve_red_black(double *temp, const double *cond, const int *fixed_mask,
                       const double *fixed_values, int rows, int cols,
                       int iterations, double omega) {
  double max_diff = 0.0;

  auto harm = [](double k1, double k2) {
    return 2.0 * k1 * k2 / (k1 + k2 + 1e-12);
  };

  for (int iter = 0; iter < iterations; ++iter) {
    max_diff = 0.0;

    // We do two passes: Red ((r+c)%2 == 0) and Black ((r+c)%2 == 1)
    for (int color = 0; color < 2; ++color) {

#pragma omp parallel for reduction(max : max_diff)
      for (int r = 1; r < rows - 1; ++r) {
        int c_start = 1;
        // Adjust start to match color
        // If (r + c_start) % 2 != color, move to next
        if ((r + c_start) % 2 != color) {
          c_start++;
        }

        for (int c = c_start; c < cols - 1; c += 2) {
          int idx = r * cols + c;

          // Skip if fixed
          if (fixed_mask[idx]) {
            continue;
          }

          int idx_up = (r - 1) * cols + c;
          int idx_dn = (r + 1) * cols + c;
          int idx_lf = r * cols + (c - 1);
          int idx_rt = r * cols + (c + 1);

          double kc = cond[idx];
          double g_up = harm(kc, cond[idx_up]);
          double g_dn = harm(kc, cond[idx_dn]);
          double g_lf = harm(kc, cond[idx_lf]);
          double g_rt = harm(kc, cond[idx_rt]);
          double g_sum = g_up + g_dn + g_lf + g_rt;

          double val_gauss = (g_up * temp[idx_up] + g_dn * temp[idx_dn] +
                              g_lf * temp[idx_lf] + g_rt * temp[idx_rt]) /
                             (g_sum + 1e-12);

          // SOR Update
          double val_new = (1.0 - omega) * temp[idx] + omega * val_gauss;

          double diff = std::abs(val_new - temp[idx]);
          if (diff > max_diff)
            max_diff = diff;

          temp[idx] = val_new;
        }
      }
    }

    // Apply Boundaries (Adiabatic or Dirichlet)
    // Dirkchlet (Fixed) are skipped above, so they retain values?
    // Wait, if we initialize with something else, we need to enforce
    // fixed_values. But usually `temp` already has them. Let's enforce fixed
    // values just in case to avoid drift if user passed bad temp. Actually,
    // enforcing them inside the loop is expensive if we do it separately. We
    // skipped them in the update, so they shouldn't change. BUT, we need to
    // handle Adiabatic boundaries (Outer edges).

    // Left (c=0)
    for (int r = 0; r < rows; ++r) {
      int idx = r * cols + 0;
      if (!fixed_mask[idx])
        temp[idx] = temp[r * cols + 1];
      else
        temp[idx] = fixed_values[idx];
    }
    // Right (c=cols-1)
    for (int r = 0; r < rows; ++r) {
      int idx = r * cols + (cols - 1);
      if (!fixed_mask[idx])
        temp[idx] = temp[r * cols + (cols - 2)];
      else
        temp[idx] = fixed_values[idx];
    }
    // Bottom (r=0)
    for (int c = 0; c < cols; ++c) {
      int idx = 0 * cols + c;
      if (!fixed_mask[idx])
        temp[idx] = temp[1 * cols + c];
      else
        temp[idx] = fixed_values[idx];
    }
    // Top (r=rows-1)
    for (int c = 0; c < cols; ++c) {
      int idx = (rows - 1) * cols + c;
      if (!fixed_mask[idx])
        temp[idx] = temp[(rows - 2) * cols + c];
      else
        temp[idx] = fixed_values[idx];
    }
  }
  return max_diff;
}
}

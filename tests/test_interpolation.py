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


import numpy as np
from scipy.interpolate import RegularGridInterpolator

def test_interpolation_logic():
    print("Testing Interpolation Logic...")
    
    # 1. Create Source Data (Proposed)
    # 10x10 grid on [0, 1] x [0, 1]
    nx_prop, ny_prop = 10, 10
    prop_x = np.linspace(0, 1.0, nx_prop+1)
    prop_y = np.linspace(0, 1.0, ny_prop+1)
    
    # Cell centers
    prop_xc = (prop_x[:-1] + prop_x[1:]) / 2.0
    prop_yc = (prop_y[:-1] + prop_y[1:]) / 2.0
    
    # Value = X + Y
    XX, YY = np.meshgrid(prop_xc, prop_yc) # Default is 'xy' for meshgrid usually, let's be explicit
    # RegularGridInterpolator expects (points_1, points_2, ...) and values shape (len(points_1), len(points_2)...)
    # Our data is typically (ny, nx) -> indexed by (y, x)
    
    # If we map Y to axis 0 and X to axis 1:
    prop_val = np.zeros((ny_prop, nx_prop))
    Yg, Xg = np.meshgrid(prop_yc, prop_xc, indexing='ij')
    prop_val = Yg + Xg
    
    # Interpolator
    # points should be (y_coords, x_coords)
    interp = RegularGridInterpolator((prop_yc, prop_xc), prop_val, bounds_error=False, fill_value=None)
    
    # 2. Reference Grid (Higher Resolution)
    # 20x20 grid
    nx_ref, ny_ref = 20, 20
    ref_x = np.linspace(0, 1.0, nx_ref+1)
    ref_y = np.linspace(0, 1.0, ny_ref+1)
    
    ref_xc = (ref_x[:-1] + ref_x[1:]) / 2.0
    ref_yc = (ref_y[:-1] + ref_y[1:]) / 2.0
    
    Y_ref, X_ref = np.meshgrid(ref_yc, ref_xc, indexing='ij')
    
    # 3. Interpolate
    resampled = interp((Y_ref, X_ref))
    
    # 4. Check Values
    # Correct value at any point is y + x
    expected = Y_ref + X_ref
    
    diff = np.abs(resampled - expected)
    max_diff = np.max(diff)
    
    print(f"Max Interpolation Error: {max_diff}")
    
    assert max_diff < 1e-10, "Interpolation should be exact for linear function"
    print("Interpolation Test Passed!")

if __name__ == "__main__":
    test_interpolation_logic()

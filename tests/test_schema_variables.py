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


import pytest
from backend.core.scenario_schema import CanvasConfig

class TestCanvasConfigVariables:
    def test_canvas_grid_references(self):
        """Canvas grid accepts variable references."""
        canvas = CanvasConfig(bounds=[0, 100, 0, 200], grid="${grid_size}")
        assert canvas.grid == "${grid_size}"
        assert canvas.x_max == 100
    
    def test_canvas_bounds_references(self):
        """Canvas bounds accept variable references."""
        canvas = CanvasConfig(bounds=[0, "${width}", 0, 200], grid=1.0)
        assert canvas.x_max == "${width}"

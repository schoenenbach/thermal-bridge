
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

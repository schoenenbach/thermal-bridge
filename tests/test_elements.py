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
from unittest.mock import MagicMock
from backend.core.elements import (
    Factory, RectElement, Wall, Insulation, InsulationTapered,
    WindowDetail, RollerShutterBox, WindowSill, VenetianBlindBox, RoofJunction
)
from backend.core.geometry import SketchGeometry, MaterialID

@pytest.fixture
def mock_sketch():
    sketch = MagicMock(spec=SketchGeometry)
    sketch.add_point = MagicMock()
    sketch.add_shape = MagicMock()
    return sketch

def test_rect_element(mock_sketch):
    el = RectElement(mock_sketch, name="TestRect", x=0, y=0, width=10, height=20, material_id=MaterialID.WALL, lambda_val=0.5)
    el.build()
    
    # Verify points added
    assert mock_sketch.add_point.call_count == 4
    # Verify shape added
    mock_sketch.add_shape.assert_called_once()
    args, _ = mock_sketch.add_shape.call_args
    assert args[1] == MaterialID.WALL
    assert args[2] == 0.5
    assert args[3] == "TestRect"

def test_wall_element(mock_sketch):
    el = Wall(mock_sketch, x=0, y=0, width=10, height=10)
    el.build()
    mock_sketch.add_shape.assert_called_once()
    args, _ = mock_sketch.add_shape.call_args
    assert args[1] == MaterialID.WALL # Default
    
def test_insulation_tapered(mock_sketch):
    el = InsulationTapered(mock_sketch, 
        x_base=0, y_bottom=0, y_top=100, 
        thick_main=10, thick_taper=5, taper_start_y=80,
        name="IsoTap"
    )
    el.build()
    
    assert mock_sketch.add_point.call_count == 6
    mock_sketch.add_shape.assert_called_once()

def test_factory_create(mock_sketch):
    el = Factory.create('rect', mock_sketch, name="FactoryRect", x=0, y=0, width=5, height=5)
    assert isinstance(el, RectElement)
    el.build()
    mock_sketch.add_shape.assert_called()

def test_roller_shutter_box(mock_sketch):
    el = RollerShutterBox(mock_sketch, name="Shutter", x=0, y=0, width=20, height=20, insulation_thickness=5)
    el.build()
    
    # Should build at least 2 shapes (box + insulation)
    assert mock_sketch.add_shape.call_count >= 2

def test_window_sill(mock_sketch):
    el = WindowSill(mock_sketch, name="Sill", x=0, y=0, width=100)
    el.build()
    
    # Should build Internal and External sill (2 shapes)
    assert mock_sketch.add_shape.call_count == 2

def test_venetian_blind_box(mock_sketch):
    el = VenetianBlindBox(mock_sketch, name="Blind", x=0, y=0, width=20, height=30, insulation_thickness=5)
    el.build()
    
    # Box + Insulation
    assert mock_sketch.add_shape.call_count >= 2

def test_roof_junction(mock_sketch):
    el = RoofJunction(mock_sketch, name="Roof", x_wall=0)
    el.build()
    
    # Wall segment
    mock_sketch.add_shape.assert_called()


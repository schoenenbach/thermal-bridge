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
Tests for Schema API endpoints.
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_scenario_schema():
    """Test retrieving the scenarios JSON Schema."""
    response = client.get("/api/schema/scenario")
    assert response.status_code == 200
    schema = response.json()
    
    assert "title" in schema
    assert schema["title"] == "Thermal Bridge Scenario"
    assert "properties" in schema
    assert "$defs" in schema
    assert "canvas" in schema["properties"]
    assert "elements" in schema["properties"]


def test_get_scenario_schema_with_hints():
    """Test retrieving schema with UI hints injected."""
    response = client.get("/api/schema/scenario?ui_hints=true")
    assert response.status_code == 200
    schema = response.json()
    
    # Check for x-ui-hints in canvas.bounds
    canvas = schema["properties"]["canvas"]
    assert "x-ui-hints" in canvas
    assert canvas["x-ui-hints"]["group"] == "Canvas Configuration"
    
    # Check deeper nesting
    canvas_def = schema["$defs"]["CanvasConfig"]
    bounds = canvas_def["properties"]["bounds"]
    assert "x-ui-hints" in bounds
    assert bounds["x-ui-hints"]["widget"] == "bounds_editor"


def test_get_element_schemas():
    """Test retrieving element-specific schemas and hints."""
    response = client.get("/api/schema/elements")
    assert response.status_code == 200
    data = response.json()
    
    assert "definitions" in data
    assert "hints" in data
    
    hints = data["hints"]
    assert "rect" in hints
    assert "wall" in hints
    
    # Check hint content
    assert hints["rect"]["x"]["unit"] == "mm"
    assert hints["wall"]["thickness"]["min"] == 10

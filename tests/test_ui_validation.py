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
Tests for UI Validation Module
"""
import pytest
from backend.core.ui_validation import validate_scenario_yaml, get_element_hints, ValidationResult

class TestValidateScenarioYaml:
    """Tests for validate_scenario_yaml function."""

    def test_validate_valid_scenario(self):
        """Valid YAML validation."""
        yaml_content = """
name: "Valid Scenario"
canvas:
  bounds: [0, 100, 0, 100]
  grid: 10
elements:
  - type: rect
    params:
      x: 0
      y: 0
      width: 50
      height: 50
"""
        result = validate_scenario_yaml(yaml_content)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.data['name'] == "Valid Scenario"

    def test_validate_invaid_yaml_syntax(self):
        """Invalid YAML syntax."""
        yaml_content = """
name: "Broken
  - indent error?
"""
        result = validate_scenario_yaml(yaml_content)
        assert result.is_valid is False
        assert "YAML Syntax Error" in result.errors[0].message
        # Line number should be roughly correct (2 or 3)
        assert result.errors[0].line > 1

    def test_validate_missing_required_field(self):
        """Missing required 'canvas' field."""
        yaml_content = """
name: "Missing Canvas"
elements: []
"""
        result = validate_scenario_yaml(yaml_content)
        assert result.is_valid is False
        # Should have error about canvas
        assert any("canvas" in err.message for err in result.errors)

    def test_validate_invalid_value_logic(self):
        """Grid size 0 is invalid logic."""
        yaml_content = """
name: "Bad Grid"
canvas:
  bounds: [0, 100, 0, 100]
  grid: 0
elements: []
"""
        result = validate_scenario_yaml(yaml_content)
        assert result.is_valid is False
        assert any("grid" in err.message for err in result.errors)

    def test_element_hints(self):
        """Test hint retrieval."""
        hints = get_element_hints("rect")
        assert "width" in hints
        assert "height" in hints
        
        hints_poly = get_element_hints("polygon")
        assert "points" in hints_poly[0]

    def test_line_finder_heuristic(self):
        """Test basic line finding."""
        yaml_content = """
name: "Test"
canvas:
  bounds: [0, 100, 0, 100]
  grid: 0
"""
        # grid is 0, so error at loc=['canvas', 'grid']
        # The key 'grid' is on line 5
        result = validate_scenario_yaml(yaml_content)
        error = next(e for e in result.errors if "grid" in e.message)
        assert error.line == 5

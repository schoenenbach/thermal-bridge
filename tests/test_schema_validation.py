"""
Schema Validation Tests

Tests for the scenario schema to ensure:
1. Schema version field exists
2. Element type definitions are correct
3. Invalid scenarios are rejected
4. JSON Schema export works correctly
"""

import pytest
import json
from scenario_schema import (
    Scenario, MaterialDef, CanvasConfig, ElementBase,
    RectParams, WallParams, InsulationTaperedParams, WindowDetailParams
)
from pydantic import ValidationError


class TestSchemaVersion:
    """Tests for schema versioning."""
    
    def test_schema_version_default(self):
        """Schema version defaults to '1.0'."""
        data = {
            "name": "Test",
            "canvas": {"bounds": [0, 100, 0, 100], "grid": 1},
            "elements": []
        }
        scenario = Scenario(**data)
        assert scenario.schema_version == "1.0"
    
    def test_schema_version_explicit(self):
        """Schema version can be set explicitly."""
        data = {
            "schema_version": "2.0",
            "name": "Test",
            "canvas": {"bounds": [0, 100, 0, 100], "grid": 1},
            "elements": []
        }
        scenario = Scenario(**data)
        assert scenario.schema_version == "2.0"


class TestMaterialDef:
    """Tests for material definition validation."""
    
    def test_material_requires_id_and_lambda(self):
        """Material must have id and lambda."""
        mat = MaterialDef(id="WALL", **{"lambda": 0.8})
        assert mat.id == "WALL"
        assert mat.lambda_val == 0.8
    
    def test_material_color_defaults(self):
        """Material color defaults to gray."""
        mat = MaterialDef(id="TEST", **{"lambda": 1.0})
        assert mat.color == "#808080"


class TestCanvasConfig:
    """Tests for canvas configuration."""
    
    def test_canvas_requires_bounds_and_grid(self):
        """Canvas must have bounds and grid."""
        canvas = CanvasConfig(bounds=[0, 100, 0, 200], grid=2.5)
        assert canvas.x_min == 0
        assert canvas.x_max == 100
        assert canvas.y_min == 0
        assert canvas.y_max == 200
        assert canvas.grid == 2.5
    
    def test_canvas_grid_must_be_positive(self):
        """Grid must be > 0."""
        with pytest.raises(ValidationError):
            CanvasConfig(bounds=[0, 100, 0, 100], grid=0)
    
    def test_canvas_bounds_must_have_4_elements(self):
        """Bounds must have exactly 4 elements."""
        with pytest.raises(ValidationError):
            CanvasConfig(bounds=[0, 100, 0], grid=1)


class TestElementParams:
    """Tests for element parameter schemas."""
    
    def test_rect_params_accepts_floats(self):
        """RectParams accepts float values."""
        params = RectParams(x=10.0, y=20.0, width=100.0, height=50.0)
        assert params.x == 10.0
        assert params.height == 50.0
    
    def test_rect_params_accepts_variable_strings(self):
        """RectParams accepts variable reference strings."""
        params = RectParams(x="${x_wall}", y="${y_bottom}", width="${w}", height="${h}")
        assert params.x == "${x_wall}"
    
    def test_insulation_tapered_params(self):
        """InsulationTaperedParams validates correctly."""
        params = InsulationTaperedParams(
            x_base=500.0,
            y_bottom=0.0,
            y_top=200.0,
            thick_main=200.0,
            thick_taper=100.0,
            taper_start_y=50.0
        )
        assert params.thick_main == 200.0


class TestJsonSchemaExport:
    """Tests for JSON Schema generation."""
    
    def test_schema_export_generates_valid_json(self):
        """model_json_schema() returns valid JSON-serializable dict."""
        schema = Scenario.model_json_schema()
        
        # Should be serializable to JSON
        json_str = json.dumps(schema)
        assert len(json_str) > 1000  # Should be substantial
    
    def test_schema_has_definitions(self):
        """Schema includes $defs for nested types."""
        schema = Scenario.model_json_schema()
        assert "$defs" in schema
        assert "CanvasConfig" in schema["$defs"]
        assert "MaterialDef" in schema["$defs"]
    
    def test_schema_has_required_fields(self):
        """Schema marks name, canvas, elements as required."""
        schema = Scenario.model_json_schema()
        assert "name" in schema.get("required", [])
        assert "canvas" in schema.get("required", [])
        assert "elements" in schema.get("required", [])


class TestScenarioValidation:
    """End-to-end scenario validation tests."""
    
    def test_minimal_valid_scenario(self):
        """Minimal scenario with required fields only."""
        data = {
            "name": "Minimal",
            "canvas": {"bounds": [0, 100, 0, 100], "grid": 1},
            "elements": []
        }
        scenario = Scenario(**data)
        assert scenario.name == "Minimal"
    
    def test_scenario_with_materials(self):
        """Scenario with custom materials."""
        data = {
            "name": "WithMaterials",
            "canvas": {"bounds": [0, 100, 0, 100], "grid": 1},
            "materials": [
                {"id": "CUSTOM", "lambda": 0.5, "color": "#FF0000"}
            ],
            "elements": []
        }
        scenario = Scenario(**data)
        assert len(scenario.materials) == 1
        assert scenario.materials[0].id == "CUSTOM"
    
    def test_scenario_missing_name_fails(self):
        """Scenario without name fails validation."""
        data = {
            "canvas": {"bounds": [0, 100, 0, 100], "grid": 1},
            "elements": []
        }
        with pytest.raises(ValidationError):
            Scenario(**data)
    
    def test_scenario_missing_canvas_fails(self):
        """Scenario without canvas fails validation."""
        data = {
            "name": "NoCanvas",
            "elements": []
        }
        with pytest.raises(ValidationError):
            Scenario(**data)

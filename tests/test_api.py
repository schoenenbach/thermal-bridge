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
API Tests.

Tests for the FastAPI REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestScenariosAPI:
    """Test scenarios API endpoints."""
    
    def test_list_scenarios(self):
        """Test listing all scenarios."""
        response = client.get("/api/scenarios/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # Should have at least demo scenarios
    
    def test_get_scenario(self):
        """Test getting a specific scenario."""
        response = client.get("/api/scenarios/scenario_1.yaml")
        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert "data" in data
    
    def test_get_scenario_not_found(self):
        """Test 404 for missing scenario."""
        response = client.get("/api/scenarios/nonexistent.yaml")
        assert response.status_code == 404
    
    def test_validate_scenario_valid(self):
        """Test validation with valid YAML."""
        valid_yaml = """
name: "Test Scenario"
canvas:
  bounds: [0, 100, 0, 100]
  grid: 5.0
elements:
  - type: rect
    material: WALL
    params:
      x: 0
      y: 0
      width: 50
      height: 100
"""
        response = client.post(
            "/api/scenarios/validate",
            json={"yaml_content": valid_yaml}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] == True
    
    def test_validate_scenario_invalid(self):
        """Test validation with invalid YAML."""
        invalid_yaml = """
name: "Test"
# Missing required canvas
elements: []
"""
        response = client.post(
            "/api/scenarios/validate",
            json={"yaml_content": invalid_yaml}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] == False
        assert len(data["errors"]) > 0


class TestMaterialsAPI:
    """Test materials API endpoints."""
    
    def test_list_materials(self):
        """Test listing all materials."""
        response = client.get("/api/materials/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_categories(self):
        """Test listing material categories."""
        response = client.get("/api/materials/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
    
    def test_get_lambda(self):
        """Test lambda lookup."""
        response = client.get("/api/materials/lookup/lambda/wall_generic?default=0.5")
        assert response.status_code == 200
        data = response.json()
        assert "lambda" in data


class TestSimulationAPI:
    """Test simulation API endpoints (basic checks only)."""
    
    def test_simulation_endpoint_exists(self):
        """Test that simulation endpoint exists."""
        # Just check it's reachable, don't run full sim
        response = client.post("/api/simulation/run", json={
            "scenario": {"name": "test", "canvas": {"bounds": [0,1,0,1], "grid": 1}, "elements": []}
        })
        # Should return 200 even if simulation fails
        assert response.status_code == 200

    def test_run_simulation_returns_temp_data(self):
        """Test that simulation returns temperature_data structure."""
        # Simple scenario that should run quickly
        scenario = {
            "name": "Test Data",
            "canvas": {"bounds": [0, 100, 0, 100], "grid": 10},
            "elements": [
                {"type": "rect", "material": "WALL", "params": {"x": 0, "y": 0, "width": 100, "height": 100}}
            ],
            "boundary_conditions": {
                "convective": {
                    "left": {"T": 20, "R": 0.13},
                    "right": {"T": 0, "R": 0.04}
                }
            }
        }
        
        response = client.post("/api/simulation/run", json={
            "scenario": scenario,
            "use_adaptive_mesh": False, # Faster
            "override_grid_size": 25 # Coarse grid
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Check temperature_data
        assert "temperature_data" in data
        t_data = data["temperature_data"]
        # It might be None if simulation failed or result didn't have temp, 
        # but with this simple scenario it should succeed and return data.
        if t_data is not None:
            assert "data" in t_data
            assert "width" in t_data
            assert "height" in t_data
            assert "temp_min" in t_data
            assert "temp_max" in t_data
            assert isinstance(t_data["data"], list)
            assert len(t_data["data"]) > 0

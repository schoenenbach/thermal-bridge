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
API Request/Response Models.

Extends existing Pydantic schemas with API-specific wrappers.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Re-export core schemas
from backend.core.scenario_schema import (
    Scenario,
    MaterialDef,
    CanvasConfig,
    BoundaryConditions,
    MeasurementsConfig,
    TransientConfig,
)


# --- Request Models ---

class ScenarioValidationRequest(BaseModel):
    """Request to validate a scenario."""
    yaml_content: Optional[str] = Field(None, description="Raw YAML content to validate")
    json_content: Optional[Dict[str, Any]] = Field(None, description="JSON/dict content to validate")
    
    def get_content(self) -> Dict[str, Any]:
        """Parse and return content as dict."""
        if self.json_content:
            return self.json_content
        elif self.yaml_content:
            import yaml
            return yaml.safe_load(self.yaml_content)
        else:
            raise ValueError("Either yaml_content or json_content must be provided")


class SimulationRequest(BaseModel):
    """Request to run a simulation."""
    scenario: Dict[str, Any] = Field(..., description="Scenario definition")
    use_adaptive_mesh: bool = Field(True, description="Use adaptive mesh refinement")
    override_grid_size: Optional[float] = Field(None, description="Override grid size in mm")
    transient_enabled: bool = Field(False, description="Run transient simulation")
    mold_analysis: bool = Field(False, description="Include mold risk analysis")
    indoor_rh: float = Field(0.5, description="Indoor relative humidity for mold analysis (0-1)")


class OptimizationRequest(BaseModel):
    """Request for parameter sweep optimization."""
    scenario: Dict[str, Any] = Field(..., description="Base scenario definition")
    variable: str = Field(..., description="Variable name to sweep")
    start: float = Field(..., description="Start value")
    end: float = Field(..., description="End value") 
    step: float = Field(..., description="Step size")


# --- Response Models ---

class ValidationError(BaseModel):
    """Single validation error."""
    field: str
    message: str
    line: Optional[int] = None


class ValidationResult(BaseModel):
    """Result of scenario validation."""
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    scenario_name: Optional[str] = None


class SimulationMetrics(BaseModel):
    """Key simulation result metrics."""
    psi_value: Optional[float] = None
    frsi_factor: Optional[float] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    heat_flux_interior: Optional[float] = None
    solver_iterations: Optional[int] = None
    computation_time_ms: Optional[float] = None


class TemperatureData(BaseModel):
    """Compressed temperature array for client-side rendering."""
    data: List[List[float]]  # 2D temperature grid (downsampled)
    width: float             # Canvas width in mm
    height: float            # Canvas height in mm
    temp_min: float          # Min temperature for color scale
    temp_max: float          # Max temperature for color scale
    rows: int                # Number of rows in data
    cols: int                # Number of columns in data


class SimulationResult(BaseModel):
    """Result of a simulation run."""
    success: bool
    metrics: Optional[SimulationMetrics] = None
    error: Optional[str] = None
    temperature_map_url: Optional[str] = None
    geometry_map_url: Optional[str] = None
    mold_risk_map_url: Optional[str] = None
    temperature_data: Optional[TemperatureData] = None  # For client-side rendering
    measurements: Dict[str, Any] = Field(default_factory=dict)


class OptimizationPoint(BaseModel):
    """Single point in optimization sweep."""
    variable_value: float
    psi_value: Optional[float] = None
    frsi_factor: Optional[float] = None
    success: bool


class OptimizationResult(BaseModel):
    """Result of parameter sweep."""
    success: bool
    variable: str
    points: List[OptimizationPoint] = Field(default_factory=list)
    optimal_value: Optional[float] = None
    optimal_psi: Optional[float] = None
    error: Optional[str] = None


class JobCreatedResponse(BaseModel):
    """Response when an async job is created."""
    job_id: str
    ws_url: str


class ProgressMessage(BaseModel):
    """Progress update message sent via WebSocket."""
    phase: str
    step: int
    total: int
    percent: float
    eta_seconds: Optional[float] = None


class MaterialInfo(BaseModel):
    """Material information for API responses."""
    id: str
    name: str
    lambda_val: float = Field(..., alias="lambda")
    color: str = "#808080"
    category: Optional[str] = None
    source: Optional[str] = None
    
    model_config = {"populate_by_name": True}


class ScenarioSummary(BaseModel):
    """Summary of a saved scenario."""
    filename: str
    name: str
    description: Optional[str] = None
    element_count: int = 0
    has_measurements: bool = False

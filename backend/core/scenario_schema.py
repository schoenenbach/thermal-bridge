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
Pydantic Schema Definitions for Scenarios.
Provides strict validation and flexible component definitions.

Schema Version: 1.0
"""

from typing import List, Dict, Optional, Union, Any, Literal, Annotated
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, Discriminator

# --- Basic Types ---

VariableValue = Union[float, int, str]
"""Variable values can be numeric or string (for expressions like ${x} + ${y})."""


class MaterialDef(BaseModel):
    """Explicit material definition."""
    id: str = Field(..., description="Unique identifier for the material (e.g. 'WALL')")
    lambda_val: float = Field(..., alias='lambda', description="Thermal conductivity in W/(m*K)")
    color: str = Field("#808080", description="Hex color for visualization")
    description: Optional[str] = None
    
    # Solver mapping (optional, used if linking to legacy solver IDs explicitly)
    solver_id: Optional[int] = None


class CanvasConfig(BaseModel):
    """Simulation canvas settings."""
    # Bounds can contain variables too
    bounds: List[Union[float, str]] = Field(..., min_length=4, max_length=4, description="[x_min, x_max, y_min, y_max]")
    grid: Union[float, str] = Field(..., description="Grid resolution in mm")

    @field_validator('grid')
    @classmethod
    def grid_must_be_positive(cls, v):
        """Grid must be > 0 when specified as a number."""
        if isinstance(v, (int, float)) and v <= 0:
            raise ValueError('grid must be greater than 0')
        return v

    @property
    def x_min(self) -> Union[float, str]: return self.bounds[0]
    @property
    def x_max(self) -> Union[float, str]: return self.bounds[1]
    @property
    def y_min(self) -> Union[float, str]: return self.bounds[2]
    @property
    def y_max(self) -> Union[float, str]: return self.bounds[3]


# --- Element Param Schemas ---
# These define the expected params for each element type.
# All fields use Optional with defaults to maintain backward compatibility
# since existing YAML files may use variable references like "${x_wall}".

class RectParams(BaseModel):
    """Parameters for rect elements."""
    x: Union[float, str] = Field(0.0, description="X coordinate (mm)")
    y: Union[float, str] = Field(0.0, description="Y coordinate (mm)")
    width: Union[float, str] = Field(0.0, description="Width (mm)")
    height: Union[float, str] = Field(0.0, description="Height (mm)")
    model_config = ConfigDict(extra='allow')


class WallParams(BaseModel):
    """Parameters for wall elements (same as rect)."""
    x: Union[float, str] = Field(0.0, description="X coordinate (mm)")
    y: Union[float, str] = Field(0.0, description="Y coordinate (mm)")
    width: Union[float, str] = Field(0.0, description="Width (mm)")
    height: Union[float, str] = Field(0.0, description="Height (mm)")
    model_config = ConfigDict(extra='allow')


class AirParams(BaseModel):
    """Parameters for air elements."""
    x: Union[float, str] = Field(0.0, description="X coordinate (mm)")
    y: Union[float, str] = Field(0.0, description="Y coordinate (mm)")
    width: Union[float, str] = Field(0.0, description="Width (mm)")
    height: Union[float, str] = Field(0.0, description="Height (mm)")
    type: Optional[str] = Field("ext", description="Air type: 'int' or 'ext'")
    name: Optional[str] = None
    model_config = ConfigDict(extra='allow')


class InsulationTaperedParams(BaseModel):
    """Parameters for tapered insulation elements."""
    x_base: Union[float, str] = Field(..., description="X base coordinate (mm)")
    y_bottom: Union[float, str] = Field(..., description="Y bottom coordinate (mm)")
    y_top: Union[float, str] = Field(..., description="Y top coordinate (mm)")
    thick_main: Union[float, str] = Field(..., description="Main thickness (mm)")
    thick_taper: Union[float, str] = Field(..., description="Tapered thickness (mm)")
    taper_start_y: Union[float, str] = Field(..., description="Y coordinate where taper starts (mm)")
    model_config = ConfigDict(extra='allow')


class WindowDetailParams(BaseModel):
    """Parameters for window detail elements."""
    x_frame_start: Union[float, str] = Field(..., description="X coordinate of frame start (mm)")
    y_frame_start: Union[float, str] = Field(..., description="Y coordinate of frame start (mm)")
    frame_depth: Union[float, str] = Field(..., description="Frame depth (mm)")
    frame_width: Union[float, str] = Field(..., description="Frame width (mm)")
    sash_depth: Union[float, str] = Field(..., description="Sash depth (mm)")
    sash_width: Union[float, str] = Field(..., description="Sash width (mm)")
    sash_overlap: Union[float, str] = Field(0.0, description="Sash overlap (mm)")
    sash_recess: Union[float, str] = Field(0.0, description="Sash recess (mm)")
    glass_thickness: Union[float, str] = Field(..., description="Glass thickness (mm)")
    y_top: Union[float, str] = Field(..., description="Y top coordinate (mm)")
    mat_frame_lambda: Optional[float] = Field(None, description="Frame thermal conductivity override")
    mat_glass_lambda: Optional[float] = Field(None, description="Glass thermal conductivity override")
    model_config = ConfigDict(extra='allow')


class WindowSillParams(BaseModel):
    """Parameters for window sill elements."""
    x: Union[float, str] = Field(..., description="X coordinate (mm)")
    y: Union[float, str] = Field(..., description="Y coordinate (mm)")
    width: Union[float, str] = Field(..., description="Width (mm)")
    depth_ext: Union[float, str] = Field(..., description="External depth (mm)")
    depth_int: Union[float, str] = Field(..., description="Internal depth (mm)")
    model_config = ConfigDict(extra='allow')


class VenetianBlindParams(BaseModel):
    """Parameters for venetian blind box elements."""
    x: Union[float, str] = Field(..., description="X coordinate (mm)")
    y: Union[float, str] = Field(..., description="Y coordinate (mm)")
    width: Union[float, str] = Field(..., description="Width (mm)")
    height: Union[float, str] = Field(..., description="Height (mm)")
    insulation_thickness: Union[float, str] = Field(0.0, description="Insulation thickness (mm)")
    model_config = ConfigDict(extra='allow')


class RoofJunctionParams(BaseModel):
    """Parameters for roof junction elements."""
    x_wall: Union[float, str] = Field(..., description="X coordinate of wall (mm)")
    y_wall_top: Union[float, str] = Field(..., description="Y coordinate of wall top (mm)")
    wall_width: Union[float, str] = Field(..., description="Wall width (mm)")
    model_config = ConfigDict(extra='allow')


# --- Element Type Definitions ---

class ElementBase(BaseModel):
    """Base class for all geometry elements."""
    type: str
    name: Optional[str] = None
    material: Union[str, int] = Field("WALL", description="Material ID or Name")
    lambda_override: Optional[float] = Field(None, alias='lambda')
    model_config = ConfigDict(extra='allow')  # Keep for backward compat with top-level x,y,width,height


class RectElement(ElementBase):
    """Rectangle element."""
    type: Literal['rect']
    params: Optional[RectParams] = Field(default_factory=RectParams)
    # Also allow top-level x,y,width,height for shorthand
    x: Optional[Union[float, str]] = None
    y: Optional[Union[float, str]] = None
    width: Optional[Union[float, str]] = None
    height: Optional[Union[float, str]] = None


class WallElement(ElementBase):
    """Wall element (specialized rect)."""
    type: Literal['wall']
    params: Optional[WallParams] = Field(default_factory=WallParams)


class AirElement(ElementBase):
    """Air region element."""
    type: Literal['air']
    params: Optional[AirParams] = Field(default_factory=AirParams)


class PolygonElement(ElementBase):
    """Polygon element defined by named points."""
    type: Literal['polygon']
    points: List[str] = Field(..., description="List of named points")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class InsulationTaperedElement(ElementBase):
    """Tapered insulation element."""
    type: Literal['insulation_tapered']
    params: InsulationTaperedParams


class WindowDetailElement(ElementBase):
    """Window detail element with frame, sash, and glass."""
    type: Literal['window_detail']
    params: WindowDetailParams


class WindowSillElement(ElementBase):
    """Window sill element."""
    type: Literal['window_sill']
    params: WindowSillParams


class VenetianBlindElement(ElementBase):
    """Venetian blind box element."""
    type: Literal['venetian_blind']
    params: VenetianBlindParams


class RoofJunctionElement(ElementBase):
    """Roof junction element."""
    type: Literal['roof_junction']
    params: RoofJunctionParams


class GenericElement(ElementBase):
    """Fallback for custom/unknown element types (component instances, etc)."""
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Discriminated Union for all element types
def get_element_type(v: Any) -> str:
    """Extract element type for discriminator."""
    if isinstance(v, dict):
        return v.get('type', '__generic__')
    return getattr(v, 'type', '__generic__')


ScenarioElement = Annotated[
    Union[
        RectElement,
        WallElement,
        AirElement,
        PolygonElement,
        InsulationTaperedElement,
        WindowDetailElement,
        WindowSillElement,
        VenetianBlindElement,
        RoofJunctionElement,
        GenericElement,  # Fallback for component instances and unknown types
    ],
    Discriminator(get_element_type)
]


# --- Measurements ---

class PointProbe(BaseModel):
    """Point probe for temperature measurement."""
    name: str
    x: float
    y: float
    expected: Optional[float] = None
    tolerance: float = 0.5


class SurfaceMetric(BaseModel):
    """Surface metric (min/max/avg temperature on boundaries)."""
    name: str
    type: Literal['min', 'max', 'avg']
    boundary: Literal['internal', 'external']
    materials: Optional[List[str]] = None


class DerivedMetric(BaseModel):
    """Derived metric calculated from simulation results."""
    name: str
    formula: str = Field(..., description="Formula name: 'psi_value', 'frsi', etc.")


class MeasurementsConfig(BaseModel):
    """Configuration for measurements to extract from simulation."""
    point_probes: List[PointProbe] = Field(default_factory=list)
    surface_metrics: List[SurfaceMetric] = Field(default_factory=list)
    derived: List[DerivedMetric] = Field(default_factory=list)


# --- Boundary Conditions ---

class ConvectiveBCParams(BaseModel):
    """Convective boundary condition parameters."""
    T: float = Field(20.0, description="Temperature in Celsius")
    R: float = Field(0.13, description="Thermal resistance in m²K/W")


class BoundaryConditions(BaseModel):
    """Boundary conditions for the simulation."""
    dirichlet: Dict[str, float] = Field(default_factory=dict, description="Fixed temperature BCs")
    adiabatic: List[str] = Field(default_factory=list, description="Adiabatic boundary names")
    convective: Dict[str, Union[ConvectiveBCParams, Dict[str, float]]] = Field(
        default_factory=dict, 
        description="Convective BCs per side (internal, external, etc.)"
    )
    surface_resistance: Dict[Union[int, str], float] = Field(
        default_factory=dict, 
        description="Surface resistance overrides by material ID (can be int or string)"
    )


# --- Reusable Definitions ---

class ComponentDefinition(BaseModel):
    """Template for a reusable group of elements."""
    params: Dict[str, Any] = Field(default_factory=dict)
    elements: List[ElementBase] = Field(default_factory=list)


# --- Transient Simulation ---

class TransientConfig(BaseModel):
    """Configuration for transient (time-dependent) simulation."""
    enabled: bool = False
    duration_hours: float = Field(24.0, description="Simulation duration in hours")
    dt_seconds: float = Field(300.0, description="Time step in seconds")
    initial_temp: float = Field(20.0, description="Initial uniform temperature")
    save_interval_steps: int = Field(1, description="Save result every N steps")


# --- Refinement Zones ---

class RefinementZoneDef(BaseModel):
    """Refinement zone for finer mesh in specific regions."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    target_dx: float
    target_dy: Optional[float] = None  # defaults to target_dx if not specified
    priority: int = 0
    grading: float = 1.0 # Default grading factor


# --- Main Scenario ---

class Scenario(BaseModel):
    """
    Root scenario definition.
    
    A scenario defines a complete thermal simulation including geometry,
    materials, boundary conditions, and measurement specifications.
    """
    schema_version: str = Field("1.0", description="Schema version for migration support")
    name: str = Field(..., description="Human-readable scenario name")
    description: Optional[str] = Field(None, description="Detailed description")
    
    # Variables for substitution (supports ${var} syntax)
    variables: Dict[str, VariableValue] = Field(default_factory=dict)
    
    # Self-contained material definitions
    materials: List[MaterialDef] = Field(default_factory=list)
    
    # Reusable component definitions
    definitions: Dict[str, ComponentDefinition] = Field(default_factory=dict)
    
    # Geometry specification
    canvas: CanvasConfig = Field(..., description="Simulation canvas bounds and grid")
    points: Dict[str, List[Union[float, str]]] = Field(
        default_factory=dict, 
        description="Named points for polygon construction"
    )
    
    # Elements - now strongly typed with discriminated union!
    # We use List[Dict[str, Any]] at the Pydantic level for compatibility,
    # but the JSON Schema will show the expected structure.
    elements: List[Dict[str, Any]] = Field(
        ..., 
        description="Geometry elements (rect, wall, polygon, window_detail, etc.)"
    )
    
    # Measurements specification
    measurements: MeasurementsConfig = Field(default_factory=MeasurementsConfig)
    
    # Boundary conditions
    boundary_conditions: BoundaryConditions = Field(default_factory=BoundaryConditions)
    
    # Transient simulation settings
    transient: TransientConfig = Field(default_factory=TransientConfig)
    
    # Mesh refinement zones for finer resolution in specific areas
    refinement_zones: List[RefinementZoneDef] = Field(default_factory=list)

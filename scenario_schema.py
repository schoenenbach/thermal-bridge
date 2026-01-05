"""
Pydantic Schema Definitions for Scenarios.
Provides strict validation and flexible component definitions.
"""

from typing import List, Dict, Optional, Union, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# --- Basic Types ---

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
    bounds: List[float] = Field(..., min_length=4, max_length=4, description="[x_min, x_max, y_min, y_max]")
    grid: float = Field(..., gt=0, description="Grid resolution in mm")

    @property
    def x_min(self) -> float: return self.bounds[0]
    @property
    def x_max(self) -> float: return self.bounds[1]
    @property
    def y_min(self) -> float: return self.bounds[2]
    @property
    def y_max(self) -> float: return self.bounds[3]

# --- Element Definitions ---

class ElementBase(BaseModel):
    """Base class for all geometry elements."""
    type: str
    name: Optional[str] = None
    material: Union[str, int] = Field("WALL", description="Material ID or Name")
    # Generic params dict to support various element types flexibly
    params: Dict[str, Any] = Field(default_factory=dict)
    
    # Optional direct overrides
    lambda_override: Optional[float] = Field(None, alias='lambda')

    model_config = ConfigDict(extra='allow') # Allow extra fields for simpler definition

class RectElement(ElementBase):
    type: Literal['rect']
    # Specific fields can be promoted from params for better validation if desired,
    # but maintaining params dict approach for compatibility with factories is also fine.
    # We will enforce x,y,width,height existence in validator or rely on factory error.

class PolygonElement(ElementBase):
    type: Literal['polygon']
    points: List[str] = Field(..., description="List of named points")

class ComponentInstance(ElementBase):
    """Instance of a reusable component definition."""
    # type will be the component name
    pass

# --- Measurements ---

class PointProbe(BaseModel):
    name: str
    x: float
    y: float
    expected: Optional[float] = None
    tolerance: float = 0.5

class SurfaceMetric(BaseModel):
    name: str
    type: Literal['min', 'max', 'avg']
    boundary: Literal['internal', 'external']
    materials: Optional[List[str]] = None

class MeasurementsConfig(BaseModel):
    point_probes: List[PointProbe] = Field(default_factory=list)
    surface_metrics: List[SurfaceMetric] = Field(default_factory=list)
    # flux etc..

# --- Boundary Conditions ---


class ConvectiveBCParams(BaseModel):
    T: float = Field(20.0, description="Temperature in Celsius")
    R: float = Field(0.13, description="Thermal resistance in m²K/W")

class BoundaryConditions(BaseModel):
    dirichlet: Dict[str, float] = Field(default_factory=dict) # e.g. {'top': 20.0}
    adiabatic: List[str] = Field(default_factory=list)
    convective: Dict[str, Union[ConvectiveBCParams, Dict[str, float]]] = Field(default_factory=dict, description="Convective BCs per side (top, bottom, etc) or named override.")
    surface_resistance: Dict[Union[int, str], float] = Field(default_factory=dict, description="Surface resistance overrides by material ID.")


# --- Reusable Definitions ---

class ComponentDefinition(BaseModel):
    """Template for a reusable group of elements."""
    params: Dict[str, Any]  # Default values or type hints
    elements: List[ElementBase]

# --- Main Scenario ---


class TransientConfig(BaseModel):
    enabled: bool = False
    duration_hours: float = Field(24.0, description="Simulation duration in hours")
    dt_seconds: float = Field(300.0, description="Time step in seconds")
    initial_temp: float = Field(20.0, description="Initial uniform temperature")
    save_interval_steps: int = Field(1, description="Save result every N steps")

class Scenario(BaseModel):
    name: str
    description: Optional[str] = None
    
    # Variables for substitution
    variables: Dict[str, Any] = Field(default_factory=dict)
    
    # Self-contained definitions
    materials: List[MaterialDef] = Field(default_factory=list)
    definitions: Dict[str, ComponentDefinition] = Field(default_factory=dict)
    
    # Geometry
    canvas: CanvasConfig
    points: Dict[str, List[float]] = Field(default_factory=dict)
    
    # Elements list (can be polymorphic)
    elements: List[Dict[str, Any]] # We keep this loose (Dict) to allow various types, validated later or by Union
    
    measurements: MeasurementsConfig = Field(default_factory=MeasurementsConfig)
    boundary_conditions: BoundaryConditions = Field(default_factory=BoundaryConditions)
    transient: TransientConfig = Field(default_factory=TransientConfig)

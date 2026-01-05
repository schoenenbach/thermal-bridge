"""
Scenario Schema Definitions

Provides dataclass models for validating YAML scenario files.
Used by DeclarativeGeometry for schema validation.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Union


# --- Canvas Configuration ---
@dataclass
class CanvasConfig:
    """Canvas/simulation domain configuration."""
    bounds: List[float]  # [x_min, x_max, y_min, y_max]
    grid: float  # Grid resolution in mm
    
    def __post_init__(self):
        if len(self.bounds) != 4:
            raise ValueError(f"Canvas bounds must have 4 values, got {len(self.bounds)}")
        if self.grid <= 0:
            raise ValueError(f"Grid size must be positive, got {self.grid}")


# --- Boundary Conditions ---
@dataclass
class ConvectiveBoundary:
    """Convective boundary condition with temperature and resistance."""
    T: float  # Temperature in °C
    R: float  # Surface resistance in m²K/W


@dataclass 
class BoundaryConditions:
    """Boundary conditions for simulation.
    
    For window scenarios: Uses default internal/external temperatures from config.
    For ISO cases: Uses explicit dirichlet/convective conditions.
    """
    # Dirichlet (fixed temperature) boundaries
    dirichlet: Optional[Dict[str, float]] = None  # {edge: temperature}
    
    # Convective boundaries
    convective: Optional[Dict[str, ConvectiveBoundary]] = None  # {edge: {T, R}}
    
    # Adiabatic (insulated) edges
    adiabatic: Optional[List[str]] = None  # ['left', 'right', ...]
    
    # Surface resistances by material ID
    surface_resistance: Optional[Dict[int, float]] = None


# --- Measurement Definitions ---
@dataclass
class PointProbe:
    """Point temperature measurement."""
    name: str
    x: float
    y: float
    expected: Optional[float] = None  # Expected value for validation
    tolerance: Optional[float] = None


@dataclass
class SurfaceMetric:
    """Surface temperature metric (min/max on boundary)."""
    name: str
    type: str  # 'min' or 'max'
    boundary: str  # 'internal' or 'external'
    materials: Optional[List[str]] = None  # Filter by material types


@dataclass
class DerivedMetric:
    """Derived calculation (Psi, fRsi, etc.)."""
    name: str
    formula: str  # Formula identifier


@dataclass
class BoundaryFlux:
    """Heat flux through a boundary."""
    name: str
    boundary: str  # 'top', 'bottom', 'left', 'right'
    expected: Optional[float] = None
    tolerance: Optional[float] = None


@dataclass
class MeasurementsConfig:
    """All measurement definitions."""
    point_probes: Optional[List[PointProbe]] = None
    surface_metrics: Optional[List[SurfaceMetric]] = None
    derived: Optional[List[DerivedMetric]] = None
    boundary_flux: Optional[List[BoundaryFlux]] = None


# --- Element Definitions ---
@dataclass
class ElementParams:
    """Generic element parameters (varies by element type)."""
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    # Additional params for specific element types
    x_base: Optional[float] = None
    y_bottom: Optional[float] = None
    y_top: Optional[float] = None
    thick_main: Optional[float] = None
    thick_taper: Optional[float] = None
    taper_start_y: Optional[float] = None
    # Window detail params
    x_frame_start: Optional[float] = None
    y_frame_start: Optional[float] = None
    frame_depth: Optional[float] = None
    frame_width: Optional[float] = None
    sash_depth: Optional[float] = None
    sash_width: Optional[float] = None
    sash_overlap: Optional[float] = None
    sash_recess: Optional[float] = None
    glass_thickness: Optional[float] = None


@dataclass
class Element:
    """Geometry element definition."""
    type: str  # 'rect', 'polygon', 'wall', 'window_detail', 'insulation_tapered'
    name: Optional[str] = None
    material: Optional[Union[str, int]] = None  # Material name or ID
    lambda_val: Optional[float] = field(default=None, metadata={'yaml_key': 'lambda'})
    params: Optional[Dict[str, Any]] = None
    points: Optional[List[str]] = None  # For polygon type


# --- Refinement Zones ---
@dataclass
class RefinementZone:
    """Mesh refinement zone."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    target_dx: float
    priority: int = 1


# --- Main Scenario Schema ---
@dataclass
class ScenarioSchema:
    """Complete scenario definition schema.
    
    Required fields:
    - name: Scenario identifier
    - canvas: Simulation domain configuration
    - elements: List of geometry elements
    
    Optional fields:
    - description: Detailed description
    - variables: Parametric variables for ${} substitution
    - points: Named point definitions for polygons
    - measurements: Temperature probes and metrics
    - boundary_conditions: Custom BCs (defaults used if omitted)
    - refinement_zones: Mesh refinement areas
    - extends: Base scenario to inherit from (future)
    """
    name: str
    canvas: CanvasConfig
    elements: List[Element]
    
    # Optional fields
    description: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    points: Optional[Dict[str, List[float]]] = None
    measurements: Optional[MeasurementsConfig] = None
    boundary_conditions: Optional[BoundaryConditions] = None
    refinement_zones: Optional[List[RefinementZone]] = None
    extends: Optional[str] = None  # For future inheritance support


# --- Validation Helpers ---
VALID_ELEMENT_TYPES = {
    'rect', 'polygon', 'wall', 'window_detail', 
    'insulation_tapered', 'insulation'
}

VALID_MATERIALS = {
    'WALL', 'INSULATION', 'REVEAL_INS', 'STYRODUR',
    'FRAME', 'GLASS', 'AIR_INT', 'AIR_EXT',
    'ALUMINUM', 'CAVITY', 'CONCRETE', 'WOOD'
}

VALID_EDGES = {'top', 'bottom', 'left', 'right'}


def validate_scenario(data: Dict[str, Any]) -> List[str]:
    """Validate scenario data against schema.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    # Required fields
    if 'name' not in data:
        errors.append("Missing required field: 'name'")
    
    if 'canvas' not in data:
        errors.append("Missing required field: 'canvas'")
    else:
        canvas = data['canvas']
        if 'bounds' not in canvas:
            errors.append("Canvas missing 'bounds'")
        elif not isinstance(canvas['bounds'], list) or len(canvas['bounds']) != 4:
            errors.append("Canvas bounds must be a list of 4 values [x_min, x_max, y_min, y_max]")
        if 'grid' not in canvas:
            errors.append("Canvas missing 'grid' (resolution)")
    
    if 'elements' not in data:
        errors.append("Missing required field: 'elements'")
    else:
        for i, elem in enumerate(data['elements']):
            if 'type' not in elem:
                errors.append(f"Element {i}: missing 'type'")
            elif elem['type'] not in VALID_ELEMENT_TYPES:
                errors.append(f"Element {i}: unknown type '{elem['type']}'")
            
            # Validate material names
            mat = elem.get('material')
            if isinstance(mat, str) and mat not in VALID_MATERIALS:
                # Allow numeric materials (custom lambda)
                if not mat.isdigit():
                    errors.append(f"Element {i}: unknown material '{mat}'")
    
    # Validate boundary conditions if present
    if 'boundary_conditions' in data:
        bc = data['boundary_conditions']
        if 'adiabatic' in bc:
            for edge in bc['adiabatic']:
                if edge not in VALID_EDGES:
                    errors.append(f"Invalid adiabatic edge: '{edge}'")
    
    return errors

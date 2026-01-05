"""
Geometry Module for Thermal Bridge Calculations

Provides base classes and primitives for defining simulation geometry:
- CanvasConfig: Domain bounds and mesh resolution settings
- Point: Named coordinate for sketch-based definition
- PolygonShape: Arbitrary polygon defined by points
- GeometryBuilder: Abstract base for geometry implementations
- SketchGeometry: Builder for arbitrary point-and-shape based geometries
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Callable, Optional, Dict
from abc import ABC, abstractmethod
import numpy as np
from matplotlib.path import Path

# Material IDs
class MaterialID:
    """Material identifier constants for grid cells."""
    AIR_EXT = 0
    AIR_INT = 1
    WALL = 2
    INSULATION = 3
    REVEAL_INS = 4
    FRAME = 5
    GLASS = 6
    SPACER = 7
    CAVITY = 8       # Unventilated cavity (e.g. inside rails)
    STYRODUR = 9     # XPS / High-performance insulation (WLS 025/028)
    
    # ISO Test Materials
    CONCRETE = 10
    WOOD = 11
    ALUMINUM = 12


@dataclass
class CanvasConfig:
    """Defines the simulation domain bounds and mesh settings."""
    x_min_mm: float
    x_max_mm: float
    y_min_mm: float
    y_max_mm: float
    
    # Default grid resolution for uniform/coarse regions
    default_dx_mm: float = 10.0
    default_dy_mm: float = 10.0
    
    # Fine grid resolution for detail regions
    fine_dx_mm: float = 0.5
    fine_dy_mm: float = 0.5
    
    # Ultra-fine for critical interfaces (glass-frame, etc.)
    ultra_dx_mm: float = 0.25
    ultra_dy_mm: float = 0.25
    
    @property
    def width_mm(self) -> float:
        return self.x_max_mm - self.x_min_mm
    
    @property
    def height_mm(self) -> float:
        return self.y_max_mm - self.y_min_mm


@dataclass
class Point:
    """A named coordinate in 2D space."""
    x: float
    y: float
    label: str


@dataclass
class RefinementZone:
    """Defines a rectangular zone requiring finer mesh resolution."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    target_dx: float
    target_dy: float = None
    priority: int = 0
    grading: float = 1.1 # Default geometric expansion factor (1.1 = 10% growth)
    
    def __post_init__(self):
        if self.target_dy is None:
            self.target_dy = self.target_dx


@dataclass
class GeometryRegion:
    """
    Base class for specific geometry areas with material assignment.
    Compatible with the original rectangular region system.
    """
    name: str
    material_id: int
    lambda_w_mk: float = None
    
    def contains(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        """
        Returns boolean mask of points contained in this region.
        Override in subclasses.
        """
        return np.zeros_like(X, dtype=bool)
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Return (xmin, xmax, ymin, ymax) bounding box."""
        return (0, 0, 0, 0)


@dataclass
class RectangularRegion(GeometryRegion):
    """Legacy rectangular region defined by min/max bounds."""
    x_min: float = 0
    x_max: float = 0
    y_min: float = 0
    y_max: float = 0
    shape_predicate: Callable[[np.ndarray, np.ndarray], np.ndarray] = None
    
    def contains(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        rect_mask = (X >= self.x_min) & (X <= self.x_max) & \
                    (Y >= self.y_min) & (Y <= self.y_max)
        if self.shape_predicate is not None:
            return rect_mask & self.shape_predicate(X, Y)
        return rect_mask
        
    @property
    def bounds(self):
        return (self.x_min, self.x_max, self.y_min, self.y_max)


@dataclass
class PolygonShape(GeometryRegion):
    """
    Arbitrary polygon defined by a list of points.
    Uses matplotlib.path for robust point-in-polygon checks.
    """
    points: List[Point] = field(default_factory=list)
    _path: Path = field(init=False, repr=False)
    
    def __post_init__(self):
        # Create matplotlib Path for rasterization
        vertices = [(p.x, p.y) for p in self.points]
        # Close the polygon if not already closed
        if vertices[0] != vertices[-1]:
            vertices.append(vertices[0])
        self._path = Path(vertices)
        
    def contains(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        """
        Check which points in the meshgrid (X,Y) are inside the polygon.
        """
        # Flatten the arrays for efficient checking
        flat_points = np.column_stack((X.ravel(), Y.ravel()))
        
        # Use radius=0 (exact containment) or small epsilon for edge cases
        # contain_points returns boolean array
        mask_flat = self._path.contains_points(flat_points, radius=-1e-9)
        
        # Reshape back to grid dimensions
        return mask_flat.reshape(X.shape)
        
    @property
    def bounds(self):
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return (min(xs), max(xs), min(ys), max(ys))


class GeometryBuilder(ABC):
    """Abstract base class for geometry definitions."""
    
    @abstractmethod
    def get_canvas_config(self) -> CanvasConfig:
        pass
    
    @abstractmethod
    def get_regions(self) -> List[GeometryRegion]:
        pass
    
    def get_critical_x_points(self) -> List[float]:
        points = set()
        config = self.get_canvas_config()
        points.add(config.x_min_mm)
        points.add(config.x_max_mm)
        
        for region in self.get_regions():
            xmin, xmax, _, _ = region.bounds
            points.add(xmin)
            points.add(xmax)
            
            # If it's a polygon, add all vertex X coordinates
            if isinstance(region, PolygonShape):
                for p in region.points:
                    points.add(p.x)
                    
        # Add refinement zone boundaries
        for zone in self.get_refinement_zones():
            points.add(zone.x_min)
            points.add(zone.x_max)
        
        return sorted([p for p in points if config.x_min_mm <= p <= config.x_max_mm])
    
    def get_critical_y_points(self) -> List[float]:
        points = set()
        config = self.get_canvas_config()
        points.add(config.y_min_mm)
        points.add(config.y_max_mm)
        
        for region in self.get_regions():
            _, _, ymin, ymax = region.bounds
            points.add(ymin)
            points.add(ymax)
            
            # If it's a polygon, add all vertex Y coordinates
            if isinstance(region, PolygonShape):
                for p in region.points:
                    points.add(p.y)
                    
        # Add refinement zone boundaries
        for zone in self.get_refinement_zones():
            points.add(zone.y_min)
            points.add(zone.y_max)
        
        return sorted([p for p in points if config.y_min_mm <= p <= config.y_max_mm])
    
    def get_refinement_zones(self) -> List[RefinementZone]:
        return []
    
    def get_boundary_conditions(self) -> dict:
        return {
            'fixed_regions': [
                (MaterialID.AIR_INT, 20.0),
                (MaterialID.AIR_EXT, -5.0),
            ],
            'surface_resistance': {
                MaterialID.AIR_INT: 0.13,
                MaterialID.AIR_EXT: 0.04,
            }
        }
    
    def get_material_conductivity(self, material_id: int) -> float:
        # Check regions for explicit lambda
        for region in self.get_regions():
            if region.material_id == material_id and region.lambda_w_mk is not None:
                return region.lambda_w_mk
        
        defaults = {
            MaterialID.WALL: 0.81,
            MaterialID.INSULATION: 0.035,
            MaterialID.REVEAL_INS: 0.035,
            MaterialID.FRAME: 0.133,
            MaterialID.GLASS: 0.032,
            MaterialID.SPACER: 0.14,
            MaterialID.AIR_INT: 0.025,
            MaterialID.AIR_EXT: 0.025,
            MaterialID.CONCRETE: 1.15,
            MaterialID.WOOD: 0.12,
            MaterialID.ALUMINUM: 230.0,
        }
        return defaults.get(material_id, 0.025)

    def get_material_density(self, material_id: int) -> float:
        defaults = {
            MaterialID.WALL: 1800.0,
            MaterialID.INSULATION: 20.0,
            MaterialID.REVEAL_INS: 20.0,
            MaterialID.FRAME: 500.0,
            MaterialID.GLASS: 2500.0,
            MaterialID.SPACER: 1000.0,
            MaterialID.AIR_INT: 1.2,
            MaterialID.AIR_EXT: 1.2,
            MaterialID.CONCRETE: 2400.0,
            MaterialID.WOOD: 500.0,
            MaterialID.ALUMINUM: 2700.0,
        }
        return defaults.get(material_id, 1000.0)

    def get_material_heat_capacity(self, material_id: int) -> float:
        defaults = {
            MaterialID.WALL: 1000.0,
            MaterialID.INSULATION: 1400.0,
            MaterialID.REVEAL_INS: 1400.0,
            MaterialID.FRAME: 1000.0,
            MaterialID.GLASS: 840.0,
            MaterialID.SPACER: 1000.0,
            MaterialID.AIR_INT: 1000.0,
            MaterialID.AIR_EXT: 1000.0,
            MaterialID.CONCRETE: 1000.0,
            MaterialID.WOOD: 1600.0,
            MaterialID.ALUMINUM: 900.0,
        }
        return defaults.get(material_id, 1000.0)



class SketchGeometry(GeometryBuilder):
    """
    Sketch-based geometry defined by named points and shapes.
    Enables arbitrary polygon definition (A-B-C-D).
    """
    
    def __init__(self):
        self.points: Dict[str, Point] = {}
        self.shapes: List[PolygonShape] = []
        self._canvas_override: Optional[CanvasConfig] = None
        
    def add_point(self, label: str, x: float, y: float):
        """Define a named point."""
        self.points[label] = Point(x, y, label)
        
    def add_shape(self, point_labels: List[str], material_id: int, 
                  lambda_val: float = None, name: str = None):
        """
        Define a shape as a sequence of point labels.
        e.g. ["A", "B", "C", "D"]
        """
        poly_points = []
        for lbl in point_labels:
            if lbl not in self.points:
                raise ValueError(f"Point '{lbl}' not defined")
            poly_points.append(self.points[lbl])
            
        if name is None:
            name = f"Shape_{len(self.shapes)+1}"
            
        shape = PolygonShape(
            name=name,
            material_id=material_id,
            lambda_w_mk=lambda_val,
            points=poly_points
        )
        self.shapes.append(shape)
        
    def set_canvas(self, x_min, x_max, y_min, y_max, grid_mm=10.0):
        """Override canvas bounds."""
        self._canvas_override = CanvasConfig(
            x_min_mm=x_min, x_max_mm=x_max,
            y_min_mm=y_min, y_max_mm=y_max,
            default_dx_mm=grid_mm,
            default_dy_mm=grid_mm,
            fine_dx_mm=grid_mm/5,
            fine_dy_mm=grid_mm/5
        )
        
    def get_canvas_config(self) -> CanvasConfig:
        if self._canvas_override:
            return self._canvas_override
            
        # Auto-compute bounds from points with 10% padding
        all_x = [p.x for p in self.points.values()]
        all_y = [p.y for p in self.points.values()]
        
        if not all_x:
            return CanvasConfig(0, 100, 0, 100) # Default
            
        dx = max(all_x) - min(all_x)
        dy = max(all_y) - min(all_y)
        padding_x = max(10, dx * 0.1)
        padding_y = max(10, dy * 0.1)
        
        return CanvasConfig(
            x_min_mm=min(all_x) - padding_x,
            x_max_mm=max(all_x) + padding_x,
            y_min_mm=min(all_y) - padding_y,
            y_max_mm=max(all_y) + padding_y
        )
        
    def get_regions(self) -> List[GeometryRegion]:
        return self.shapes


def build_material_grid(geometry: GeometryBuilder, 
                        xc: np.ndarray, 
                        yc: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build material ID and conductivity grids from backend.core.geometry definition.
    """
    ny, nx = len(yc), len(xc)
    X, Y = np.meshgrid(xc, yc)
    
    grid_map = np.zeros((ny, nx), dtype=int)
    cond = np.zeros((ny, nx), dtype=float)
    
    # Initialize with default value (AIR_EXT = 0)
    grid_map[:] = MaterialID.AIR_EXT
    cond[:] = geometry.get_material_conductivity(MaterialID.AIR_EXT)
    
    # Apply regions
    for region in geometry.get_regions():
        # PolygonShape.contains uses matplotlib.path for accurate rasterization
        mask = region.contains(X, Y)
        
        grid_map[mask] = region.material_id
        
        if region.lambda_w_mk is not None:
            cond[mask] = region.lambda_w_mk
        else:
            cond[mask] = geometry.get_material_conductivity(region.material_id)
    
    return grid_map, cond


def build_transient_grid(geometry: GeometryBuilder, 
                         grid_map: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build density and heat capacity grids based on material map.
    Returns (density_grid, capacity_grid)
    """
    ny, nx = grid_map.shape
    
    rho = np.zeros((ny, nx), dtype=float)
    cp = np.zeros((ny, nx), dtype=float)
    
    unique_ids = np.unique(grid_map)
    
    for mid in unique_ids:
        mask = (grid_map == mid)
        rho[mask] = geometry.get_material_density(mid)
        cp[mask] = geometry.get_material_heat_capacity(mid)
        
    return rho, cp

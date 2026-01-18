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
    grading: float = 1.0 # Default uniform refinement (1.0 = no expansion)
    
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


def compute_cell_coverage(
    x_center: float, 
    y_center: float, 
    dx: float, 
    dy: float, 
    regions: List[GeometryRegion],
    n_samples: int = 4
) -> Dict[int, float]:
    """
    Compute fractional coverage of each material within a cell using sub-sampling.
    
    Args:
        x_center: Cell center X coordinate
        y_center: Cell center Y coordinate
        dx: Cell width
        dy: Cell height
        regions: List of geometry regions (checked in order, last wins)
        n_samples: Number of sample points per dimension (NxN grid)
        
    Returns:
        Dictionary mapping material_id -> fractional coverage (0.0 to 1.0)
    """
    # Generate sub-sample points within the cell
    half_dx = dx / 2
    half_dy = dy / 2
    
    # Create NxN sample grid
    x_offsets = np.linspace(-half_dx + dx/(2*n_samples), half_dx - dx/(2*n_samples), n_samples)
    y_offsets = np.linspace(-half_dy + dy/(2*n_samples), half_dy - dy/(2*n_samples), n_samples)
    
    sample_x = x_center + x_offsets
    sample_y = y_center + y_offsets
    X_sub, Y_sub = np.meshgrid(sample_x, sample_y)
    
    # Initialize all samples as AIR_EXT
    sample_materials = np.full((n_samples, n_samples), MaterialID.AIR_EXT, dtype=int)
    
    # Apply regions in order (last region wins for overlapping areas)
    for region in regions:
        mask = region.contains(X_sub, Y_sub)
        sample_materials[mask] = region.material_id
    
    # Count occurrences of each material
    total_samples = n_samples * n_samples
    unique, counts = np.unique(sample_materials, return_counts=True)
    
    coverage = {}
    for mat_id, count in zip(unique, counts):
        coverage[int(mat_id)] = count / total_samples
        
    return coverage


def build_material_grid_averaged(
    geometry: GeometryBuilder, 
    xc: np.ndarray, 
    yc: np.ndarray,
    n_samples: int = 4
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build material ID and conductivity grids with sub-cell averaging for boundary cells.
    
    For cells that span multiple materials (diagonal boundaries), computes the
    harmonic mean of conductivities weighted by coverage fraction. This is 
    appropriate for heat flow perpendicular to the interface (series resistance).
    
    Args:
        geometry: GeometryBuilder instance providing regions and material properties
        xc: 1D array of cell center X coordinates
        yc: 1D array of cell center Y coordinates
        n_samples: Sub-sampling grid size per dimension (default 4 = 16 samples)
        
    Returns:
        Tuple of (grid_map, cond, is_averaged):
        - grid_map: 2D array of dominant material IDs (ny, nx)
        - cond: 2D array of conductivity values (W/mK), averaged at boundaries
        - is_averaged: 2D boolean array marking cells where averaging was applied
    """
    ny, nx = len(yc), len(xc)
    
    grid_map = np.zeros((ny, nx), dtype=int)
    cond = np.zeros((ny, nx), dtype=float)
    is_averaged = np.zeros((ny, nx), dtype=bool)
    
    # Get cell sizes (assumes uniform grid; use average for non-uniform)
    if nx > 1:
        dx = np.mean(np.diff(xc))
    else:
        dx = 1.0
    if ny > 1:
        dy = np.mean(np.diff(yc))
    else:
        dy = 1.0
        
    regions = geometry.get_regions()
    
    for j in range(ny):
        for i in range(nx):
            x_c = xc[i]
            y_c = yc[j]
            
            # Compute coverage for this cell
            coverage = compute_cell_coverage(x_c, y_c, dx, dy, regions, n_samples)
            
            if len(coverage) == 0:
                # Shouldn't happen, but fallback to AIR_EXT
                grid_map[j, i] = MaterialID.AIR_EXT
                cond[j, i] = geometry.get_material_conductivity(MaterialID.AIR_EXT)
                
            elif len(coverage) == 1:
                # Single material - direct assignment (no averaging needed)
                mat_id = list(coverage.keys())[0]
                grid_map[j, i] = mat_id
                
                # Get conductivity from region if specified, else from geometry
                lambda_val = None
                for region in regions:
                    if region.material_id == mat_id and region.lambda_w_mk is not None:
                        lambda_val = region.lambda_w_mk
                        break
                        
                if lambda_val is not None:
                    cond[j, i] = lambda_val
                else:
                    cond[j, i] = geometry.get_material_conductivity(mat_id)
                    
            else:
                # Multiple materials - use weighted harmonic mean
                is_averaged[j, i] = True
                
                # Dominant material for grid_map (highest coverage)
                dominant_mat = max(coverage, key=coverage.get)
                grid_map[j, i] = dominant_mat
                
                # Compute harmonic mean: 1/λ_eff = Σ(f_i / λ_i)
                inv_lambda_sum = 0.0
                for mat_id, frac in coverage.items():
                    # Get conductivity for this material
                    lambda_val = None
                    for region in regions:
                        if region.material_id == mat_id and region.lambda_w_mk is not None:
                            lambda_val = region.lambda_w_mk
                            break
                    
                    if lambda_val is None:
                        lambda_val = geometry.get_material_conductivity(mat_id)
                    
                    # Add to harmonic mean calculation
                    if lambda_val > 0:
                        inv_lambda_sum += frac / lambda_val
                        
                # Compute effective conductivity
                if inv_lambda_sum > 0:
                    cond[j, i] = 1.0 / inv_lambda_sum
                else:
                    cond[j, i] = geometry.get_material_conductivity(dominant_mat)
    
    return grid_map, cond, is_averaged

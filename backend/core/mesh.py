"""
Mesh Module for Thermal Bridge Calculations

Provides adaptive mesh generation based on geometry hints:
- AdaptiveMesh: Non-uniform rectilinear mesh with refinement zones
- UniformMesh: Simple uniform grid for simpler cases
"""

import numpy as np
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.core.geometry import GeometryBuilder


class AdaptiveMesh:
    """
    Generates non-uniform rectilinear mesh from backend.core.geometry hints.
    
    The mesh is constructed by:
    1. Collecting critical X/Y points from backend.core.geometry (material boundaries)
    2. Filling intervals between critical points with appropriate resolution
    3. Applying refinement zones for higher density in detail areas
    
    Attributes:
        x_coords: 1D array of cell face X coordinates (mm)
        y_coords: 1D array of cell face Y coordinates (mm)
        xc: 1D array of cell center X coordinates (mm)
        yc: 1D array of cell center Y coordinates (mm)
        dx_array: 1D array of cell widths (mm)
        dy_array: 1D array of cell heights (mm)
        nx: Number of cells in X direction
        ny: Number of cells in Y direction
    """
    
    def __init__(self, geometry: 'GeometryBuilder'):
        self.geometry = geometry
        self.x_coords = None
        self.y_coords = None
        self.xc = None
        self.yc = None
        self.dx_array = None
        self.dy_array = None
        self.nx = 0
        self.ny = 0
        self._generated = False
        
    def generate(self):
        """Build the mesh based on geometry configuration."""
        if self._generated:
            return
            
        config = self.geometry.get_canvas_config()
        crit_x = self.geometry.get_critical_x_points()
        crit_y = self.geometry.get_critical_y_points()
        refine_zones = self.geometry.get_refinement_zones()
        
        # Build X coordinates
        self.x_coords = self._build_coords_1d(
            crit_x, 
            config.x_min_mm, 
            config.x_max_mm,
            config.default_dx_mm,
            [(z.x_min, z.x_max, z.target_dx, z.priority) for z in refine_zones]
        )
        
        # Build Y coordinates
        self.y_coords = self._build_coords_1d(
            crit_y,
            config.y_min_mm,
            config.y_max_mm,
            config.default_dy_mm,
            [(z.y_min, z.y_max, z.target_dy, z.priority) for z in refine_zones]
        )
        
        # Compute cell properties
        self.dx_array = np.diff(self.x_coords)
        self.dy_array = np.diff(self.y_coords)
        self.xc = (self.x_coords[:-1] + self.x_coords[1:]) / 2.0
        self.yc = (self.y_coords[:-1] + self.y_coords[1:]) / 2.0
        self.nx = len(self.xc)
        self.ny = len(self.yc)
        
        self._generated = True
        
    def _build_coords_1d(self, 
                         critical_points: List[float],
                         coord_min: float,
                         coord_max: float,
                         default_dh: float,
                         refinement_1d: List[Tuple[float, float, float, int]]
                        ) -> np.ndarray:
        """
        Build 1D coordinate array with refinement.
        
        Args:
            critical_points: Points where mesh nodes should align
            coord_min, coord_max: Domain bounds
            default_dh: Default cell size
            refinement_1d: List of (min, max, target_dh, priority) tuples
            
        Returns:
            1D numpy array of face coordinates
        """
        # Ensure bounds are in critical points
        crit = sorted(set(critical_points) | {coord_min, coord_max})
        crit = [p for p in crit if coord_min <= p <= coord_max]
        
        coords = [crit[0]]
        
        for i in range(len(crit) - 1):
            start = crit[i]
            end = crit[i + 1]
            dist = end - start
            
            if dist <= 1e-9:
                continue
                
            # Determine target resolution for this interval
            # Check if interval overlaps any refinement zone
            target_dh = default_dh
            best_priority = -1
            
            for r_min, r_max, r_dh, r_priority in refinement_1d:
                # Check overlap
                if start < r_max and end > r_min:
                    if r_priority > best_priority:
                        target_dh = r_dh
                        best_priority = r_priority
            
            # Subdivide interval
            n_cells = max(1, int(np.ceil(dist / target_dh)))
            steps = np.linspace(start, end, n_cells + 1)
            
            for s in steps[1:]:
                coords.append(s)
        
        return np.array(coords)
    
    @property
    def width_mm(self) -> float:
        """Total domain width in mm."""
        return self.x_coords[-1] - self.x_coords[0]
    
    @property
    def height_mm(self) -> float:
        """Total domain height in mm."""
        return self.y_coords[-1] - self.y_coords[0]
    
    def get_meshgrid(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return 2D arrays of cell center coordinates (X, Y)."""
        return np.meshgrid(self.xc, self.yc)
    
    def info(self) -> str:
        """Return summary string of mesh properties."""
        if not self._generated:
            return "Mesh not generated"
        return (f"AdaptiveMesh: {self.nx} x {self.ny} cells "
                f"({self.width_mm:.1f} x {self.height_mm:.1f} mm)")


class UniformMesh:
    """
    Simple uniform rectilinear mesh.
    
    Use for simple geometries or when adaptive meshing is not needed.
    """
    
    def __init__(self, geometry: 'GeometryBuilder', grid_size_mm: float = None):
        self.geometry = geometry
        self.grid_size_mm = grid_size_mm
        self.x_coords = None
        self.y_coords = None
        self.xc = None
        self.yc = None
        self.dx_array = None
        self.dy_array = None
        self.nx = 0
        self.ny = 0
        self._generated = False
        
    def generate(self):
        """Build uniform mesh from canvas bounds."""
        if self._generated:
            return
            
        config = self.geometry.get_canvas_config()
        
        # Use provided grid size or default from canvas
        dh = self.grid_size_mm if self.grid_size_mm else config.default_dx_mm
        
        # Build coordinates
        self.x_coords = np.arange(config.x_min_mm, config.x_max_mm + dh, dh)
        self.y_coords = np.arange(config.y_min_mm, config.y_max_mm + dh, dh)
        
        # Ensure we don't exceed bounds
        if self.x_coords[-1] > config.x_max_mm + 1e-6:
            self.x_coords = self.x_coords[:-1]
        if self.y_coords[-1] > config.y_max_mm + 1e-6:
            self.y_coords = self.y_coords[:-1]
            
        self.nx = len(self.x_coords) - 1
        self.ny = len(self.y_coords) - 1
        
        self.dx_array = np.full(self.nx, dh)
        self.dy_array = np.full(self.ny, dh)
        
        self.xc = (self.x_coords[:-1] + self.x_coords[1:]) / 2.0
        self.yc = (self.y_coords[:-1] + self.y_coords[1:]) / 2.0
        
        self._generated = True
        
    @property
    def width_mm(self) -> float:
        return self.x_coords[-1] - self.x_coords[0]
    
    @property
    def height_mm(self) -> float:
        return self.y_coords[-1] - self.y_coords[0]
    
    def get_meshgrid(self) -> Tuple[np.ndarray, np.ndarray]:
        return np.meshgrid(self.xc, self.yc)
    
    def info(self) -> str:
        if not self._generated:
            return "Mesh not generated"
        return (f"UniformMesh: {self.nx} x {self.ny} cells "
                f"({self.width_mm:.1f} x {self.height_mm:.1f} mm), "
                f"dh={self.grid_size_mm:.2f}mm")

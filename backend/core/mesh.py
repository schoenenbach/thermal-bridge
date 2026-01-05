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
            [(z.x_min, z.x_max, z.target_dx, z.priority, z.grading) for z in refine_zones]
        )
        
        # Build Y coordinates
        self.y_coords = self._build_coords_1d(
            crit_y,
            config.y_min_mm,
            config.y_max_mm,
            config.default_dy_mm,
            [(z.y_min, z.y_max, z.target_dy, z.priority, z.grading) for z in refine_zones]
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
                         refinement_1d: List[Tuple[float, float, float, int, float]]
                        ) -> np.ndarray:
        """
        Build 1D coordinate array with refinement and grading.
        
        Args:
            critical_points: Points where mesh nodes should align
            coord_min, coord_max: Domain bounds
            default_dh: Default cell size
            refinement_1d: List of (min, max, target_dh, priority, grading) tuples
            
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
                
            # Determine params for this interval
            target_dh = default_dh
            grading = 1.05 # Default grading if slightly allowed? Or stick to uniform?
            # Stick to uniform (1.0) unless specified otherwise to prevent unexpected drift
            grading = 1.0 
            
            best_priority = -1
            
            # Check overlap with refinement zones
            for r_min, r_max, r_dh, r_priority, r_grading in refinement_1d:
                # Interval is fully or partially inside zone?
                # Usually we refine if the interval is "of interest".
                # Simplification: If center of interval is in zone
                mid = (start + end) / 2
                if mid >= r_min and mid <= r_max:
                    if r_priority > best_priority:
                        target_dh = r_dh
                        best_priority = r_priority
                        grading = r_grading
            
            # Generate points for this interval
            # Case 1: Uniform
            if abs(grading - 1.0) < 1e-3:
                n_cells = max(1, int(np.ceil(dist / target_dh)))
                # Adjust dh to fit exactly
                actual_dh = dist / n_cells
                for k in range(n_cells):
                    coords.append(start + (k+1)*actual_dh)
            else:
                # Case 2: Graded (Geometric Expansion)
                # We want to start with target_dh at both ends (if adjacent to other crit points?)
                # Or just start with target_dh and expand towards center?
                # WUFI strategy: Expand from critical edges.
                # Since 'start' and 'end' are critical points, we should be fine at boundaries.
                # Problem: How to expand from BOTH sides to the middle? 
                # Or is this interval just one-way?
                # Usually critical points define the rigid features.
                # We should refine near start and end, and coarse in middle.
                # "Double Grading"
                
                # Check required space for 2 steps
                if dist < 2 * target_dh:
                    # Too small to grade, just uniform
                     n_cells = max(1, int(np.ceil(dist / target_dh)))
                     actual_dh = dist / n_cells
                     for k in range(n_cells):
                         coords.append(start + (k+1)*actual_dh)
                     continue
                
                # Iterative generation from both sides
                pts_left = []
                pts_right = []
                
                curr_dx = target_dh
                curr_pos = start
                
                # Forward from start
                rem_dist = dist
                while rem_dist > 0:
                    pts_left.append(curr_pos + curr_dx)
                    curr_pos += curr_dx
                    rem_dist -= curr_dx
                    curr_dx *= grading
                    # Cap at default_dh to avoid over-coarsening?
                    if curr_dx > default_dh: curr_dx = default_dh
                
                # If we overshot, we need to reconcile.
                # Simpler approach: Calculate number of steps N such that sum(geometric series) ~ dist
                # But double sided is tricky.
                
                # Alternative: Explicit "Graded Interval" generator
                # 1. Generate normalized spacing 1, r, r^2 ... until sum > dist/2
                # 2. Mirror for other side
                # 3. Scale to fit exactly
                
                # Let's try a robust "fill with expansion"
                # Generate points from left
                xs = [start]
                dx = target_dh
                while xs[-1] + dx < end - target_dh/2: # stop before end
                    next_x = xs[-1] + dx
                    # Check if we passed midpoint?
                    # If we passed midpoint, we should match the sequence coming from the right?
                    xs.append(next_x)
                    dx *= grading
                    if dx > default_dh: dx = default_dh
                
                # This is one-sided expansion.
                # Ideally we want symmetric if start/end are both critical.
                # If best_priority was triggered by a zone, it implies high res needed entire zone?
                # No, grading is usually used OUTSIDE refinement zones.
                # But here we are applying grading INSIDE an interval between critical points.
                # If this interval is "Wall core", we want fine near surface, coarse in center.
                
                # Let's assume symmetric expansion from start and end towards center.
                left_pts = [start]
                right_pts = [end]
                
                ldx = target_dh
                rdx = target_dh
                
                # While gap exists
                while (right_pts[-1] - left_pts[-1]) > (ldx + rdx): # heuristic check
                    # Add point from left
                    left_pts.append(left_pts[-1] + ldx)
                    ldx *= grading
                    if ldx > default_dh: ldx = default_dh
                    
                    if (right_pts[-1] - left_pts[-1]) <= rdx: break # Check overlap
                    
                    # Add point from right
                    right_pts.append(right_pts[-1] - rdx)
                    rdx *= grading
                    if rdx > default_dh: rdx = default_dh
                    
                # Fill the remaining gap with uniform steps
                gap_start = left_pts[-1]
                gap_end = right_pts[-1]
                gap = gap_end - gap_start
                
                # Use the average of last dx values as step size for gap
                avg_dx = (ldx + rdx) / 2
                if grading > 1 and gap > avg_dx: 
                     # slightly squash or stretch?
                     n_gap = max(1, int(round(gap / avg_dx)))
                     gap_step = gap / n_gap
                     for k in range(n_gap):
                         left_pts.append(gap_start + (k+1)*gap_step)
                else: 
                     # Just close it?
                     pass # gap is covered by merge
                     
                # Sort and uniq (right_pts are descending, so reverse)
                # Combine
                right_pts.pop(0) # Remove 'end' which is duplicate if we merge carefully? 
                # Actually right_pts has 'end' at index 0. 
                # We generated: end, end-dx..
                
                # Merging
                full_pts = left_pts + sorted(right_pts)
                
                # Sanity check: Ensure monotonic and within bounds
                full_pts = sorted(list(set(full_pts))) # Dedupe boundaries
                full_pts = [p for p in full_pts if p >= start and p <= end]
                
                # Fix exact end point floating point issues
                if abs(full_pts[-1] - end) > 1e-9:
                     full_pts.append(end)
                     
                coords.extend(full_pts[1:]) # Skip start as it matches prev coords[-1]
        
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

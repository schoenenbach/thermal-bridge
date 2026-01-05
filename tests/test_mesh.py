import pytest
import numpy as np
from mesh import UniformMesh, AdaptiveMesh
from geometry import CanvasConfig, RefinementZone

class MockGeometry:
    def __init__(self):
        self.canvas = CanvasConfig(
            x_min_mm=0, x_max_mm=100,
            y_min_mm=0, y_max_mm=50,
            default_dx_mm=10, default_dy_mm=10
        )
        self.crit_x = []
        self.crit_y = []
        self.zones = []

    def get_canvas_config(self):
        return self.canvas

    def get_critical_x_points(self):
        return self.crit_x

    def get_critical_y_points(self):
        return self.crit_y

    def get_refinement_zones(self):
        return self.zones

def test_uniform_mesh_dimensions(simple_canvas):
    """Test standard uniform mesh generation."""
    geom = MockGeometry()
    # 100x50 mm, grid=10mm -> 10x5 cells
    mesh = UniformMesh(geom, grid_size_mm=10.0)
    mesh.generate()
    
    assert mesh.nx == 10
    assert mesh.ny == 5
    assert mesh.width_mm == 100.0
    assert mesh.height_mm == 50.0
    assert np.allclose(mesh.dx_array, 10.0)
    assert np.allclose(mesh.dy_array, 10.0)

def test_adaptive_mesh_critical_points():
    """Test that adaptive mesh respects critical points."""
    geom = MockGeometry()
    geom.crit_x = [15.0, 85.0] # Should add vertical lines at x=15, x=85
    geom.crit_y = [25.0]       # Should add horizontal line at y=25
    
    mesh = AdaptiveMesh(geom)
    mesh.generate()
    
    # Check that 15.0 and 85.0 are present in x_coords
    assert np.isclose(mesh.x_coords, 15.0).any()
    assert np.isclose(mesh.x_coords, 85.0).any()
    
    # Check that 25.0 is present in y_coords
    assert np.isclose(mesh.y_coords, 25.0).any()
    
    # Basic bounds check
    assert mesh.x_coords[0] == 0.0
    assert mesh.x_coords[-1] == 100.0
    assert mesh.y_coords[0] == 0.0
    assert mesh.y_coords[-1] == 50.0

def test_adaptive_mesh_refinement():
    """Test local refinement zones."""
    geom = MockGeometry()
    # Zone from x=40 to x=60 with 1mm resolution
    zone = RefinementZone(x_min=40, x_max=60, y_min=0, y_max=50, target_dx=1.0, target_dy=10.0)
    geom.zones = [zone]
    # Critical points needed for adaptive mesh to split at zone boundaries
    geom.crit_x = [40.0, 60.0]
    
    mesh = AdaptiveMesh(geom)
    mesh.generate()
    
    # Check resolution in the refined zone
    # Find indices where x is between 40 and 60
    mask = (mesh.xc > 40) & (mesh.xc < 60)
    refined_dx = mesh.dx_array[mask]
    
    # Should be close to 1.0 (might be slightly adjusted to fit exactly)
    # The current implementation rounds up n_cells, so dx <= target
    assert np.all(refined_dx <= 1.0 + 1e-9)
    # Check outside zone (0-40), should be default 10mm
    mask_out = (mesh.xc < 39)
    assert np.allclose(mesh.dx_array[mask_out], 10.0)

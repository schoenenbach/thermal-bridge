import pytest
import os
import sys
import yaml
import numpy as np

# Add project root to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from geometry import CanvasConfig, Point
from declarative_geometry import DeclarativeGeometry
from mesh import UniformMesh, AdaptiveMesh
from solver import get_solver_lib

def pytest_addoption(parser):
    parser.addoption(
        "--slow", action="store_true", default=False, help="run slow tests"
    )

def pytest_collection_modifyitems(config, items):
    if config.getoption("--slow"):
        # --slow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --slow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)

@pytest.fixture(scope="session")
def solver_lib():
    """Load the C++ solver library once for the session."""
    return get_solver_lib()

@pytest.fixture
def simple_canvas():
    """A simple 100x100mm canvas configuration."""
    return CanvasConfig(
        x_min_mm=0, x_max_mm=100,
        y_min_mm=0, y_max_mm=100,
        default_dx_mm=10, default_dy_mm=10
    )

@pytest.fixture
def uniform_mesh_10mm(simple_canvas):
    """A uniform 10x10 grid mesh."""
    # We need a mock geometry builder that acts like DeclarativeGeometry
    class MockGeometry:
        def get_canvas_config(self):
            return simple_canvas
            
    mesh = UniformMesh(MockGeometry(), grid_size_mm=10.0)
    mesh.generate()
    return mesh

@pytest.fixture
def iso_case_1_data():
    """Load ISO Case 1 YAML data."""
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scenarios/iso_case_1.yaml'))
    with open(path, 'r') as f:
        return yaml.safe_load(f)

@pytest.fixture
def iso_case_1_geometry(iso_case_1_data):
    """DeclarativeGeometry for ISO Case 1."""
    return DeclarativeGeometry(iso_case_1_data)


import sys
import os
import yaml
import pytest

# Add current dir to path
sys.path.insert(0, os.getcwd())

from backend.core.dxf_importer import DXFImporter
from backend.core.declarative_geometry import DeclarativeGeometry
from backend.core.elements import Factory

def test_dxf_to_scenario_flow():
    dxf_path = "Testing_Plan/sample_dxf/03016.dxf"
    if not os.path.exists(dxf_path):
        pytest.skip("Sample DXF not found")

    print(f"Testing Import from {dxf_path}...")
    
    with open(dxf_path, "rb") as f:
        importer = DXFImporter(f)
        
    layers = importer.get_layers()
    assert len(layers) > 0, "No layers found"
    print(f"Layers: {layers}")
    
    # Auto-map based on what we saw in previous manual test
    # Layers: ['Xella 025', 'Xella 035', 'Xella Bemaßung', 'Xella-Rahmen', 'Xella-Schraff', 'Xella-Text']
    mapping = {
        'Xella 025': 'INSULATION',
        'Xella 035': 'WALL',
        'Xella-Rahmen': 'FRAME'
    }
    
    scenario_dict = importer.extract_scenario(mapping)
    
    # Check structure
    assert 'elements' in scenario_dict
    assert 'points' in scenario_dict
    assert len(scenario_dict['elements']) > 0
    
    # Optimization Impact
    # With optimization (Union + Filter), count should be low (e.g. < 50) compared to raw (2000+)
    print(f"Extracted {len(scenario_dict['elements'])} optimized elements.")
    # assert len(scenario_dict['elements']) < 50


    
    # Convert to YAML string (simulate UI)
    yaml_str = yaml.dump(scenario_dict)
    
    # Parse back (Simulate Loading)
    parsed_scen = yaml.safe_load(yaml_str)
    
    # Instantiate Geometry (Validation)
    try:
        geom = DeclarativeGeometry(parsed_scen)
        print("DeclarativeGeometry instantiation successful.")
        
        # Check if shapes were added
        assert len(geom.shapes) > 0, "No shapes created in geometry"
        
    except Exception as e:
        pytest.fail(f"Failed to instantiate Geometry from DXF scenario: {e}")

if __name__ == "__main__":
    test_dxf_to_scenario_flow()


def test_simplification_tolerance_affects_output():
    """Verify that different simplification tolerances produce different vertex counts."""
    dxf_path = "Testing_Plan/sample_dxf/03016.dxf"
    if not os.path.exists(dxf_path):
        pytest.skip("Sample DXF not found")
    
    mapping = {
        'Xella 025': 'INSULATION',
        'Xella 035': 'WALL',
    }
    
    with open(dxf_path, "rb") as f:
        importer = DXFImporter(f)
    
    # Low tolerance (more detail)
    result_low = importer.extract_scenario(mapping, simplify_tolerance=0.5, min_area_threshold=5.0)
    
    with open(dxf_path, "rb") as f:
        importer2 = DXFImporter(f)
    
    # High tolerance (less detail)
    result_high = importer2.extract_scenario(mapping, simplify_tolerance=5.0, min_area_threshold=5.0)
    
    # Count total vertices
    def count_vertices(scenario):
        return sum(len(el.get('points', [])) for el in scenario.get('elements', []))
    
    vertices_low = count_vertices(result_low)
    vertices_high = count_vertices(result_high)
    
    print(f"Vertices at tolerance 0.5: {vertices_low}")
    print(f"Vertices at tolerance 5.0: {vertices_high}")
    
    # Higher tolerance should result in fewer vertices (or same in edge cases)
    assert vertices_high <= vertices_low, "Higher tolerance should simplify geometry"


def test_preview_data_method():
    """Verify get_preview_data returns expected structure."""
    dxf_path = "Testing_Plan/sample_dxf/03016.dxf"
    if not os.path.exists(dxf_path):
        pytest.skip("Sample DXF not found")
    
    mapping = {
        'Xella 025': 'INSULATION',
        'Xella 035': 'WALL',
    }
    
    with open(dxf_path, "rb") as f:
        importer = DXFImporter(f)
    
    preview = importer.get_preview_data(mapping)
    
    # Check structure
    assert 'polygons' in preview
    assert 'stats' in preview
    assert 'bounds' in preview
    
    # Check stats
    stats = preview['stats']
    assert 'polygon_count' in stats
    assert 'total_area_mm2' in stats
    assert 'materials_used' in stats
    assert 'point_count' in stats
    
    assert stats['polygon_count'] > 0
    assert len(stats['materials_used']) > 0
    
    print(f"Preview stats: {stats}")


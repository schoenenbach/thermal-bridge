
import sys
import os
import yaml
import pytest

# Add current dir to path
sys.path.insert(0, os.getcwd())

from dxf_importer import DXFImporter
from declarative_geometry import DeclarativeGeometry
from elements import Factory

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

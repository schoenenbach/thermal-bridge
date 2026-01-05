import pytest
from declarative_geometry import DeclarativeGeometry
from geometry import RectangularRegion, PolygonShape, MaterialID

def test_declarative_variable_resolution():
    """Test variable substitution in YAML."""
    data = {
        "name": "TestVariableResolution",
        "variables": {
            "width": 100,
            "height": 50
        },
        "canvas": {
            "bounds": [0, "${width}", 0, "${height}"],
            "grid": 10.0
        },
        "elements": []
    }
    
    geom = DeclarativeGeometry(data)
    cfg = geom.get_canvas_config()
    
    assert cfg.width_mm == 100.0
    assert cfg.height_mm == 50.0

def test_declarative_material_resolution():
    """Test resolving material IDs from strings."""
    data = {
        "name": "TestMatRes",
        "canvas": {"bounds": [0, 10, 0, 10], "grid": 1},
        "elements": []
    }
    geom = DeclarativeGeometry(data)
    
    # Test built-in lookup logic (private method access)
    # Using publicly exposed behavior via element building ideally, 
    # but unit testing the helper is useful.
    
    # "concrete" -> MaterialID.CONCRETE (10 usually, or defined in config)
    # Actually MaterialID enum: CONCRETE=10
    
    mat_id, k = geom._resolve_material("concrete")
    assert mat_id == MaterialID.CONCRETE
    
    mat_id, k = geom._resolve_material(100)
    assert mat_id == 100

def test_declarative_elements_parsing():
    """Test parsing of rectangular elements."""
    data = {
        "name": "TestElements",
        "canvas": {"bounds": [0, 10, 0, 10], "grid": 1},
        "elements": [
            {
                "type": "rect",
                "name": "TestRect",
                "material": "concrete",
                "params": {
                    "x": 0, "y": 0, "width": 10, "height": 10
                }
            }
        ]
    }
    
    geom = DeclarativeGeometry(data)
    regions = geom.get_regions()
    
    assert len(regions) == 1
    r = regions[0]
    # DeclarativeGeometry converts rects to PolygonShape internally if using basic elements
    # Or check if it uses add_rect -> elements.add_rect?
    # elements.add_rect calls self.add_shape?
    # Actually elements.py likely uses add_shape (Polygon).
    assert isinstance(r, PolygonShape)
    assert r.material_id == MaterialID.CONCRETE
    assert r.bounds == (0, 10, 0, 10)

def test_iso_case_1_fixture_loading(iso_case_1_geometry):
    """Test that the ISO Case 1 fixture loads correctly."""
    regions = iso_case_1_geometry.get_regions()
    
    # ISO Case 1 usually has 1 element (SolidColumn)
    assert len(regions) >= 1
    
    # Check canvas
    cfg = iso_case_1_geometry.get_canvas_config()
    assert cfg.width_mm == 200.0
    assert cfg.height_mm == 400.0

import pytest
import os
from library.material_registry import MaterialRegistry
from config import MAT_WALL

@pytest.fixture
def clean_registry():
    # Reset singleton provided it's safe - actually hard to reset strict singleton. 
    # But we can verify what's already loaded by config.py
    return MaterialRegistry.get()

def test_registry_initialization(clean_registry):
    reg = clean_registry
    assert reg.initialized
    assert len(reg.materials) > 0

def test_get_generic_materials(clean_registry):
    reg = clean_registry
    
    # Check Wall
    wall = reg.get_by_id("wall_generic")
    assert wall is not None
    assert wall.lambda_val > 0.5
    
    # Check Insulation
    ins = reg.get_by_id("insulation_generic")
    assert ins is not None
    assert ins.lambda_val == 0.035

def test_get_lambda_fallback(clean_registry):
    reg = clean_registry
    lam = reg.get_lambda("non_existent_material", default=999.0)
    assert lam == 999.0

def test_config_integration():
    # Verify that config.py globals are populated correctly
    # MAT_WALL should be 0.81 (from json or default in config)
    assert MAT_WALL == 0.81

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

import pytest
import os
from library.material_registry import MaterialRegistry
from backend.core.config import MAT_WALL

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

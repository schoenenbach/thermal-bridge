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
Unit tests for RoomProfileRegistry.

Tests cover:
- Registry initialization and JSON loading
- Profile lookup by ID and name
- Boundary condition generation
- Specific profile validations
"""

import pytest
import os
import tempfile
import json

from library.room_profile_registry import RoomProfileRegistry, RoomProfileProp


class TestRoomProfileRegistry:
    """Tests for RoomProfileRegistry singleton."""

    def setup_method(self):
        """Reset singleton before each test."""
        RoomProfileRegistry.reset()

    def test_singleton_pattern(self):
        """Registry should be a singleton."""
        r1 = RoomProfileRegistry.get()
        r2 = RoomProfileRegistry.get()
        assert r1 is r2

    def test_registry_loads_profiles(self):
        """Registry should load profiles from default location."""
        registry = RoomProfileRegistry.get()
        profiles = registry.list_all()
        assert len(profiles) >= 4  # At least living_room, bedroom, bathroom, kitchen

    def test_get_by_id_found(self):
        """get_by_id should return profile for valid ID."""
        registry = RoomProfileRegistry.get()
        profile = registry.get_by_id("living_room")
        
        assert profile is not None
        assert profile.id == "living_room"
        assert profile.temperature == 20.0

    def test_get_by_id_not_found(self):
        """get_by_id should return None for invalid ID."""
        registry = RoomProfileRegistry.get()
        profile = registry.get_by_id("nonexistent_room")
        assert profile is None

    def test_get_by_name_found(self):
        """get_by_name should return profile for valid name."""
        registry = RoomProfileRegistry.get()
        profile = registry.get_by_name("Bathroom (High Humidity)")
        
        assert profile is not None
        assert profile.id == "bathroom"

    def test_get_by_name_not_found(self):
        """get_by_name should return None for invalid name."""
        registry = RoomProfileRegistry.get()
        profile = registry.get_by_name("Nonexistent Room")
        assert profile is None

    def test_list_ids(self):
        """list_ids should return all profile IDs."""
        registry = RoomProfileRegistry.get()
        ids = registry.list_ids()
        
        assert "living_room" in ids
        assert "bathroom" in ids
        assert "kitchen" in ids

    def test_get_boundary_conditions_valid(self):
        """get_boundary_conditions should return proper BC dict."""
        registry = RoomProfileRegistry.get()
        bc = registry.get_boundary_conditions("bathroom", T_exterior=-10.0)
        
        assert "convective" in bc
        assert "internal" in bc["convective"]
        assert "external" in bc["convective"]
        
        internal = bc["convective"]["internal"]
        assert internal["T"] == 24.0  # Bathroom temperature
        assert internal["R"] == 0.10  # Bathroom interior R
        
        external = bc["convective"]["external"]
        assert external["T"] == -10.0  # Our specified exterior temp

    def test_get_boundary_conditions_invalid(self):
        """get_boundary_conditions should return empty dict for invalid ID."""
        registry = RoomProfileRegistry.get()
        bc = registry.get_boundary_conditions("nonexistent")
        assert bc == {}

    def test_bathroom_has_high_humidity(self):
        """Bathroom should have high humidity class."""
        registry = RoomProfileRegistry.get()
        profile = registry.get_by_id("bathroom")
        
        assert profile.relative_humidity >= 0.70
        assert profile.humidity_class >= 4

    def test_warehouse_has_low_humidity(self):
        """Warehouse should have low humidity class."""
        registry = RoomProfileRegistry.get()
        profile = registry.get_by_id("warehouse")
        
        assert profile.humidity_class == 1
        assert profile.temperature == 15.0

    def test_office_is_class_2(self):
        """Office should be humidity class 2."""
        registry = RoomProfileRegistry.get()
        profile = registry.get_by_id("office")
        
        assert profile.humidity_class == 2

    def test_swimming_pool_is_class_5(self):
        """Swimming pool should be highest humidity class."""
        registry = RoomProfileRegistry.get()
        profile = registry.get_by_id("swimming_pool")
        
        assert profile.humidity_class == 5
        assert profile.relative_humidity >= 0.80


class TestRoomProfileRegistryCustomPath:
    """Tests for loading from custom path."""

    def setup_method(self):
        """Reset singleton before each test."""
        RoomProfileRegistry.reset()

    def test_load_from_custom_path(self):
        """Registry should load from custom JSON path."""
        # Create temporary JSON file
        with tempfile.TemporaryDirectory() as tmpdir:
            test_data = [
                {
                    "id": "test_room",
                    "name": "Test Room",
                    "category": "Test",
                    "temperature": 25.0,
                    "relative_humidity": 0.60,
                    "humidity_class": 3
                }
            ]
            
            json_path = os.path.join(tmpdir, "test_profiles.json")
            with open(json_path, 'w') as f:
                json.dump(test_data, f)
            
            registry = RoomProfileRegistry.get()
            registry.initialize(tmpdir)
            
            profile = registry.get_by_id("test_room")
            assert profile is not None
            assert profile.temperature == 25.0


class TestRoomProfileProp:
    """Tests for RoomProfileProp dataclass."""

    def test_default_values(self):
        """RoomProfileProp should have sensible defaults."""
        prop = RoomProfileProp(
            id="test",
            name="Test",
            category="Test",
            temperature=20.0,
            relative_humidity=0.5,
            humidity_class=3
        )
        
        assert prop.surface_resistance_int == 0.13
        assert prop.surface_resistance_ext == 0.04
        assert prop.description == ""
        assert prop.source == ""

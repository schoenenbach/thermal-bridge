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
Room Profile Registry for Standard Boundary Conditions.

This module provides predefined room profiles (Living Room, Bathroom, Kitchen, etc.)
with standard temperature and humidity values per DIN 4108-2 and EN ISO 13788.

Usage:
    registry = RoomProfileRegistry.get()
    registry.initialize("library/room_profiles")
    
    profile = registry.get_by_id("bathroom")
    print(f"Temperature: {profile.temperature}°C, RH: {profile.relative_humidity*100}%")
    
    # Get ready-to-use boundary conditions dict
    bc = registry.get_boundary_conditions("bathroom", T_exterior=-5.0)
"""

import json
import os
import glob
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RoomProfileProp:
    """
    Room profile properties for boundary condition setup.
    
    Attributes:
        id: Unique identifier (e.g., 'living_room', 'bathroom')
        name: Human-readable name
        category: Category classification (Residential, Commercial, etc.)
        temperature: Typical interior temperature [°C]
        relative_humidity: Typical relative humidity [0.0-1.0]
        humidity_class: ISO 13788 humidity class (1-5)
        surface_resistance_int: Interior surface resistance [m²K/W]
        surface_resistance_ext: Exterior surface resistance [m²K/W]
        description: Detailed description
        source: Reference standard (e.g., 'DIN 4108-2')
    """
    id: str
    name: str
    category: str
    temperature: float
    relative_humidity: float
    humidity_class: int
    surface_resistance_int: float = 0.13
    surface_resistance_ext: float = 0.04
    description: str = ""
    source: str = ""


class RoomProfileRegistry:
    """
    Singleton registry for room profile definitions.
    
    Mirrors the MaterialRegistry pattern for consistency.
    Loads profiles from JSON files in a specified directory.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RoomProfileRegistry, cls).__new__(cls)
            cls._instance.profiles: Dict[str, RoomProfileProp] = {}
            cls._instance.initialized = False
        return cls._instance

    def initialize(self, library_path: str = None):
        """
        Load room profiles from JSON files.
        
        Args:
            library_path: Path to directory containing room_profiles.json files.
                         If None, uses default location relative to this file.
        """
        if self.initialized:
            return
        
        if library_path is None:
            # Default: same directory as this file, under room_profiles/
            library_path = os.path.join(os.path.dirname(__file__), "room_profiles")
            
        # Load all JSON files in the directory
        pattern = os.path.join(library_path, "*.json")
        for fpath in glob.glob(pattern):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            self._register_profile(item)
            except Exception as e:
                print(f"[ERROR] Failed to load room profiles from {fpath}: {e}")
        
        self.initialized = True

    def _register_profile(self, data: dict):
        """Register a single profile from JSON data."""
        profile_id = data.get('id')
        if not profile_id:
            return
            
        prop = RoomProfileProp(
            id=profile_id,
            name=data.get('name', 'Unknown'),
            category=data.get('category', 'General'),
            temperature=float(data.get('temperature', 20.0)),
            relative_humidity=float(data.get('relative_humidity', 0.5)),
            humidity_class=int(data.get('humidity_class', 3)),
            surface_resistance_int=float(data.get('surface_resistance_int', 0.13)),
            surface_resistance_ext=float(data.get('surface_resistance_ext', 0.04)),
            description=data.get('description', ''),
            source=data.get('source', '')
        )
        
        self.profiles[profile_id] = prop

    def get_by_id(self, profile_id: str) -> Optional[RoomProfileProp]:
        """Get a room profile by its ID."""
        self._ensure_initialized()
        return self.profiles.get(profile_id)

    def get_by_name(self, name: str) -> Optional[RoomProfileProp]:
        """Get a room profile by its display name."""
        self._ensure_initialized()
        for profile in self.profiles.values():
            if profile.name == name:
                return profile
        return None

    def list_all(self) -> List[RoomProfileProp]:
        """Return all registered room profiles."""
        self._ensure_initialized()
        return list(self.profiles.values())
    
    def list_ids(self) -> List[str]:
        """Return all profile IDs."""
        self._ensure_initialized()
        return list(self.profiles.keys())

    def get_boundary_conditions(
        self, 
        profile_id: str, 
        T_exterior: float = -5.0,
        R_exterior: float = None
    ) -> dict:
        """
        Get boundary conditions dict for a room profile.
        
        Args:
            profile_id: Room profile ID
            T_exterior: Exterior temperature [°C], default -5.0 (winter design)
            R_exterior: Override exterior surface resistance if specified
            
        Returns:
            Dictionary suitable for use in scenario['boundary_conditions']:
            {
                'convective': {
                    'internal': {'T': 20.0, 'R': 0.13},
                    'external': {'T': -5.0, 'R': 0.04}
                }
            }
            
            Returns empty dict if profile not found.
        """
        profile = self.get_by_id(profile_id)
        if not profile:
            return {}
        
        R_ext = R_exterior if R_exterior is not None else profile.surface_resistance_ext
        
        return {
            'convective': {
                'internal': {
                    'T': profile.temperature,
                    'R': profile.surface_resistance_int
                },
                'external': {
                    'T': T_exterior,
                    'R': R_ext
                }
            }
        }

    def _ensure_initialized(self):
        """Auto-initialize if not already done."""
        if not self.initialized:
            self.initialize()

    @classmethod
    def get(cls) -> 'RoomProfileRegistry':
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the singleton (mainly for testing)."""
        cls._instance = None

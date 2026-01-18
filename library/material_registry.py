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

import json
import os
import glob
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

@dataclass
class MaterialProp:
    id: str
    name: str
    category: str
    lambda_val: float
    density: float = 1000.0
    heat_capacity: float = 1000.0
    color: str = "#808080"
    source: str = "Unknown"
    solver_id: int = 0
    emissivity: float = 0.9  # Surface emissivity (0-1), default for most building materials

class MaterialRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MaterialRegistry, cls).__new__(cls)
            cls._instance.materials: Dict[str, MaterialProp] = {}
            cls._instance.solver_id_map: Dict[int, MaterialProp] = {}
            # Start solver IDs from 100 to avoid conflict with legacy hardcoded IDs (if any)
            # Actually, we should probably reserve 0-10 or so for Air/BCs.
            cls._instance.next_solver_id = 100 
            cls._instance.initialized = False
        return cls._instance

    def initialize(self, library_path: str):
        if self.initialized:
            return
            
        # load json files
        pattern = os.path.join(library_path, "*.json")
        for fpath in glob.glob(pattern):
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            self._register_material(item)
            except Exception as e:
                print(f"[ERROR] Failed to load materials from {fpath}: {e}")
        
        self.initialized = True

    def _register_material(self, data: dict):
        mat_id = data.get('id')
        if not mat_id:
            return
            
        # Determine solver ID (Auto or Explicit)
        use_auto_id = "id_numeric" not in data
        solver_id = self.next_solver_id
        
        if not use_auto_id:
            solver_id = int(data["id_numeric"])
            
        prop = MaterialProp(
            id=mat_id,
            name=data.get('name', 'Unknown'),
            category=data.get('category', 'General'),
            lambda_val=float(data.get('lambda', 1.0)),
            density=float(data.get('density', 1000.0)),
            heat_capacity=float(data.get('heat_capacity', 1000.0)),
            color=data.get('color', '#808080'),
            source=data.get('source', ''),
            solver_id=solver_id,
            emissivity=float(data.get('emissivity', 0.9))
        )
        
        self.materials[mat_id] = prop
        self.solver_id_map[solver_id] = prop
        
        if use_auto_id:
            self.next_solver_id += 1

    def get_by_id(self, mat_id: str) -> Optional[MaterialProp]:
        return self.materials.get(mat_id)

    def get_lambda(self, mat_id: str, default=1.0) -> float:
        m = self.materials.get(mat_id)
        return m.lambda_val if m else default

    def get_emissivity(self, mat_id: str, default=0.9) -> float:
        """Get surface emissivity for a material (0-1)."""
        m = self.materials.get(mat_id)
        return m.emissivity if m else default
        
    def get_solver_id(self, mat_id: str) -> int:
        m = self.materials.get(mat_id)
        if m:
            return m.solver_id
        # Fallback? Should we register on fly? 
        # For now return a generic error ID or 2 (Wall)
        return 2

    # Global Access Pattern
    @classmethod
    def get(cls):
        if cls._instance is None:
            cls()
        return cls._instance

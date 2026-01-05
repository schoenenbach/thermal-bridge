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
            
        prop = MaterialProp(
            id=mat_id,
            name=data.get('name', 'Unknown'),
            category=data.get('category', 'General'),
            lambda_val=float(data.get('lambda', 1.0)),
            density=float(data.get('density', 1000.0)),
            heat_capacity=float(data.get('heat_capacity', 1000.0)),
            color=data.get('color', '#808080'),
            source=data.get('source', ''),
            solver_id=self.next_solver_id
        )
        
        self.materials[mat_id] = prop
        self.solver_id_map[self.next_solver_id] = prop
        self.next_solver_id += 1

    def get_by_id(self, mat_id: str) -> Optional[MaterialProp]:
        return self.materials.get(mat_id)

    def get_lambda(self, mat_id: str, default=1.0) -> float:
        m = self.materials.get(mat_id)
        return m.lambda_val if m else default
        
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

"""
ISO 10211 Test Case 2: Multi-Material Bridge

Geometry specification from ISO 10211:
- Domain: 500mm (W) x 47.5mm (H)
- Materials:
  - Concrete: λ = 1.15 W/(m·K)
  - Wood: λ = 0.12 W/(m·K)  
  - Insulation: λ = 0.029 W/(m·K)
  - Aluminium: λ = 230 W/(m·K)
  
Validation: Heat flux ≈ 9.5 W/m
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometry import SketchGeometry, RefinementZone, MaterialID
from typing import List


# Material IDs for ISO Case 2
MAT_INSULATION = 200
MAT_CONCRETE = 201
MAT_WOOD = 202
MAT_ALUMINUM = 203
MAT_AIR_INT = 204
MAT_AIR_EXT = 205


class ISOCase2Geometry(SketchGeometry):
    """
    ISO 10211 Test Case 2: Multi-Material Thermal Bridge
    
    Refactored to use SketchGeometry (Points + Shapes).
    """
    
    def __init__(self, grid_mm: float = 0.25):
        super().__init__()
        self.grid_mm = grid_mm
        
        self.rsi = 0.11
        self.rse = 0.06
        
        # --- Define Geometry using Points & Shapes ---
        
        # 1. Base Insulation (Full Domain Background)
        # Using 0-500 x 0-47.5
        self.add_point("BL", 0.0, 0.0)      # Bottom Left
        self.add_point("BR", 500.0, 0.0)    # Bottom Right
        self.add_point("TR", 500.0, 47.5)   # Top Right
        self.add_point("TL", 0.0, 47.5)     # Top Left
        
        self.add_shape(["BL", "BR", "TR", "TL"], 
                       material_id=MAT_INSULATION, lambda_val=0.029, 
                       name="InsulationBase")
        
        # 2. Concrete Top Layer (41.5mm - 47.5mm)
        self.add_point("Conc_BL", 0.0, 41.5)
        self.add_point("Conc_BR", 500.0, 41.5)
        # Re-use TR, TL from base or new points? Re-use is fine if ID matches
        # TR is (500, 47.5), TL is (0, 47.5)
        
        self.add_shape(["Conc_BL", "Conc_BR", "TR", "TL"],
                       material_id=MAT_CONCRETE, lambda_val=1.15,
                       name="ConcreteLayer")
                       
        # 3. Wood Block (0-15mm x 36.5-41.5mm)
        self.add_point("Wood_BL", 0.0, 36.5)
        self.add_point("Wood_BR", 15.0, 36.5)
        self.add_point("Wood_TR", 15.0, 41.5)
        # Conc_BL is (0, 41.5) - reuse as Wood_TL
        
        self.add_shape(["Wood_BL", "Wood_BR", "Wood_TR", "Conc_BL"],
                       material_id=MAT_WOOD, lambda_val=0.12,
                       name="WoodBlock")
        
        # 4. Aluminum Head (0-15mm x 35.0-36.5mm)
        self.add_point("AluHead_BL", 0.0, 35.0)
        self.add_point("AluHead_BR", 15.0, 35.0)
        # Wood_BL is (0, 36.5), Wood_BR is (15, 36.5)
        
        self.add_shape(["AluHead_BL", "AluHead_BR", "Wood_BR", "Wood_BL"],
                       material_id=MAT_ALUMINUM, lambda_val=230.0,
                       name="AluminumHead")
                       
        # 5. Aluminum Leg (0-1.5mm x 1.5-35.0mm)
        self.add_point("AluLeg_BL", 0.0, 1.5)
        self.add_point("AluLeg_BR", 1.5, 1.5)
        self.add_point("AluLeg_TR", 1.5, 35.0)
        # AluHead_BL is (0, 35.0)
        
        self.add_shape(["AluLeg_BL", "AluLeg_BR", "AluLeg_TR", "AluHead_BL"],
                       material_id=MAT_ALUMINUM, lambda_val=230.0,
                       name="AluminumLeg")
                       
        # 6. Aluminum Plate (0-500mm x 0-1.5mm)
        # Re-use BL(0,0), BR(500,0)
        self.add_point("AluPlate_TR", 500.0, 1.5)
        # AluLeg_BL is (0, 1.5)
        
        self.add_shape(["BL", "BR", "AluPlate_TR", "AluLeg_BL"],
                       material_id=MAT_ALUMINUM, lambda_val=230.0,
                       name="AluminumPlate")
                       
        # Set Canvas
        self.set_canvas(0.0, 500.0, 0.0, 47.5, grid_mm=grid_mm)
        
    def get_refinement_zones(self) -> List[RefinementZone]:
        # Refine near the aluminum leg
        return [
            RefinementZone(
                x_min=0.0, x_max=20.0,
                y_min=0.0, y_max=47.5,
                target_dx=self.grid_mm,
                priority=1
            )
        ]
        
    def get_boundary_conditions(self) -> dict:
        return {
            'convective': {
                'bottom': {'T': 20.0, 'R': self.rsi},
                'top': {'T': 0.0, 'R': self.rse},
            },
            'adiabatic': ['left', 'right'],
            'surface_resistance': {
                MAT_AIR_INT: self.rsi,
                MAT_AIR_EXT: self.rse,
            }
        }


if __name__ == "__main__":
    # Quick test
    geom = ISOCase2Geometry(grid_mm=0.25)
    config = geom.get_canvas_config()
    print(f"Canvas: {config.width_mm} x {config.height_mm} mm")
    print(f"Shapes: {len(geom.shapes)}")
    for s in geom.shapes:
        print(f"  - {s.name}: {s.material_id}")

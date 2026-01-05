from dataclasses import dataclass

import os
from library.material_registry import MaterialRegistry

# --- Configuration & Constants ---

# Initialize Registry
# Assuming the script runs from root or we find the library relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BASE_DIR, "library", "materials")
registry = MaterialRegistry.get()
registry.initialize(LIB_DIR)

# Materials (Lambda in W/mK) - Fetched from Registry with fallbacks
MAT_WALL = registry.get_lambda("wall_generic", 0.81)
MAT_INSULATION = registry.get_lambda("insulation_generic", 0.035)
MAT_REVEAL_INSULATION = registry.get_lambda("insulation_generic", 0.035) # Using same generic for now
MAT_STYRODUR = registry.get_lambda("insulation_styrodur", 0.025)

# Boundary Conditions (Temperature in C, Resistance in m2K/W)
TEMP_INT = 20.0
TEMP_EXT = -5.0
RSI_WALL = 0.13
RSI_CORNER = 0.25 
RSE = 0.04

# --- Calibrated Material Properties (Fixing double resistance error) ---
# The U-value provided (Ug, Uf) INCLUDES Rsi and Rse.
# In the Finite Difference Model, Rsi and Rse are applied as boundary conditions.
# Therefore, the material block must have a resistance of R_mat = 1/U - Rsi - Rse.

# Frame
# U_f = 1.3
# R_f_total = 1 / 1.3 = 0.769 m2K/W
# R_f_mat = 0.769 - RSI_WALL - RSE = 0.769 - 0.13 - 0.04 = 0.599 m2K/W
# Frame Depth d = 0.07 m
# Lambda_frame_eq = d / R_f_mat = 0.07 / 0.599 = 0.117 W/mK
MAT_FRAME_EQ = 0.07 / (1.0/1.3 - RSI_WALL - RSE) 

# Glass 
# U_g = 1.1
# R_g_total = 1 / 1.1 = 0.909 m2K/W
# R_g_mat = 0.909 - RSI_WALL - RSE = 0.909 - 0.13 - 0.04 = 0.739 m2K/W
# Glass Model Thickness d = 0.024 m (24mm used in grid)
# Lambda_glass_eq = 0.024 / R_g_mat
MAT_GLASS_UG11 = 0.024 / (1.0/1.1 - RSI_WALL - RSE)

# Spacers (Effective Lamdba for a solid block simulation of the edge)
# Values approx from ISO 10077-2 / Passive House Institute Data
MAT_SPACER_SWISS_ULTIMATE = 0.14
MAT_SPACER_STAINLESS = registry.get_lambda("steel_generic", 0.60)  # Approx
MAT_SPACER_ALUMINUM = registry.get_lambda("aluminum_generic", 10.0)
MAT_ALUMINUM = registry.get_lambda("aluminum_generic", 160.0)
MAT_CAVITY_ISO = registry.get_lambda("air_cavity_unventilated", 0.25)
MAT_EPDM = 0.25
MAT_AIR_EXT = 0.025
MAT_AIR_INT = 0.025

class SpacerType:
    NONE = 0
    SWISS_ULTIMATE = 1
    STAINLESS_STEEL = 2
    ALUMINUM = 3


@dataclass
class WindowConfig:
    """Window-specific dimensions for different window types.
    
    Allows easy configuration of different window types without
    modifying core geometry code.
    """
    frame_depth_mm: int = 70
    frame_width_mm: int = 70
    
    # Sash configuration
    sash_overlap_mm: int = 10
    sash_depth_mm: int = 70
    sash_width_mm: int = 70
    sash_recess_mm: int = 30
    
    # Glass configuration
    glass_thickness_mm: int = 24
    
    # U-values for reference calculations
    u_frame: float = 1.3
    u_glass: float = 1.1


@dataclass
class CalculationConfig:
    """Main configuration for thermal bridge calculations."""
    
    # Wall/Insulation geometry
    wall_thickness_mm: int
    insulation_thick_max_mm: int
    insulation_thick_min_mm: int
    reveal_insulation_mm: int
    taper_length_mm: int
    
    # Window positioning
    window_position_from_exterior_masonry_mm: int = 0
    masonry_rebate_overlap_mm: int = 0
    uninsulated_reveal: bool = False
    
    # Window configuration (use defaults or provide custom)
    window_config: WindowConfig = None
    
    # Legacy frame dimensions (for backward compatibility)
    frame_depth_mm: int = 70
    frame_width_mm: int = 70
    
    # Simulation settings
    grid_size_mm: float = 2.5
    spacer_type: int = SpacerType.SWISS_ULTIMATE
    use_styrodur_variant: bool = False
    
    def __post_init__(self):
        """Initialize window config if not provided."""
        if self.window_config is None:
            self.window_config = WindowConfig(
                frame_depth_mm=self.frame_depth_mm,
                frame_width_mm=self.frame_width_mm
            )


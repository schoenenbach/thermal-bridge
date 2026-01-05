from dataclasses import dataclass

# --- Configuration & Constants ---
# Materials (Lambda in W/mK)
MAT_WALL = 0.81  # Brick/Masonry (Standard Vollziegel 1800kg/m3)
MAT_INSULATION = 0.035  # ETICS WLS 035
MAT_REVEAL_INSULATION = 0.035

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
# Frame Depth d = 0.08 m
# Lambda_frame_eq = d / R_f_mat = 0.08 / 0.599 = 0.133 W/mK
MAT_FRAME_EQ = 0.08 / (1.0/1.3 - RSI_WALL - RSE) 

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
MAT_SPACER_STAINLESS = 0.60  # Typical stainless steel box
MAT_SPACER_ALUMINUM = 10.0 # High internal conductivity

class SpacerType:
    NONE = 0
    SWISS_ULTIMATE = 1
    STAINLESS_STEEL = 2
    ALUMINUM = 3

@dataclass
class CalculationConfig:
    wall_thickness_mm: int
    insulation_thick_max_mm: int
    insulation_thick_min_mm: int
    reveal_insulation_mm: int
    taper_length_mm: int
    
    # Advanced Settings
    frame_depth_mm: int = 80
    frame_width_mm: int = 80 
    window_position_from_exterior_masonry_mm: int = 0
    masonry_rebate_overlap_mm: int = 0
    uninsulated_reveal: bool = False
    
    # Simulation Fidelity
    grid_size_mm: float = 1.0
    spacer_type: int = SpacerType.SWISS_ULTIMATE

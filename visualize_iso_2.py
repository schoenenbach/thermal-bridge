import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors

def visualize_test_case_2():
    print("--- Visualizing ISO 10211 Test Case 2 Geometry ---")
    # Materials
    MAT_CONC=1.15
    MAT_WOOD=0.12
    MAT_INS=0.029
    MAT_ALU=230.0
    
    GRID_MM=0.5; W_mm=500.0; H_mm=47.5
    nx=int(W_mm/GRID_MM)+1; ny=int(H_mm/GRID_MM)+1
    
    cond = np.full((ny, nx), MAT_INS) # Background 0.029
    def to_idx(v): return int(round(v/GRID_MM))
    
    # Geometry from verify_iso_10211.py
    # 1. Concrete (Top 6mm, Full Width)
    cond[to_idx(41.5):to_idx(47.5), :] = MAT_CONC
    
    # 2. Wood (Left Block, 15x6.5 mm) - Touching Metal
    cond[to_idx(35.0):to_idx(41.5), to_idx(0):to_idx(15)] = MAT_WOOD
    
    # 3. Gap (35.0..36.5) -> Remains INS (Background)
    
    # 4. Metal Top Flange (15mm wide)
    cond[to_idx(33.5):to_idx(35.0), to_idx(0):to_idx(15)] = MAT_ALU
    
    # 5. Metal Web (1.5mm wide, 1.5..33.5)
    cond[to_idx(1.5):to_idx(33.5), to_idx(0):to_idx(1.5)] = MAT_ALU
    
    # 6. Metal Bottom Flange (Full Width 500mm)
    cond[to_idx(0):to_idx(1.5), :] = MAT_ALU
    
    # Plotting
    plt.figure(figsize=(12, 4))
    
    # Use a custom colormap for discrete materials
    cmap = plt.cm.get_cmap('viridis', 4)
    # Map values to 0,1,2,3 for cleaner plotting
    plot_data = np.zeros_like(cond)
    plot_data[cond == MAT_INS] = 0
    plot_data[cond == MAT_WOOD] = 1
    plot_data[cond == MAT_CONC] = 2
    plot_data[cond == MAT_ALU] = 3
    
    im = plt.imshow(plot_data, cmap=plt.cm.get_cmap('tab10', 4), origin='lower', extent=[0, W_mm, 0, H_mm], aspect='equal', interpolation='nearest')
    
    cbar = plt.colorbar(im, ticks=[0.375, 1.125, 1.875, 2.625])
    cbar.ax.set_yticklabels(['Insulation (0.029)', 'Wood (0.12)', 'Concrete (1.15)', 'Aluminium (230.0)'])
    
    plt.title('ISO 10211 Test Case 2: Geometry & Materials')
    plt.xlabel('Width (mm)')
    plt.ylabel('Height (mm)')
    plt.grid(True, linestyle='--', alpha=0.3)
    
    out_file = 'iso_case_2_geometry.png'
    plt.tight_layout()
    plt.savefig(out_file, dpi=150)
    print(f"Saved geometry visualization to {out_file}")

if __name__ == "__main__":
    visualize_test_case_2()

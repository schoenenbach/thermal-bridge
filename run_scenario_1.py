
import matplotlib.pyplot as plt
import numpy as np
import time
from config import CalculationConfig, SpacerType
from geometries.window_reveal import WindowRevealGeometry
from mesh import AdaptiveMesh
from geometry import build_material_grid
from thermal_solver import ThermalSolver

def run_scenario_1():
    print("=========================================")
    print("Running Scenario 1: Wall 360mm (No Insulation)")
    print("=========================================")
    
    # 1. Configure
    # Case 1: Wall 360, No Insulation (set ins_max=0)
    # The requirement says "No Insulation"
    cfg = CalculationConfig(
        wall_thickness_mm=360,
        insulation_thick_max_mm=0, # No Insulation
        insulation_thick_min_mm=0,
        reveal_insulation_mm=0,
        taper_length_mm=0,
        window_position_from_exterior_masonry_mm=150,
        masonry_rebate_overlap_mm=50,
        uninsulated_reveal=True,
        frame_depth_mm=70,
        frame_width_mm=70,
        grid_size_mm=2.5
    )
    
    # 2. Build Geometry & Mesh
    print("Generating Geometry...")
    geom = WindowRevealGeometry(cfg)
    mesh = AdaptiveMesh(geom)
    mesh.generate()
    
    # 3. Build Material Grid
    # Note: build_material_grid defaults to AIR_EXT (0). 
    # We need to distinguish AIR_INT (1). 
    # Strategy: 
    # 1. Treat all non-solid as AIR_INT first.
    # 2. Scan each row, find rightmost solid. Everything to the right is AIR_EXT.
    
    grid_map, _ = build_material_grid(geom, mesh.xc, mesh.yc)
    
    # Remap default 0 (AirExt) to 1 (AirInt) temporarily
    mask_air = (grid_map == 0)
    grid_map[mask_air] = 1 # AIR_INT
    
    # Apply Scanline Logic for Exterior Air
    ny, nx = grid_map.shape
    for i in range(ny):
        row = grid_map[i, :]
        # Find indices of solids (ID > 1)
        solids = np.where(row > 1)[0]
        if solids.size > 0:
            last_solid_idx = solids[-1]
            # Everything to the right is Exterior Air (0)
            if last_solid_idx < nx - 1:
                grid_map[i, last_solid_idx+1:] = 0 # AIR_EXT
        else:
             # No solids in this row (e.g. below wall or above?)
             # If completely empty, it's likely all Exterior or all Interior?
             # For this geometry (Window Reveal), "Empty" at bottom/top usually means...
             # Actually, if no solids, we need context.
             # But our geometry always has wall/ins/frame.
             # If a row is empty, let's assume it's AIR_EXT (0) if it's "outside" the domain?
             # Or AIR_INT?
             # Let's leave it as AIR_INT (1) if undefined, or check previous row?
             pass

    print(f"Mesh Size: {mesh.nx} x {mesh.ny} cells")
    
    # 4. Initialize Solver
    print("Initializing Solver...")
    solver = ThermalSolver(cfg, rsi_value=0.13, use_adaptive=True)
    # Inject pre-built grid/map to avoid re-calculation
    solver.x_coords = mesh.x_coords
    solver.y_coords = mesh.y_coords
    solver.dx_array = mesh.dx_array
    solver.dy_array = mesh.dy_array
    solver.xc = mesh.xc
    solver.yc = mesh.yc
    solver.nx = mesh.nx
    solver.ny = mesh.ny
    solver.grid_map = grid_map
    solver.width_mm = mesh.width_mm
    solver.height_mm = mesh.height_mm
    solver.temp = np.ones((solver.ny, solver.nx)) * 20.0 # Start warm
    solver.assign_materials_adaptive()
    
    # DEBUG: Plot Material Map
    print("Saving debug_material_map.png...")
    plt.figure(figsize=(12, 10))
    # Use tab10 to differentiate 0 and 1
    # 0=AirExt, 1=AirInt
    cmap = plt.get_cmap('tab10', 10)
    X, Y = np.meshgrid(mesh.x_coords, mesh.y_coords)
    plt.pcolormesh(X, Y, grid_map, cmap=cmap, shading='flat', vmin=-0.5, vmax=9.5)
    plt.gca().set_aspect('equal')
    plt.colorbar(ticks=range(10))
    plt.title("Debug Material Map (0=Ext, 1=Int)")
    plt.savefig("debug_material_map.png")
    plt.close()
    
    # 5. Solve
    print("Starting Thermal Simulation (Max 200k iters, tol=1e-8)...")
    start_time = time.time()
    solver.solve(max_iter=200000, tol=1e-8)
    end_time = time.time()
    print(f"Simulation completed in {end_time - start_time:.2f} seconds.")
    
    # 6. Results
    res = solver.calculate_psi()
    print("\n--- Results ---")
    print(f"Psi-Value: {res['Psi']:.4f} W/(m*K)")
    print(f"fRsi:      {res['fRsi']:.4f}")
    print(f"Min Temp:  {res['MinT']:.2f} °C")
    
    # 7. Plot
    filename = "result_scenario_1.png"
    
    plt.figure(figsize=(12, 10))
    X, Y = np.meshgrid(mesh.x_coords, mesh.y_coords)
    plt.pcolormesh(X, Y, solver.temp, cmap='jet', shading='flat')
    plt.gca().set_aspect('equal')
    plt.colorbar(label='Temperature [°C]')
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')
    plt.title(f"Scenario 1: Wall 360mm No Ins (Psi={res['Psi']:.3f})")
    plt.savefig(filename, dpi=150)
    print(f"Saved thermal plot to {filename}")

if __name__ == "__main__":
    run_scenario_1()

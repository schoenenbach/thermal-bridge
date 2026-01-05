#!/usr/bin/env python3
"""
Test script for SketchGeometry (Polygon based geometry).
Verifies the user's "Square A-B-C-D" example.
"""

import numpy as np
import matplotlib.pyplot as plt
from geometry import SketchGeometry, build_material_grid, MaterialID
from mesh import AdaptiveMesh

def plot_result(mesh, grid_map, filename):
    plt.figure(figsize=(10, 8))
    
    # Plot grid map
    cmap = plt.get_cmap('tab10', 10)
    plt.imshow(grid_map, cmap=cmap, origin='lower',
               extent=[mesh.x_coords[0], mesh.x_coords[-1],
                      mesh.y_coords[0], mesh.y_coords[-1]],
               interpolation='nearest')
    plt.colorbar(label='Material ID')
    
    # Overlay mesh lines
    for x in mesh.x_coords:
        plt.axvline(x, color='white', alpha=0.3, linewidth=0.5)
    for y in mesh.y_coords:
        plt.axhline(y, color='white', alpha=0.3, linewidth=0.5)
        
    plt.title(f"Sketch Geometry Verification\n{filename}")
    plt.xlabel("X [mm]")
    plt.ylabel("Y [mm]")
    
    plt.savefig(filename, dpi=150)
    print(f"Saved plot to {filename}")
    plt.close()

def main():
    print("Initializing SketchGeometry...")
    geom = SketchGeometry()
    
    print("Defining Points A, B, C, D...")
    # A (0,0)
    # B (100,0)
    # C (100,100)
    # D (0, 100)
    geom.add_point("A", 0, 0)
    geom.add_point("B", 100, 0)
    geom.add_point("C", 100, 100)
    geom.add_point("D", 0, 100)
    
    print("Defining Shape from points...")
    # Insulation with lambda 0.035
    geom.add_shape(["A", "B", "C", "D"], 
                   material_id=MaterialID.INSULATION, 
                   lambda_val=0.035,
                   name="InsulationSquare")
    
    # Optional: Add another shape to test overlap/complex geometry
    # E.g. a Triangle sitting on top
    geom.add_point("E", 50, 150)
    geom.add_shape(["D", "C", "E"], 
                   material_id=MaterialID.CONCRETE,
                   lambda_val=1.15,
                   name="RoofTriangle")
    
    print("Generating Adaptive Mesh...")
    mesh = AdaptiveMesh(geom)
    mesh.generate()
    print(mesh.info())
    
    print("Building Material Grid...")
    grid_map, cond = build_material_grid(geom, mesh.xc, mesh.yc)
    
    # Analyze results
    ins_cells = np.sum(grid_map == MaterialID.INSULATION)
    conc_cells = np.sum(grid_map == MaterialID.CONCRETE)
    total_cells = grid_map.size
    
    print("\nGrid Analysis:")
    print(f"  Total Cells: {total_cells}")
    print(f"  Insulation Cells: {ins_cells}")
    print(f"  Concrete Cells:   {conc_cells}")
    print(f"  Mesh X: {mesh.x_coords}")
    print(f"  Mesh Y: {mesh.y_coords}")
    
    plot_result(mesh, grid_map, "test_sketch_result.png")
    
    # Verification check
    # Center of square (50, 50) should be Insulation
    # Center of triangle (50, 125) should be Concrete
    
    # Find indices for (50, 50)
    idx_x = np.searchsorted(mesh.x_coords, 50) - 1
    idx_y = np.searchsorted(mesh.y_coords, 50) - 1
    mat_50_50 = grid_map[idx_y, idx_x]
    
    # Find indices for (50, 125)
    idx_x2 = np.searchsorted(mesh.x_coords, 50) - 1
    idx_y2 = np.searchsorted(mesh.y_coords, 125) - 1
    mat_50_125 = grid_map[idx_y2, idx_x2]
    
    print(f"\nSpot Check:")
    print(f"  Point (50, 50) Material ID: {mat_50_50} (Expected {MaterialID.INSULATION})")
    print(f"  Point (50, 125) Material ID: {mat_50_125} (Expected {MaterialID.CONCRETE})")
    
    if mat_50_50 == MaterialID.INSULATION and mat_50_125 == MaterialID.CONCRETE:
        print("\nSUCCESS: Geometry rasterization verified!")
    else:
        print("\nFAILURE: Material assignment incorrect.")

if __name__ == "__main__":
    main()

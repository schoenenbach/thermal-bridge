
import sys
import os
import json
from shapely.geometry import Polygon
import matplotlib.pyplot as plt

# Add current dir to path
sys.path.append(os.getcwd())

from dxf_importer import DXFImporter

def test_import():
    dxf_path = "Testing_Plan/sample_dxf/03016.dxf"
    if not os.path.exists(dxf_path):
        print(f"File not found: {dxf_path}")
        return

    print(f"Loading {dxf_path}...")
    with open(dxf_path, "rb") as f:
        importer = DXFImporter(f)
    
    layers = importer.get_layers()
    print(f"Layers found: {layers}")
    
    # Map each layer to itself to preserve distinctness
    mapping = {layer: layer for layer in layers}
    scenario = importer.extract_scenario(mapping)
    
    print("Scenario extraction successful.")
    print(f"Points: {len(scenario['points'])}")
    print(f"Elements: {len(scenario['elements'])}")
    
    for el in scenario['elements']:
        print(f"  Element: {el.get('name')} | Mat: {el.get('material')} | Pts: {len(el['points'])}")

    # Visual check
    fig, ax = plt.subplots(figsize=(10, 10))
    colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'orange', 'purple']
    
    # Collect all polygons
    for i, el in enumerate(scenario['elements']):
        pts = [scenario["points"][p] for p in el["points"]]
        if pts:
            poly = Polygon(pts)
            x, y = poly.exterior.xy
            c = colors[i % len(colors)]
            ax.fill(x, y, alpha=0.5, fc=c, ec='black', linewidth=0.5, label=el['material'])
    
    plt.axis('equal')
    plt.title(f"Imported Geometry: {dxf_path}")
    output_img = "test_dxf_result.png"
    plt.savefig(output_img)
    print(f"Saved visualization to {output_img}")

if __name__ == "__main__":
    test_import()

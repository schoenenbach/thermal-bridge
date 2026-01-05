import streamlit as st
import glob
import os
import yaml
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import sys

# Ensure current directory is in path so we can import modules
sys.path.append(os.getcwd())

from declarative_geometry import DeclarativeGeometry
from simulation_engine import solve_scenario
from solver import get_solver_lib

# --- Auto-Build for Cloud Deployment ---
import subprocess
if not os.path.exists("thermal_solver_core.so"):
    st.warning("Compiling Solver (First Run)...")
    try:
        subprocess.check_call(["python3", "build_solver.py"])
        st.success("Solver compiled!")
    except Exception as e:
        st.error(f"Compilation failed: {e}")
        st.stop()
# ---------------------------------------

st.set_page_config(page_title="Thermal Bridge Simulator", layout="wide")

st.title("Thermal Bridge Simulator")
st.markdown("Calculate thermal bridges for window reveals using a hybrid Python/C++ solver.")

# --- Mode Selection ---
st.sidebar.title("Mode")
mode = st.sidebar.radio("Select Mode", ["Standard Scenarios", "Custom Editor"])

grid_override = 0.0

if mode == "Standard Scenarios":
    # --- Standard Mode (Existing Logic) ---
    st.sidebar.header("Configuration")
    
    # Find Scenarios
    scenario_files = glob.glob("scenarios/scenario_*.yaml") + glob.glob("scenarios/iso_*.yaml")
    scenario_files.sort()
    scenario_names = [os.path.basename(f) for f in scenario_files]
    
    selected_file_name = st.sidebar.selectbox("Select Scenario", scenario_names)
    
    if selected_file_name:
        selected_file_path = os.path.join("scenarios", selected_file_name)
        with open(selected_file_path, 'r') as f:
            yaml_content = f.read()
            data = yaml.safe_load(yaml_content)
            
        # ... (Parametric Controls logic - kept for standard mode)
        # Variable Overrides
        st.sidebar.subheader("Parameters")
        variables = data.get('variables', {})
        modified_variables = {}
        
        if variables:
            for key, value in variables.items():
                if isinstance(value, (int, float)):
                    # Heuristic for ranges
                    min_val = 0.0
                    max_val = float(value) * 3.0 if value > 0 else 100.0
                    step = 5.0
                    if "thick" in key:
                        min_val = 0.0
                        max_val = 500.0
                    
                    if value < min_val: min_val = value
                    if value > max_val: max_val = value * 2.0
                    
                    new_val = st.sidebar.number_input(f"{key} (mm)", 
                                                    min_value=float(min_val), 
                                                    max_value=float(max_val), 
                                                    value=float(value),
                                                    step=step)
                    modified_variables[key] = new_val
                else:
                    st.sidebar.text(f"{key}: {value}")
                    modified_variables[key] = value
        
        if modified_variables:
            data['variables'] = modified_variables
            
        # Store data for execution
        active_data = data
        active_name = data.get('name', selected_file_name)

else:
    # --- Custom Editor Mode ---
    st.sidebar.header("Builder")
    
    # Template Loader
    scenario_files = glob.glob("scenarios/*.yaml")
    scenario_files.sort()
    display_names = ["(New Empty)"] + [os.path.basename(f) for f in scenario_files]
    
    template = st.sidebar.selectbox("Load Template", display_names)
    
    default_yaml = """name: "My Custom Geometry"
canvas:
  bounds: [0, 500, 0, 500]
  grid: 10.0
elements:
  - type: rect
    material: 2 # WALL
    params:
      x: 0
      y: 0
      width: 360
      height: 500
"""
    
    if template != "(New Empty)":
        pth = os.path.join("scenarios", template)
        with open(pth, 'r') as f:
            default_yaml = f.read()

    # Grid Override (Performance)
    st.sidebar.markdown("---")
    grid_override = st.sidebar.number_input("Override Grid Size (mm)", 
                                           min_value=0.0, max_value=50.0, value=0.0, step=0.5,
                                           help="Set > 0 to override YAML grid size. Larger = Faster, Less Accurate.")

    # Editor
    st.subheader("Geometry Definition (YAML)")
    yaml_input = st.text_area("Edit Configuration", value=default_yaml, height=400)
    
    try:
        active_data = yaml.safe_load(yaml_input)
        active_name = active_data.get('name', "Custom")
        st.sidebar.success("YAML Valid")
    except Exception as e:
        st.sidebar.error(f"YAML Error: {e}")
        active_data = None
        active_name = "Invalid"


# --- Execution (Common) ---
if active_data:
    st.header(active_name)
    
    col_act1, col_act2 = st.columns([1,1])
    
    with col_act1:
        if st.button("Run Simulation", type="primary"):
            with st.spinner("Simulating..."):
                try:
                    # Apply Grid Override
                    if grid_override > 0:
                        if 'canvas' not in active_data: active_data['canvas'] = {}
                        active_data['canvas']['grid'] = grid_override
                        # Also bounds if needed? No, just grid.

                    # Temp file strategy
                    temp_yaml = "temp_active.yaml"
                    with open(temp_yaml, 'w') as f:
                        yaml.dump(active_data, f)
                        
                    scenario_def = {
                        "name": active_name,
                        "file_suffix": "custom",
                        "cfg": temp_yaml
                    }
                    
                    # Progress Bar
                    prog_bar = st.progress(0.0)
                    status_text = st.empty()
                    
                    def app_progress_cb(phase, step, total, diff):
                        pct = float(step) / float(total)
                        base = 0.0 if "Pass 1" in phase else 0.5
                        final_pct = base + (pct * 0.5)
                        # Clamp
                        final_pct = min(1.0, max(0.0, final_pct))
                        
                        prog_bar.progress(final_pct)
                        status_text.text(f"{phase}: Iteration {step}/{total} (Diff={diff:.2e})")

                    results = solve_scenario(scenario_def, use_adaptive_mesh=True, progress_callback=app_progress_cb)
                    
                    prog_bar.progress(1.0)
                    status_text.success("Simulation Complete")
                    st.metric("Psi-Value", f"{results.get('Psi', 0.0):.4f} W/mK", help="Available if 'Psi' is defined in measurements")
                    if 'fRsi' in results:
                        st.metric("fRsi Factor", f"{results['fRsi']:.4f}")
                    else:
                        st.info("fRsi not calculated")
                        
                    if 'MinT' in results:
                        st.metric("Min Temp", f"{results['MinT']:.2f} °C")
                    else:
                        st.info("Min Temp not available")
                    
                    # Cleanup
                    if os.path.exists(temp_yaml): os.remove(temp_yaml)
                    
                    # Show Result Image
                    img_path = f"result_{active_name}.png"
                    if os.path.exists(img_path):
                        st.image(img_path, caption="Result")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with col_act2:
        if st.button("Preview Geometry"):
            try:
                geom = DeclarativeGeometry(active_data)
                from mesh import AdaptiveMesh
                from solver import plot_geometry
                from geometry import build_material_grid
                
                mesh = AdaptiveMesh(geom)
                mesh.generate()
                grid_map, _ = build_material_grid(geom, mesh.xc, mesh.yc)
                
                plot_geometry(grid_map, 
                              geom.get_canvas_config().width_mm, 
                              geom.get_canvas_config().height_mm,
                              filename="preview.png",
                              x_coords=mesh.x_coords,
                              y_coords=mesh.y_coords)
                st.image("preview.png", caption="Geometry Map")
            except Exception as e:
                st.error(f"Preview Failed: {e}")

    # Download
    if mode == "Custom Editor":
        st.download_button("Download YAML", data=yaml_input, file_name=f"{active_name.replace(' ', '_')}.yaml")



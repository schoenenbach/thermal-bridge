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
from solver import get_solver_lib
from geometry_builder import generate_scenario, COLOR_MAP, scenario_to_canvas

from streamlit_drawable_canvas import st_canvas

# ... (Previous imports)

# Remove try-except, let it crash if missing
# try:
#     from streamlit_drawable_canvas import st_canvas
# except ImportError:
#     st_canvas = None

# ... (Inside tab_builder)




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

# --- Configuration Sidebar ---
st.sidebar.title("Configuration")

# 1. Template Loader
scenario_files = glob.glob("scenarios/scenario_*.yaml") + glob.glob("scenarios/iso_*.yaml")
scenario_files.sort()
display_names = ["(New Empty)"] + [os.path.basename(f) for f in scenario_files]

# Use session state to handle template loading without overwriting edits accidentally
if "yaml_editor" not in st.session_state:
    st.session_state.yaml_editor = """name: "My Custom Geometry"
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

def load_template():
    selected = st.session_state.template_selector
    if selected != "(New Empty)":
        pth = os.path.join("scenarios", selected)
        with open(pth, 'r') as f:
            # Crucial: Update the widget key directly!
            st.session_state.yaml_editor = f.read()

template = st.sidebar.selectbox("Load Template", display_names, key="template_selector", on_change=load_template)

# 2. Grid Override
st.sidebar.markdown("---")
grid_override = st.sidebar.number_input("Override Grid Size (mm)", 
                                       min_value=0.0, max_value=50.0, value=0.0, step=0.5,
                                       help="Set > 0 to override YAML grid size. Larger = Faster, Less Accurate.")

# --- Main Editor Area ---
# --- Main Area Tabs ---
tab_editor, tab_builder, tab_opt = st.tabs(["Scenario Editor", "Geometry Builder", "Optimization"])

with tab_builder:
    st.header("Interactive Geometry Builder")
    
    # CSS to force iframe visibility - potentially needed for some browser/streamlit combos
    st.markdown("""
        <style>
        iframe[title="streamlit_drawable_canvas.st_canvas"] {
            min-height: 400px;
            border: 1px solid #ccc;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.info("Instructions:\n- **Draw**: Click and drag.\n- **Edit**: Select to move/resize.\n- **Delete**: Select object and click the **control handle/square** above it (or try Backspace).\n- **Reset**: Click 'Clear Canvas' above to remove everything.")
    
    # --- Load from Scenario Button ---
    if st.button("Load from Active Scenario", type="primary", help="Populate builder with current YAML geometry"):
        try:
            # Parse current YAML
            current_scen = yaml.safe_load(st.session_state.yaml_editor)
            if current_scen:
                # Convert to Canvas JSON
                canvas_init = scenario_to_canvas(current_scen)
                
                # Update Session State to force reload
                st.session_state.canvas_reset_count += 1
                st.session_state['builder_initial_state'] = canvas_init
                st.session_state['builder_obj_map'] = canvas_init.get('metadata', {}).get('obj_map', {})
                st.session_state['builder_source_elements'] = current_scen.get('elements', [])
                st.session_state['builder_source_variables'] = current_scen.get('variables', {})
                
                st.success(f"Loaded {len(canvas_init['objects'])} objects from scenario.")
                st.rerun()
        except Exception as e:
            st.error(f"Failed to load scenario: {e}")

    # Tool Bar
    col_tools_1, col_tools_2 = st.columns(2)
    
    with col_tools_1:
        # Material Selector
        material_mode = st.radio("Material", list(COLOR_MAP.values()), index=0, horizontal=True)
        # Reverse lookup
        fill_color = "#808080"
        for k, v in COLOR_MAP.items():
            if v == material_mode:
                fill_color = k
                break
                
    with col_tools_2:
        tool_mode = st.radio("Tool", ["Draw Rectangle", "Edit/Select"], index=0, horizontal=True)
        mode_map = {"Draw Rectangle": "rect", "Edit/Select": "transform"}
    
    # Reset Button logic
    if "canvas_reset_count" not in st.session_state:
        st.session_state.canvas_reset_count = 0
        
    if st.button("Clear Canvas", type="secondary"):
        st.session_state.canvas_reset_count += 1
        st.rerun()

    # Canvas
    realtime_update = st.checkbox("Update YAML Realtime", value=True)
    
    # CSS to force iframe visibility - potentially needed for some browser/streamlit combos
    st.markdown("""
        <style>
        iframe[title="streamlit_drawable_canvas.st_canvas"] {
            min-height: 400px;
            border: 1px solid #ccc;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Canvas Component
    c_container = st.container()
    with c_container:
        canvas_key = f"geometry_canvas_prod_v1_{st.session_state.canvas_reset_count}"
        canvas_result = st_canvas(
            fill_color=fill_color,
            stroke_width=2,
            stroke_color="#000000",
            background_color="#eeeeee",
            update_streamlit=realtime_update,
            height=400,
            width=600,
            drawing_mode=mode_map[tool_mode],
            display_toolbar=True,
            initial_drawing=st.session_state.get('builder_initial_state', {'version': '4.4.0', 'objects': []}), 
            key=canvas_key
        )

    # --- Element Inspector ---
    st.markdown("---")
    st.subheader("Element Inspector")
    
    # 1. Selection Logic
    # Currently st_canvas does not push selection events to Streamlit.
    # We rely on the Dropdown for inspection.
    
    source_elements = st.session_state.get('builder_source_elements', [])
    source_variables = st.session_state.get('builder_source_variables', {})
    obj_map = st.session_state.get('builder_obj_map', {})
    
    if source_elements:
        # Create display names
        el_names = [f"{i}: {el.get('name', el.get('type', 'Element'))}" for i, el in enumerate(source_elements)]
        
        st.caption("Select an element from the list below to view its variables.")
        
        # Try to find selected element from Dropdown
        sel_name = st.selectbox("Select Element to Inspect", ["(None)"] + el_names)
        
        selected_el_idx = -1
        if sel_name != "(None)":
            selected_el_idx = int(sel_name.split(":")[0])

        if selected_el_idx >= 0:
            st.info(f"Inspecting Element: **{el_names[selected_el_idx]}**")
            
            el_data = source_elements[selected_el_idx]
            el_params = el_data.get('params', {})
            
            # Display Variables
            # If a param maps to a variable like "${wall_thick}", show that relationship.
            
            st.markdown("#### Parameters")
            disp_data = []
            for k, v in el_params.items():
                val_display = v
                var_name = None
                
                # Check for variable reference
                if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    var_name = v[2:-1]
                    val_display = f"{v} (= {source_variables.get(var_name, '???')})"
                
                disp_data.append({"Parameter": k, "Value": val_display})
                
            st.table(disp_data)
        
    else:
        st.write("Load a scenario to inspect specific element variables.")

    # Output Processing
    if canvas_result and canvas_result.json_data:
         # Only show summary, not full dump
         num_obj = len(canvas_result.json_data.get("objects", []))
         st.caption(f"Objects detected: {num_obj}")
          
         if num_obj > 0:
             # Merge with active scenario if available to preserve BCs
             base_scen = None
             # Trying to retrieve active_data from editor tab is hard without re-parsing.
             # But we stored it in session_state when loading? 
             # No, 'active_data' is a local var in editor tab loop.
             # Use st.session_state.get('builder_source_variables') is not enough.
             # Re-parsing 'yaml_editor' is safest.
             try:
                 if 'yaml_editor' in st.session_state:
                     base_scen = yaml.safe_load(st.session_state.yaml_editor)
             except:
                 pass

             scen = generate_scenario(canvas_result.json_data, base_scenario=base_scen)
             
             # Preview and Send
             col_res1, col_res2 = st.columns([2, 1])
             with col_res1:
                 st.subheader("Generated Scenario")
                 st.code(yaml.dump(scen), language='yaml')
             with col_res2:
                 st.write(" ")
                 st.write(" ")
                 if st.button("Use this Geometry", type="primary"):
                    st.session_state.yaml_editor = yaml.dump(scen, sort_keys=False)
                    st.toast("Configuration Updated!", icon="✅")
                    # Switch to Editor tab? st.experimental_set_query_params? No, strictly manual tab check.
                    st.success("Sent to Editor Tab ->")

with tab_editor:
    st.subheader("Geometry Definition (YAML)")
    # No need for value=... if key is used and initialized in session_state, but providing value is good practice for first run fallback
    yaml_input = st.text_area("Edit Configuration", height=500, key="yaml_editor")
    
    # --- Live Parsing & Dynamic Sliders ---
    active_data = None
    active_name = "Custom"
    
    try:
        active_data = yaml.safe_load(yaml_input)
        active_name = active_data.get('name', "Custom")
        # st.sidebar.success("YAML Valid") # Less noise
    except Exception as e:
        st.sidebar.error(f"YAML Error: {e}")
        active_data = None
        active_name = "Invalid"
    
    # Dynamic Variable Extraction
    if active_data:
        variables = active_data.get('variables', {})
        if variables:
            st.sidebar.markdown("---")
            st.sidebar.subheader("Parameters")
            
            modified_variables = {}
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
                    
                    # Make key unique using scenario name to avoid state collisions
                    widget_key = f"var_{active_name}_{key}"
                    
                    new_val = st.sidebar.number_input(f"{key} (mm)", 
                                                    min_value=float(min_val), 
                                                    max_value=float(max_val), 
                                                    value=float(value),
                                                    step=step,
                                                    key=widget_key)
                    modified_variables[key] = new_val
                else:
                    st.sidebar.text(f"{key}: {value}")
                    modified_variables[key] = value
            
            # Apply Overrides to active_data
            if modified_variables:
                active_data['variables'] = modified_variables
    
    
    # --- Execution Control ---
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
    
                        # Temp file strategy (No longer required by engine but useful for debug or legacy)
                        # We can now pass dict directly. but let's keep temp file strictly for debug if needed
                        # Update: solve_scenario now accepts dict.
                        
                        scenario_def = {
                            "name": active_name,
                            "file_suffix": "custom",
                            "cfg": active_data
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
                        
                        measurements = results.get('measurements', {})
                        if measurements:
                            st.subheader("Measurements")
                            # Dynamic grid layout
                            cols = st.columns(3)
                            for i, (name, res) in enumerate(measurements.items()):
                                val = res.get('value')
                                if val is None: continue
                                
                                with cols[i % 3]:
                                    label = name
                                    value_str = f"{val:.4f}"
                                    delta = None
                                    help_txt = None
                                    
                                    # Handle special formatting for known keys
                                    if name == "Psi":
                                        label = "Ψ-Value [W/mK]"
                                    elif name == "fRsi":
                                        label = "fRsi Factor"
                                    elif "MinT" in name:
                                        value_str += " °C"
                                    
                                    # Handle validation data
                                    if 'expected' in res:
                                        expected = res['expected']
                                        diff = res.get('diff', abs(val - expected))
                                        passed = res.get('passed', diff < 0.1) # Fallback tolerance
                                        
                                        icon = "✅" if passed else "❌"
                                        label = f"{icon} {label}"
                                        delta = f"Err: {diff:.4f}"
                                        help_txt = f"Expected: {expected:.4f}"
                                    
                                    st.metric(label, value_str, delta=delta, delta_color="inverse", help=help_txt)
                                    
                        # Store results for report generation
                        simple_results = {k: v.get('value') for k, v in measurements.items()}
                        st.session_state['last_simulation_results'] = simple_results
                                    
                        # Show Result Image
                        img_path = f"result_{active_name}.png"
                        if os.path.exists(img_path):
                            # Force browser reload with unique param
                            st.image(img_path, caption=f"Result (Ti={active_data.get('boundary_conditions', {}).get('convective', {}).get('internal', {}).get('T', 'Def')}°C)", output_format="PNG")
                            
                    except Exception as e:
                        st.error(f"Error: {e}")
                        import traceback
                        st.code(traceback.format_exc())
        
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
        st.download_button("Download YAML", data=yaml_input, file_name=f"{active_name.replace(' ', '_')}.yaml")


import plotly.express as px
from batch_simulator import BatchSimulator

with tab_opt:
    st.header("Parametric Optimization")
    
    if active_data:
        st.info("Optimize parameters for the currently loaded scenario.")
        
        try:
            bs = BatchSimulator(active_data)
            params = bs.get_optimizable_parameters()
            
            if not params:
                st.warning("No numeric parameters found in this scenario configuration.")
            else:
                col_opt1, col_opt2 = st.columns([1, 2])
                
                with col_opt1:
                    target_param = st.selectbox("Parameter to Sweep", list(params.keys()))
                    current_val = params[target_param]
                    st.caption(f"Current Value: {current_val}")
                    
                    start_val = st.number_input("Start", value=float(current_val * 0.5))
                    end_val = st.number_input("End", value=float(current_val * 1.5))
                    step_val = st.number_input("Step", value=float(current_val * 0.1) if current_val != 0 else 1.0)
                    
                with col_opt2:
                    if st.button("Run Sweep"):
                        if step_val <= 0:
                            st.error("Step must be positive.")
                        else:
                            with st.spinner(f"Running sweep for {target_param}..."):
                                try:
                                    df = bs.run_sweep(target_param, start_val, end_val, step_val)
                                    
                                    st.success(f"Sweep Completed ({len(df)} iterations)")
                                    st.dataframe(df)
                                    
                                    if not df.empty and 'psi_value' in df.columns:
                                        fig = px.line(df, x='value', y='psi_value', 
                                                      title=f"Impact of {target_param} on Psi-Value",
                                                      labels={'value': target_param, 'psi_value': 'Psi-Value [W/mK]'},
                                                      markers=True)
                                        st.plotly_chart(fig, use_container_width=True)
                                        
                                        if 'fRsi' in df.columns and df['fRsi'].notnull().any():
                                            fig2 = px.line(df, x='value', y='fRsi',
                                                           title=f"Impact of {target_param} on fRsi",
                                                            labels={'value': target_param, 'fRsi': 'fRsi Factor'},
                                                           markers=True)
                                            st.plotly_chart(fig2, use_container_width=True)
                                            
                                except Exception as e:
                                    st.error(f"Sweep Failed: {e}")
                                    import traceback
                                    st.code(traceback.format_exc())
                                    
        except Exception as e:
             st.error(f"Failed to initialize BatchSimulator: {e}")
    else:
        st.warning("Please load or define a valid scenario in the Editor tab first.")

    # --- PDF Report Generation ---
    st.markdown("---")
    st.subheader("Export Report")
    
    from report_generator import generate_pdf_report
    
    col_rep1, col_rep2 = st.columns(2)
    with col_rep1:
        rep_project_name = st.text_input("Project Name", value=active_name)
        rep_author = st.text_input("Author", value="User")
    
    with col_rep2:
        rep_desc = st.text_area("Description", value="Thermal simulation of window reveal details.")
        
    if st.button("Generate PDF Report"):
        # Gather results (need to be in scope or session state)
        # We might need to re-parse or better yet, store 'last_results' in session_state.
        
        # Better approach: Check if results image exists
        img_path = f"result_{active_name}.png"
        if os.path.exists(img_path):
            # Try to reconstruct results from a simplified approach or session state
            # Ideally, 'results' should be saved. 
            # Let's check if we can read measurement values from a log or just pass empty for now if missing.
            # To do this properly, let's modify the simulation block to save to session_state.
            
            # Use 'st.session_state.get' to find results if we decide to store them
            results_for_report = st.session_state.get('last_simulation_results', {})
            
            pdf_path = f"report_{active_name.replace(' ', '_')}.pdf"
            success, msg = generate_pdf_report(
                project_name=rep_project_name,
                author=rep_author,
                description=rep_desc,
                results=results_for_report,
                image_path=img_path,
                output_path=pdf_path
            )
            
            if success:
                st.success(f"Report Generated: {pdf_path}")
                with open(pdf_path, "rb") as f:
                    st.download_button("Download Report PDF", data=f, file_name=pdf_path, mime="application/pdf")
            else:
                st.error(msg)
        else:
            st.warning("Please run the simulation first to generate results.")




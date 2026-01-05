import streamlit as st
import glob
import os
import yaml
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import sys
from io import BytesIO

# Ensure current directory is in path so we can import modules
sys.path.append(os.getcwd())

from backend.core.declarative_geometry import DeclarativeGeometry
from backend.core.dxf_importer import DXFImporter
from backend.core.simulation_engine import solve_scenario
from backend.core.solver import get_solver_lib
from backend.core.solver import get_solver_lib
from backend.core.geometry_builder import generate_scenario, COLOR_MAP, scenario_to_canvas

from streamlit_drawable_canvas import st_canvas
from backend.core.mold_analysis import calculate_surface_humidity, plot_mold_risk_map

# ... (Previous imports)

# Remove try-except, let it crash if missing
# try:
#     from streamlit_drawable_canvas import st_canvas
# except ImportError:
#     st_canvas = None

# ... (Inside tab_builder)




# --- Auto-Build for Cloud Deployment ---
# --- Auto-Build for Cloud Deployment ---
import subprocess
solver_path = os.path.join("backend", "solver", "thermal_solver_core.so")
if not os.path.exists(solver_path):
    st.warning(f"Compiling Solver to {solver_path}...")
    try:
        subprocess.check_call(["python3", "backend/solver/build_solver.py"])
        st.success("Solver compiled!")
    except Exception as e:
        st.error(f"Compilation failed: {e}")
        st.stop()
# ---------------------------------------
# ---------------------------------------

st.set_page_config(page_title="Thermal Bridge Simulator", layout="wide")

st.title("Thermal Bridge Simulator")
st.markdown("Calculate thermal bridges for window reveals using a hybrid Python/C++ solver.")

# Sidebar removed - functionality moved to main area
template = None # Placeholder so logic below doesn't break if referenced differently, 
# though we are redefining it inside the tab. 
# Better: Just define the display_names globally as before.

# 1. Template Loader - Definitions
scenario_files = glob.glob("scenarios/scenario_*.yaml") + glob.glob("scenarios/iso_*.yaml")
scenario_files.sort()
display_names = ["(New Empty)"] + [os.path.basename(f) for f in scenario_files]

# Determine default index for iso_case_1.yaml
default_scen_name = "iso_case_1.yaml"
default_idx = 0
if default_scen_name in display_names:
    default_idx = display_names.index(default_scen_name)

# Use session state to handle template loading without overwriting edits accidentally
if "yaml_editor" not in st.session_state:
    # Try to load default scenario
    default_content = """name: "My Custom Geometry"
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
    if default_idx > 0: # 0 is (New Empty)
         try:
             # Find the path
             # recreating the path logic from below mainly to get content
             # display_names mapped from scenario_files
             # indices: 0 -> None, 1 -> file[0]
             file_path = scenario_files[default_idx - 1]
             with open(file_path, 'r') as f:
                 default_content = f.read()
         except Exception as e:
             print(f"Failed to load default scenario: {e}")

    st.session_state.yaml_editor = default_content
    st.session_state.template_selector_idx = default_idx

def load_template():
    selected = st.session_state.template_selector
    if selected != "(New Empty)":
        pth = os.path.join("scenarios", selected)
        with open(pth, 'r') as f:
            # Crucial: Update the widget key directly!
            st.session_state.yaml_editor = f.read()

# Default values for logic that might depend on them if UI element is hidden/separate
transient_enabled = False
show_mold_map = False
indoor_rh = 50 
grid_override = 0.0

# Sidebar is now empty or can be used for global app info if needed
# st.sidebar.title("Configuration") - REMOVED

# --- Main Editor Area ---
# --- Main Area Tabs ---
tab_studio, tab_compare, tab_opt, tab_import, tab_help = st.tabs(["Scenario Studio", "Compare", "Optimization", "Import DXF", "Help & Reference"])

with tab_studio:
    st.header("Scenario Studio")
    st.caption("Unified workspace: Edit YAML, preview geometry, and inspect elements in one view.")
    
    # 1. Template Loader (Moved from Sidebar)
    # Using columns to make it not take up too much vertical space if needed, 
    # but full width is fine too.
    col_sel, col_dummy = st.columns([1, 1])
    with col_sel:
        # Use index to set default
        idx = st.session_state.get('template_selector_idx', 0)
        # Ensure index is valid
        if idx >= len(display_names): idx = 0
        
        template = st.selectbox("Load Scenario", display_names, index=idx, key="template_selector", on_change=load_template)

    # --- Three-Column Layout ---
    col_yaml, col_preview, col_inspector = st.columns([1.2, 1.5, 1.0])
    
    # == LEFT COLUMN: YAML Editor ==
    with col_yaml:
        st.subheader("📝 YAML Definition")
        yaml_input = st.text_area("Edit Configuration", height=450, key="yaml_editor", label_visibility="collapsed")
        
        # Validation Status
        from backend.core.ui_validation import validate_scenario_yaml, get_element_hints
        validation_res = validate_scenario_yaml(yaml_input)
        
        # Dynamic CSS for validation feedback
        # Green (#28a745) for valid, Red (#dc3545) for invalid
        border_color = "#28a745" if validation_res.is_valid else "#dc3545"
        st.markdown(f"""
        <style>
            div[data-testid="stTextArea"] textarea {{
                border: 2px solid {border_color} !important;
                box-shadow: 0 0 5px {border_color}33; 
            }}
        </style>
        """, unsafe_allow_html=True)
        
        if validation_res.is_valid:
            active_data = validation_res.data
            active_name = active_data.get('name', "Custom")
            st.success(f"✅ Valid: {active_name}")
        else:
            active_data = validation_res.data  # May be partially valid
            active_name = "Invalid"
            st.error(f"❌ {len(validation_res.errors)} errors")
            
            with st.expander("View Errors"):
                for err in validation_res.errors:
                    loc_str = " -> ".join(str(l) for l in err.loc)
                    st.warning(f"Line {err.line}: {err.message}")
                    
                st.info("💡 Required: 'name', 'canvas', 'elements'. Grid must be > 0.")
                for etype in ["rect", "wall", "window_detail"]:
                    hints = get_element_hints(etype)
                    st.caption(f"**{etype}**: {', '.join(hints)}")
        
        # Download button
        if active_data:
            st.download_button("⬇️ Download YAML", data=yaml_input, file_name=f"{active_name.replace(' ', '_')}.yaml", help="Save current configuration", type="secondary")
        
        # Apply variable overrides from session state (set by inspector sliders)
        # This must happen BEFORE preview generation
    # Variable overrides removed - edit YAML directly

    # == CENTER COLUMN: Geometry Preview ==
    with col_preview:
        st.subheader("🗺️ Geometry Preview")
        
        # Get selected element index for highlighting
        selected_el_idx = st.session_state.get('studio_selected_element', -1)
        
        # Generate preview if we have valid data
        if active_data and 'canvas' in active_data and 'elements' in active_data:
            try:
                from backend.core.geometry_builder import get_element_bbox
                from backend.core.mesh import AdaptiveMesh
                from backend.core.solver import plot_geometry
                from backend.core.geometry import build_material_grid, MaterialID
                from library.material_registry import MaterialRegistry
                
                geom = DeclarativeGeometry(active_data)
                mesh = AdaptiveMesh(geom)
                mesh.generate()
                grid_map, _ = build_material_grid(geom, mesh.xc, mesh.yc)
                
                # Determine highlight bbox
                highlight = None
                if selected_el_idx >= 0:
                    highlight = get_element_bbox(active_data, selected_el_idx)
                
                # Prepare Material Legend Map
                registry_map = {p.solver_id: p.name for p in MaterialRegistry.get().solver_id_map.values()}
                registry_colors = {p.solver_id: p.color for p in MaterialRegistry.get().solver_id_map.values()}
                
                defaults = {
                     MaterialID.AIR_EXT: "Air Ext",
                     MaterialID.AIR_INT: "Air Int",
                     MaterialID.WALL: "Wall",
                     MaterialID.INSULATION: "Insulation",
                     MaterialID.REVEAL_INS: "Reveal Ins",
                     MaterialID.FRAME: "Frame",
                     MaterialID.GLASS: "Glass",
                     MaterialID.SPACER: "Spacer",
                     MaterialID.CAVITY: "Cavity",
                     MaterialID.STYRODUR: "Styrodur",
                     MaterialID.CONCRETE: "Concrete",
                     MaterialID.WOOD: "Wood",
                     MaterialID.ALUMINUM: "Aluminum"
                }
                
                # Default colors (High Contrast Palette)
                defaults_colors = {
                     MaterialID.AIR_EXT: "#E0F7FA",  # Light Cyan
                     MaterialID.AIR_INT: "#FFFFFF",  # White
                     MaterialID.WALL: "#D3D3D3",     # LightGray (vs Concrete)
                     MaterialID.INSULATION: "#F0E68C", # Khaki (Light Yellow)
                     MaterialID.REVEAL_INS: "#FFA500", # Orange (Distinct from Ins)
                     MaterialID.FRAME: "#555555",    # DimGray
                     MaterialID.GLASS: "#87CEEB",    # SkyBlue
                     MaterialID.SPACER: "#000000",   # Black
                     MaterialID.CAVITY: "#F0FFFF",   # Azure
                     MaterialID.STYRODUR: "#BA55D3", # MediumOrchid
                     MaterialID.CONCRETE: "#708090", # SlateGray (Distinct from Wall)
                     MaterialID.WOOD: "#8B4513",     # SaddleBrown
                     MaterialID.ALUMINUM: "#B0C4DE"  # LightSteelBlue (Distinct from Grey)
                }
                
                final_names = defaults.copy()
                final_names.update(registry_map)
                
                final_colors = defaults_colors.copy()
                final_colors.update(registry_colors)

                # Generate preview with unique filename to bust cache
                # preview_file = "studio_preview.png"
                preview_buf = plot_geometry(grid_map, 
                              geom.get_canvas_config().width_mm, 
                              geom.get_canvas_config().height_mm,
                              filename=None,
                              x_coords=mesh.x_coords,
                              y_coords=mesh.y_coords,
                              highlight_bbox=highlight,
                              material_names=final_names,
                              material_colors=final_colors)
                
                # Display with unique key to force refresh
                st.image(preview_buf) # Removed width constraint to default behavior or use width='stretch' if supported, but image usually handles itself. Warning said use width='stretch'
                
            except Exception as e:
                st.warning(f"Preview error: {e}")
                import traceback
                with st.expander("Error details"):
                    st.code(traceback.format_exc())
        else:
            st.info("Define a valid scenario to see the geometry preview.")
        
        # Action Buttons
        st.markdown("---")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            run_sim_clicked = st.button("▶️ Run Simulation", type="primary")
        with col_btn2:
            refresh_preview = st.button("🔄 Refresh Preview")
            if refresh_preview:
                st.rerun()
    
    # == RIGHT COLUMN: Element Inspector ==
    with col_inspector:
        st.subheader("🔍 Inspector")
        
        # 2. Settings / Grid Override (Moved from Sidebar)
        with st.expander("⚙️ Settings", expanded=False):
            grid_override = st.number_input("Override Grid Size (mm)", 
                                           min_value=0.0, max_value=50.0, value=0.0, step=0.5,
                                           help="Set > 0 to override YAML grid size. Larger = Faster, Less Accurate.")
            
        with st.expander("🌡️ Simulation Settings", expanded=True):
             # Transient
             transient_enabled = st.checkbox("Enable Transient Simulation", value=active_data.get('transient', {}).get('enabled', False) if active_data else False, key="transient_enable_chk")
             
             if transient_enabled:
                 dur = st.number_input("Duration (hours)", min_value=0.1, max_value=48.0, value=24.0, key="trans_dur")
                 dt = st.number_input("Time Step (s)", min_value=1.0, max_value=3600.0, value=300.0, key="trans_dt")
                 save_int = st.number_input("Save Interval", min_value=1, max_value=100, value=1, key="trans_save")
                 
                 # Inject into active_data immediately
                 if active_data:
                     if 'transient' not in active_data: active_data['transient'] = {}
                     active_data['transient']['enabled'] = True
                     active_data['transient']['duration_hours'] = dur
                     active_data['transient']['dt_seconds'] = dt
                     active_data['transient']['save_interval_steps'] = save_int
             else:
                 # Ensure disabled in data if unchecked
                 if active_data and 'transient' in active_data:
                     active_data['transient']['enabled'] = False
            
             st.markdown("---")
             # Mold
             show_mold_map = st.checkbox("Calculate Mold Risk", value=False, key="mold_enable_chk")
             if show_mold_map:
                 indoor_rh = st.slider("Indoor Humidity (%)", min_value=30, max_value=80, value=50, step=5, key="mold_rh")
        
        if active_data:
            elements = active_data.get('elements', [])
            variables = active_data.get('variables', {})
            
            if elements:
                # Element selector
                el_names = [f"{i}: {el.get('name', el.get('type', 'Element'))}" for i, el in enumerate(elements)]
                sel_options = ["(None - show all variables)"] + el_names
                
                sel = st.selectbox("Select Element", sel_options, key="studio_element_selector")
                
                # Update session state for highlighting
                if sel == "(None - show all variables)":
                    st.session_state['studio_selected_element'] = -1
                    selected_el_idx = -1
                else:
                    selected_el_idx = int(sel.split(":")[0])
                    if st.session_state.get('studio_selected_element') != selected_el_idx:
                        st.session_state['studio_selected_element'] = selected_el_idx
                        st.rerun()  # Refresh to show highlight
                
                st.markdown("---")
                
                # Show element-specific params or all variables
                if selected_el_idx >= 0:
                    el = elements[selected_el_idx]
                    st.caption(f"**Type**: {el.get('type', 'unknown')}")
                    st.caption(f"**Material**: {el.get('material', 'default')}")
                    
                    params = el.get('params', {})
                    
                    # Show parameters with variable resolution
                    st.markdown("**Parameters:**")
                    for k, v in params.items():
                        if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                            var_name = v[2:-1]
                            resolved = variables.get(var_name, "?")
                            st.caption(f"`{k}`: {v} = **{resolved}**")
                        else:
                            st.caption(f"`{k}`: **{v}**")
                else:
                    # No element selected
                    st.info("Select an element above to inspect its parameters.")
                    st.caption("To edit variables, please use the YAML editor on the left.")
            else:
                st.info("No elements defined.")
        else:
            st.info("Load a valid scenario.")
    
    # --- Simulation Execution (triggered by button above) ---
    if run_sim_clicked and active_data:
        with st.spinner("Running simulation..."):
            try:
                # Apply Grid Override
                if grid_override > 0:
                    if 'canvas' not in active_data: active_data['canvas'] = {}
                    active_data['canvas']['grid'] = grid_override

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
                    final_pct = min(1.0, max(0.0, base + (pct * 0.5)))
                    prog_bar.progress(final_pct)
                    status_text.text(f"{phase}: Iteration {step}/{total} (Diff={diff:.2e})")

                results = solve_scenario(scenario_def, use_adaptive_mesh=True, progress_callback=app_progress_cb, return_plot_data=True)
                
                prog_bar.progress(1.0)
                status_text.success("Simulation Complete!")
                
                # Display Measurements
                measurements = results.get('measurements', {})
                if measurements:
                    st.subheader("📊 Results")
                    cols = st.columns(3)
                    for i, (name, res) in enumerate(measurements.items()):
                        val = res.get('value')
                        if val is None: continue
                        
                        with cols[i % 3]:
                            label = name
                            value_str = f"{val:.4f}"
                            delta = None
                            
                            if name == "Psi": label = "Ψ-Value [W/mK]"
                            elif name == "fRsi": label = "fRsi Factor"
                            elif "MinT" in name: value_str += " °C"
                            
                            if 'expected' in res:
                                expected = res['expected']
                                diff = res.get('diff', abs(val - expected))
                                passed = res.get('passed', diff < 0.1)
                                icon = "✅" if passed else "❌"
                                label = f"{icon} {label}"
                                delta = f"Err: {diff:.4f}"
                            
                            st.metric(label, value_str, delta=delta, delta_color="inverse")
                
                # Store for report
                simple_results = {k: v.get('value') for k, v in measurements.items()}
                st.session_state['last_simulation_results'] = simple_results
                # Store plot buffer for report
                if 'plot_buffer' in results:
                     st.session_state['last_plot_buffer'] = results['plot_buffer']
                
                # Show Result Image
                if active_data.get('transient', {}).get('enabled'):
                    # GIF handling
                    anim_buf = results.get('anim_buffer')
                    if anim_buf:
                        st.image(anim_buf, caption=f"Transient Animation ({active_data['transient']['duration_hours']}h)")
                        st.download_button("Download GIF", data=anim_buf, file_name=f"result_{active_name}.gif", mime="image/gif")
                    
                    final_buf = results.get('plot_buffer')
                    if final_buf:
                        st.image(final_buf, caption="Final State")
                else:
                    img_buf = results.get('plot_buffer')
                    if img_buf:
                        st.image(img_buf, caption=f"Temperature Distribution")
                        st.download_button("Download Image", data=img_buf, file_name=f"result_{active_name}.png", mime="image/png")
                
                # Mold Analysis
                if show_mold_map and not active_data.get('transient', {}).get('enabled'):
                    st.markdown("---")
                    st.subheader("🦠 Mold Risk Analysis")
                    
                    if 'temp' in results:
                        temp_field = results['temp']
                        t_int_val = active_data.get('boundary_conditions', {}).get('convective', {}).get('internal', {}).get('T', 20.0)
                        rh_grid = calculate_surface_humidity(temp_field, t_int_val, indoor_rh / 100.0)
                        
                        x_c, y_c = None, None
                        if 'mesh' in results:
                            x_c = results['mesh'].get('x_coords')
                            y_c = results['mesh'].get('y_coords')
                        
                        mold_filename = f"mold_risk_{active_name}.png"
                        
                        if x_c is not None and y_c is not None:
                            w_mm, h_mm = 0, 0
                        else:
                            b = active_data.get('canvas', {}).get('bounds', [0, 500, 0, 500])
                            w_mm = b[1] - b[0] if len(b) >= 4 else 500
                            h_mm = b[3] - b[2] if len(b) >= 4 else 500
                        
                        mold_buf = plot_mold_risk_map(rh_grid, width_mm=w_mm, height_mm=h_mm,
                                           filename=None, x_coords=x_c, y_coords=y_c)
                        st.image(mold_buf, caption=f"Mold Risk (Ti={t_int_val}°C, RHi={indoor_rh}%)")
                    else:
                        st.warning("Temperature field not found in results.")
                        
            except Exception as e:
                st.error(f"Simulation Error: {e}")
                import traceback
                st.code(traceback.format_exc())

import plotly.express as px
from backend.core.batch_simulator import BatchSimulator




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
                                        st.plotly_chart(fig)
                                        
                                        if 'fRsi' in df.columns and df['fRsi'].notnull().any():
                                            fig2 = px.line(df, x='value', y='fRsi',
                                                           title=f"Impact of {target_param} on fRsi",
                                                            labels={'value': target_param, 'fRsi': 'fRsi Factor'},
                                                           markers=True)
                                            st.plotly_chart(fig2)
                                            
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
    
    from backend.core.report_generator import generate_pdf_report
    
    col_rep1, col_rep2 = st.columns(2)
    with col_rep1:
        rep_project_name = st.text_input("Project Name", value=active_name)
        rep_author = st.text_input("Author", value="User")
    
    with col_rep2:
        rep_desc = st.text_area("Description", value="Thermal simulation of window reveal details.")
        
    if st.button("Generate PDF Report"):
        # Gather results (need to be in scope or session state)
        
        # Better approach: Check if results image exists (now in buffer)
        img_buf = st.session_state.get('last_plot_buffer')
        
        if img_buf:
            # Use 'st.session_state.get' to find results if we decide to store them
            results_for_report = st.session_state.get('last_simulation_results', {})
            
            pdf_filename = f"report_{active_name.replace(' ', '_')}.pdf"
            
            # Rewind buffer just in case
            if hasattr(img_buf, 'seek'): img_buf.seek(0)
            
            # Generate PDF in-memory (no disk write for multi-user safety)
            success, result = generate_pdf_report(
                project_name=rep_project_name,
                author=rep_author,
                description=rep_desc,
                results=results_for_report,
                image_path=img_buf, 
                output_path=None  # In-memory mode
            )
            
            if success:
                st.success("Report Generated!")
                st.download_button("Download Report PDF", data=result, file_name=pdf_filename, mime="application/pdf")
            else:
                st.error(result)
        else:
            st.warning("Please run the simulation first to generate results.")

with tab_compare:
    st.header("Side-by-Side Comparison")
    st.info("Select two scenarios to compare their thermal performance and temperature fields.")

    comp_col1, comp_col2 = st.columns(2)
    
    # helper to find file
    def get_scen_path(name):
        if name == "(New Empty)": return None
        try:
            # Reconstruct path logic same as sidebar
            # scenario_files is available in global scope of script
            idx = display_names.index(name) - 1
            if 0 <= idx < len(scenario_files):
                return scenario_files[idx]
        except:
            pass
        return None

    with comp_col1:
        st.subheader("Reference Scenario")
        # Default to first available
        r_idx = 1 if len(display_names) > 1 else 0
        ref_sel = st.selectbox("Select Reference", display_names, index=r_idx, key="comp_ref")
        
    with comp_col2:
        st.subheader("Proposed Scenario")
        # Default to second available or same
        p_idx = 2 if len(display_names) > 2 else r_idx
        prop_sel = st.selectbox("Select Proposed", display_names, index=p_idx, key="comp_prop")
        
    if st.button("Run Comparison", type="primary"):
        ref_path = get_scen_path(ref_sel)
        prop_path = get_scen_path(prop_sel)
        
        if not ref_path or not prop_path:
            st.error("Please select valid scenarios (not New Empty).")
        else:
            # Run Simulations
            # We need to run them one by one.
            import pandas as pd
            
            res_ref = None
            res_prop = None
            
            try:
                # 1. Reference
                with st.spinner(f"Simulating Reference: {ref_sel}..."):
                     # Load config
                     with open(ref_path, 'r') as f:
                        cfg_ref = yaml.safe_load(f)
                        
                     # Unique name to avoid overwrite
                     ref_run_name = f"{ref_sel}_REF"
                     cfg_ref['name'] = ref_run_name
                        
                     defprog = {"name": ref_run_name, "file_suffix": "ref", "cfg": cfg_ref}
                     res_ref = solve_scenario(defprog, use_adaptive_mesh=True, return_plot_data=True)
                
                # 2. Proposed
                with st.spinner(f"Simulating Proposed: {prop_sel}..."):
                     with open(prop_path, 'r') as f:
                        cfg_prop = yaml.safe_load(f)
                        
                     prop_run_name = f"{prop_sel}_PROP"
                     cfg_prop['name'] = prop_run_name
                        
                     defprog = {"name": prop_run_name, "file_suffix": "prop", "cfg": cfg_prop}
                     res_prop = solve_scenario(defprog, use_adaptive_mesh=True, return_plot_data=True)
                     
                st.success("Simulations Complete!")
                
                # --- Analysis ---
                
                # Table
                st.subheader("Performance Comparison")
                
                # Extract Metrics
                def get_metric(res, name):
                    return res.get('measurements', {}).get(name, {}).get('value')
                
                metrics = []
                # Psi
                psi_r = get_metric(res_ref, "Psi")
                psi_p = get_metric(res_prop, "Psi")
                if psi_r is not None and psi_p is not None:
                    diff = psi_p - psi_r
                    pct = (diff / psi_r * 100.0) if psi_r != 0 else 0.0
                    metrics.append({"Metric": "Psi-Value [W/mK]", "Reference": psi_r, "Proposed": psi_p, "Diff": diff, "% Change": pct})
                    
                # fRsi
                frsi_r = get_metric(res_ref, "fRsi")
                frsi_p = get_metric(res_prop, "fRsi")
                if frsi_r is not None and frsi_p is not None:
                    diff = frsi_p - frsi_r
                    pct = (diff / frsi_r * 100.0) if frsi_r != 0 else 0.0
                    metrics.append({"Metric": "fRsi Factor", "Reference": frsi_r, "Proposed": frsi_p, "Diff": diff, "% Change": pct})
                
                df_metrics = pd.DataFrame(metrics)
                st.dataframe(df_metrics.style.format({
                    "Reference": "{:.4f}", 
                    "Proposed": "{:.4f}", 
                    "Diff": "{:+.4f}", 
                    "% Change": "{:+.2f}%"
                }))
                
                # Visuals
                st.subheader("Temperature Distribution")
                v_col1, v_col2 = st.columns(2)
                
                import matplotlib.pyplot as plt
                
                img_r = res_ref.get('plot_buffer')
                img_p = res_prop.get('plot_buffer')
                
                with v_col1:
                    st.caption(f"Reference: {ref_sel}")
                    if img_r: st.image(img_r)
                with v_col2:
                    st.caption(f"Proposed: {prop_sel}")
                    if img_p: st.image(img_p)
                    
                # Delta Map
                st.subheader("Difference Map (Proposed - Reference)")
                
                delta = None
                interpolated_used = False
                
                # Direct match check
                if res_ref['temp'].shape == res_prop['temp'].shape:
                    delta = res_prop['temp'] - res_ref['temp']
                
                # Interpolation Fallback
                elif 'mesh' in res_ref and 'mesh' in res_prop:
                     try:
                         from scipy.interpolate import RegularGridInterpolator
                         
                         # Reference Mesh (Target)
                         ref_x = res_ref['mesh']['x_coords'] # Edges
                         ref_y = res_ref['mesh']['y_coords'] # Edges
                         # We need cell centers for RegularGridInterp? 
                         # No, temp is defined at nodes. But finite volume... 
                         # Usually temp is (ny, nx). mesh.x_coords is (nx+1).
                         # Let's use cell centers.
                         
                         def get_centers(edges):
                             return (edges[:-1] + edges[1:]) / 2.0
                             
                         ref_xc = get_centers(np.array(ref_x))
                         ref_yc = get_centers(np.array(ref_y))
                         
                         # Proposed Mesh (Source)
                         prop_x = res_prop['mesh']['x_coords']
                         prop_y = res_prop['mesh']['y_coords']
                         prop_xc = get_centers(np.array(prop_x))
                         prop_yc = get_centers(np.array(prop_y))
                         
                         # Create Interpolator (y, x) -> z
                         # Data shape is (ny, nx) -> (y, x)
                         interp = RegularGridInterpolator((prop_yc, prop_xc), res_prop['temp'], 
                                                          bounds_error=False, fill_value=None)
                         
                         # Grid to interpolate onto (Reference)
                         # mesgrid 'ij' indexing for (y, x)
                         Y_ref, X_ref = np.meshgrid(ref_yc, ref_xc, indexing='ij')
                         
                         # Interpolate
                         prop_resampled = interp((Y_ref, X_ref))
                         
                         delta = prop_resampled - res_ref['temp']
                         interpolated_used = True
                         
                     except ImportError:
                         st.warning("Scipy not found. Cannot perform interpolation for mismatched grids.")
                     except Exception as e:
                         st.warning(f"Interpolation failed: {e}")
                
                if delta is not None:
                    if interpolated_used:
                        st.info("ℹ️ Grids differed in size. 'Proposed' result was resampled to match 'Reference' grid for this plot.")
                    
                    # Plot Delta
                    fig, ax = plt.subplots(figsize=(10, 6))
                    # centered CMAP
                    # Handle NaNs from interpolation (if bounds mismatch)
                    mask_nan = np.isnan(delta)
                    if np.any(mask_nan):
                         delta = np.nan_to_num(delta, nan=0.0)
                         
                    limit = np.max(np.abs(delta))
                    if limit < 1e-3: limit = 0.1 # Avoid singular colorbar
                    
                    im = ax.imshow(delta, cmap='bwr', vmin=-limit, vmax=limit, origin='lower')
                    plt.colorbar(im, ax=ax, label="Temperature Difference [K]")
                    ax.set_title(f"Delta: {prop_sel} - {ref_sel}")
                    ax.axis('off')
                    
                    st.pyplot(fig)
                    plt.close(fig)
                else:
                    st.warning(f"Grids differ in size ({res_ref['temp'].shape} vs {res_prop['temp'].shape}) and interpolation data unavailable. Cannot compute difference map.")

            except Exception as e:
                st.error(f"Comparison Failed: {e}")
                import traceback
                st.code(traceback.format_exc())





with tab_import:
    st.header("Import from DXF")
    
    dxf_file = st.file_uploader("Upload DXF File", type=["dxf"])
    
    # Session state for generated yaml to persist across reruns
    if "dxf_yaml_preview" not in st.session_state:
        st.session_state.dxf_yaml_preview = ""
    if "dxf_importer" not in st.session_state:
        st.session_state.dxf_importer = None

    if dxf_file:
        try:
            # Instantiate Importer (loads file) - cache in session state
            if st.session_state.dxf_importer is None or st.session_state.get('dxf_filename') != dxf_file.name:
                dxf_file.seek(0)  # Reset stream position
                st.session_state.dxf_importer = DXFImporter(dxf_file)
                st.session_state.dxf_filename = dxf_file.name
                st.session_state.dxf_yaml_preview = ""  # Reset on new file
                
            importer = st.session_state.dxf_importer
            layers = importer.get_layers()
            
            st.success(f"✅ Loaded DXF: **{dxf_file.name}** | {len(layers)} layers found")
            
            # Two-column layout: Settings | Preview
            col_settings, col_preview = st.columns([1, 1.5])
            
            with col_settings:
                # Layer Mapping UI
                st.subheader("📋 Layer Mapping")
                st.caption("Map DXF layers to simulation materials. Leave empty to ignore.")
                
                # Common Materials
                common_mats = ["", "WALL", "INSULATION", "FRAME", "GLASS", "AIR_INT", "AIR_EXT", "CONCRETE", "ALUMINUM", "REVEAL_INS"]
                
                mapping = {}
                for layer in layers:
                    # Intelligent default based on name
                    default_idx = 0
                    u_layer = layer.upper()
                    if "WALL" in u_layer or "MAUER" in u_layer: default_idx = common_mats.index("WALL")
                    elif "INS" in u_layer or "DAEMM" in u_layer: default_idx = common_mats.index("INSULATION")
                    elif "FRAME" in u_layer or "RAHMEN" in u_layer: default_idx = common_mats.index("FRAME")
                    elif "GLAS" in u_layer: default_idx = common_mats.index("GLASS")
                    elif "LUFT" in u_layer or "AIR" in u_layer: default_idx = common_mats.index("AIR_EXT")
                    
                    selection = st.selectbox(f"{layer}", common_mats, index=default_idx, key=f"map_{layer}")
                    if selection:
                        mapping[layer] = selection
                
                st.markdown("---")
                
                # Import Settings
                st.subheader("⚙️ Import Settings")
                simplify_tol = st.slider(
                    "Simplification Tolerance (mm)", 
                    min_value=0.1, max_value=10.0, value=1.0, step=0.1,
                    help="Higher = fewer vertices, simpler geometry. Lower = more detail preserved."
                )
                min_area = st.slider(
                    "Min Polygon Area (mm²)", 
                    min_value=1.0, max_value=100.0, value=5.0, step=1.0,
                    help="Polygons smaller than this will be filtered out."
                )
            
            with col_preview:
                st.subheader("🔍 Geometry Preview")
                
                if mapping:
                    try:
                        # Get preview data
                        preview_data = importer.get_preview_data(mapping, simplify_tol, min_area)
                        polys = preview_data['polygons']
                        stats = preview_data['stats']
                        bounds = preview_data['bounds']
                        
                        # Statistics
                        stat_cols = st.columns(3)
                        with stat_cols[0]:
                            st.metric("Polygons", stats['polygon_count'])
                        with stat_cols[1]:
                            st.metric("Points", stats['point_count'])
                        with stat_cols[2]:
                            area_m2 = stats['total_area_mm2'] / 1e6
                            st.metric("Total Area", f"{area_m2:.3f} m²")
                        
                        st.caption(f"Materials: {', '.join(stats['materials_used'])}")
                        
                        # Matplotlib preview
                        import matplotlib.pyplot as plt
                        from matplotlib.patches import Polygon as MplPolygon
                        from matplotlib.collections import PatchCollection
                        
                        fig, ax = plt.subplots(figsize=(8, 6))
                        
                        # Color map for materials
                        mat_colors = {
                            'WALL': '#8B4513',
                            'INSULATION': '#FFD700',
                            'FRAME': '#4169E1',
                            'GLASS': '#87CEEB',
                            'AIR_INT': '#E6E6FA',
                            'AIR_EXT': '#B0E0E6',
                            'CONCRETE': '#808080',
                            'ALUMINUM': '#C0C0C0',
                            'REVEAL_INS': '#FFA500'
                        }
                        
                        patches = []
                        colors = []
                        for p in polys:
                            patch = MplPolygon(p['coords'], closed=True)
                            patches.append(patch)
                            colors.append(mat_colors.get(p['material'], '#CCCCCC'))
                        
                        if patches:
                            collection = PatchCollection(patches, facecolors=colors, edgecolors='black', linewidths=0.5, alpha=0.7)
                            ax.add_collection(collection)
                            ax.set_xlim(bounds[0], bounds[1])
                            ax.set_ylim(bounds[2], bounds[3])
                            ax.set_aspect('equal')
                            ax.set_xlabel('X (mm)')
                            ax.set_ylabel('Y (mm)')
                            ax.set_title('DXF Import Preview')
                        else:
                            ax.text(0.5, 0.5, 'No polygons extracted', ha='center', va='center', transform=ax.transAxes)
                        
                        st.pyplot(fig)
                        plt.close(fig)
                        
                    except Exception as e:
                        st.warning(f"Preview error: {e}")
                else:
                    st.info("Map at least one layer to see the preview.")
            
            # Action Buttons
            st.markdown("---")
            col_dxf_act1, col_dxf_act2, col_dxf_act3 = st.columns(3)
            
            with col_dxf_act1:
                if st.button("Convert to Scenario", type="primary"):
                    if mapping:
                        scen_dict = importer.extract_scenario(mapping, simplify_tol, min_area)
                        yaml_str = yaml.dump(scen_dict, sort_keys=False)
                        st.session_state.dxf_yaml_preview = yaml_str
                        st.toast("Conversion Successful!", icon="✅")
                    else:
                        st.warning("Please map at least one layer to a material.")
            
            with col_dxf_act2:
                if st.session_state.dxf_yaml_preview:
                    if st.button("Load into Editor"):
                         st.session_state.yaml_editor = st.session_state.dxf_yaml_preview
                         st.success("Loaded into Editor! Switch to 'Scenario Studio' tab.")
            
            with col_dxf_act3:
                if st.session_state.dxf_yaml_preview:
                    st.download_button(
                        "Download YAML", 
                        data=st.session_state.dxf_yaml_preview,
                        file_name=f"imported_{dxf_file.name.replace('.dxf', '')}.yaml",
                        mime="text/yaml"
                    )
                        
            # Show YAML Preview if available
            if st.session_state.dxf_yaml_preview:
                with st.expander("📄 Generated YAML", expanded=False):
                    st.code(st.session_state.dxf_yaml_preview, language='yaml')
                        
        except Exception as e:
            st.error(f"Failed to process DXF: {e}")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())


with tab_help:
    st.header("📚 Configuration Reference")
    st.info("The scenario configuration is based on a YAML schema. Below are the available element types and parameters.")
    
    from backend.core.scenario_schema import (
        Scenario, CanvasConfig, MaterialDef,
        RectParams, WallParams, AirParams, 
        InsulationTaperedParams, WindowDetailParams, 
        WindowSillParams, VenetianBlindParams, RoofJunctionParams
    )
    from pydantic import BaseModel
    import inspect
    
    def get_field_info(model: BaseModel):
        infos = []
        schema = model.model_json_schema()
        props = schema.get('properties', {})
        required = schema.get('required', [])
        
        for name, detail in props.items():
            desc = detail.get('description', '')
            typ = detail.get('type', 'any')
            if 'anyOf' in detail:
                typ = " | ".join([t.get('type', 'ref') for t in detail['anyOf']])
            
            # Default
            default = detail.get('default', None)
            
            req_str = "Required" if name in required else "Optional"
            
            infos.append({
                "Name": f"`{name}`",
                "Type": f"`{typ}`",
                "Required": req_str,
                "Description": desc,
                "Default": f"`{default}`" if default is not None else "-"
            })
        return infos

    # 1. Structure
    st.subheader("1. Scenario Structure")
    st.markdown("""
    A scenario file consists of several top-level sections:
    - **`name`**: Name of the scenario
    - **`canvas`**: Canvas dimensions and grid settings
    - **`materials`**: Custom material definitions
    - **`elements`**: List of geometry elements
    - **`boundary_conditions`**: Thermal boundary conditions
    - **`transient`**: Settings for time-dependent simulation
    """)
    
    # 2. ElementsTable
    st.subheader("2. Element Types")
    
    element_map = {
        "rect": RectParams,
        "wall": WallParams,
        "air": AirParams,
        "insulation_tapered": InsulationTaperedParams,
        "window_detail": WindowDetailParams,
        "window_sill": WindowSillParams,
        "venetian_blind": VenetianBlindParams,
        "roof_junction": RoofJunctionParams
    }
    
    cols = st.columns([1, 3])
    with cols[0]:
        st.markdown("**Select Element Type**")
        selected_el_type = st.radio("Type", list(element_map.keys()), label_visibility='collapsed')
        
    with cols[1]:
        st.markdown(f"### `{selected_el_type}` Parameters")
        model = element_map[selected_el_type]
        infos = get_field_info(model)
        st.table(infos)
        
    # 3. Canvas
    st.subheader("3. Canvas Config")
    st.table(get_field_info(CanvasConfig))
    
    # 4. Materials
    st.subheader("4. Material Definition")
    st.table(get_field_info(MaterialDef))

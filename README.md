# Thermal Bridge Simulation (Fensterlaibung)

A high-performance, hybrid Python/C++ Finite Element Method (FEM) solver for calculating 2D thermal bridges, specifically tailored for window reveal details. This tool is verified against **ISO 10211** standards and supports declarative geometry definitions via YAML.

## Features

-   **Hybrid Solver**: Core thermal conduction logic implemented in C++ (OpenMP parallelized) for high speed, wrapped in Python for ease of use.
-   **Declarative Geometries**: Define simulation scenarios using simple **YAML** files. No Python coding required for new geometries.
    -   Support for Points, Polygons, and parametric Variables.
    -   Built-in macros for Walls, Insulation, Window Frames, and Shutter Rails.
-   **Adaptive & Graded Meshing**: Automatically refines the grid in critical areas and uses **geometric grading** to expand cell sizes away from details, significantly reducing simulation time while maintaining ISO accuracy.
-   **ISO 10211 Verified**: Validated against **Test Cases 1 (High Precision) and 2 (Multi-Material Bridge)** from the DIN EN ISO 10211 standard.
-   **Transient Simulation**: Calculate time-dependent thermal behavior (e.g., heating curves, thermal inertia) and generate animated results.
-   **Visual Output**: Generates temperature maps (with isotherms) and concise result summaries (Psi-values, fRsi factors).
-   **Web App**: Interactive Interface using Streamlit for easy sharing and parameter exploration.

## Installation

### Prerequisites
-   **Linux** (Tested on Ubuntu/Debian)
-   **Python 3.10+**
-   **G++** (or compatible C++ compiler)
-   Python dependencies: `numpy`, `matplotlib`, `pyyaml`, `scipy`, `shapely`, `pytest`

### Setup
1.  Clone the repository.
2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Compile the C++ solver core:
    ```bash
    python3 build_solver.py
    ```
    This will generate `thermal_solver_core.so` in the project directory.

## Usage

### Running Standard Scenarios
The project comes with a set of pre-defined scenarios in the `scenarios/` directory (Scenario 1-9).

To run all scenarios using the **Adaptive Mesh** (recommended):
```bash
python3 simulation_engine.py --run-all
```

To run specific scenarios (e.g., Scenario 1 and 5):
```bash
python3 simulation_engine.py --scenarios 1 5
```

### Running Custom Scenarios
You can run any custom YAML geometry file:
```bash
python3 simulation_engine.py --scenario-file scenarios/my_custom_geometry.yaml
```

### Importing DXF/CAD
The application supports importing 2D geometry from **DXF** files. It extracts geometry from:
- **Polylines** (LWPOLYLINE, POLYLINE)
- **Hatches** (HATCH boundaries)
- **Lines** (Automatically stitches connected lines into closed loops)

1.  Open the Web Interface.

2.  Go to the **"Import DXF"** tab.
3.  Upload your `.dxf` file.
4.  Map the DXF Layers to Simulation Materials (e.g., `Layer_0` -> `WALL`).
5.  Click "Convert to Scenario".
6.  Load the generated scenario into the Editor to fine-tune or run simulations.

> **Note:** Binary **DWG** files are not directly supported. Please convert them to DXF first using a tool like *ODA File Converter* or *LibreDWG*.


### Debugging Geometries
To check your geometry definitions without running the full thermal simulation, use the `--geometries-only` flag. This will generate material map images (`geometry_check_*.png`) for visual inspection.
```bash
python3 simulation_engine.py --geometries-only
```

### Running the Web Interface
To start the interactive web application:
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

#### Transient Simulation (Time-Dependent)
The web interface includes a "Transient Simulation" mode:
1.  Open the **Scenario Editor** tab.
2.  In the Sidebar, expand the **"Transient Simulation"** section.
3.  Check **"Enable Transient"**.
4.  Configure **Duration** (hours) and **Time Step** (seconds).
5.  Click "Run Simulation". The result will be displayed as an animated GIF.

#### Side-by-Side Comparison
The **Compare** tab allows you to select two different scenarios (Reference vs. Proposed) and compare their results directly.
- **Metrics Table**: Shows differences in Psi-value and fRsi factor.
- **Side-by-Side Maps**: Visual comparison of temperature fields.
- **Delta Map**: Plots the temperature difference ($T_{prop} - T_{ref}$) to highlight areas of improvement (requires identical grid dimensions).

### Docker Support
Build and run the containerized application:
```bash
docker build -t thermal-sim .
docker run -p 8501:8501 thermal-sim
```

### Running ISO Verification Tests
To verify the solver accuracy against ISO 10211:
```bash
python3 run_iso_tests.py all
```
This runs Test Case 1 and Test Case 2 and outputs the deviation from reference values.

### Running Unit Tests
To run the project's test suite (using pytest):
```bash
pytest
```

## Configuration (YAML)

Geometries are defined in `.yaml` files. See `scenarios/scenario_1.yaml` for a simple example or `scenarios/scenario_5.yaml` for a complex parametric example.

### Structure
```yaml
name: "My Scenario"
description: "Description..."

# Define reusable variables (parametric design)
variables:
  wall_thick: 360.0
  ins_thick: 200.0

# Simulation Canvas
canvas:
  bounds: [0, 500, 0, 500] # x_min, x_max, y_min, y_max
  grid: 2.5 # Base grid size in mm

# Named Points (optional, useful for complex polygons)
points:
  P1: [0.0, 0.0]
  P2: ["${wall_thick}", 0.0]

# Geometry Elements
elements:
  - type: rect
    material: WALL # See config.py for material IDs
    params:
      x: 0
      y: 0
      width: ${wall_thick}
      height: 500

  - type: insulation_tapered
    material: INSULATION
    params: ...
```

### Supported Element Types
-   `rect`: Simple rectangle.
-   `polygon`: Arbitrary polygon defined by a list of points.
-   `wall`: Macro for wall sections.
-   `window_detail`: Macro for standard window frames (Sash + Frame + Glass).
-   `insulation_tapered`: Macro for external insulation with a tapered top edge.

## Boundary Conditions
By default, the simulation uses standard ISO conditions:
-   **Interior**: 20.0 °C (Rsi = 0.13 m²K/W)
-   **Exterior**: -5.0 °C (Rse = 0.04 m²K/W)
-   **Condensation Check**: Rsi = 0.25 m²K/W (used in a second pass for fRsi calculation).

You can override these standards per scenario in the YAML file:

```yaml
boundary_conditions:
  convective:
    # Essential for Temperature Field
    internal: { T: 22.0, R: 0.13 }
    external: { T: -10.0, R: 0.04 }
    
    # Optional: Assign specific boundary sides (top, bottom, left, right)
    # This is helpful for ISO test cases or vertical/horizontal gradients.
    bottom: { T: 20.0, R: 0.11 } 
    
  # Boundaries with no heat flow
  adiabatic:
    - top
    - right
```

### Visualizing Results
The output plots will display the actual temperatures used (`Ti` and `Te`) in the title, allowing you to instantly verify if your overrides were applied correctly. Note that metric results like **fRsi** and **Psi-value** are generally invariant to the absolute temperature difference, so check absolute temperatures (e.g., `MinT`) to confirm changes.

## Project Structure

-   `simulation_engine.py`: Main entry point for running window simulations.
-   `declarative_geometry.py`: Loader that parses YAML files into geometry objects.
-   `thermal_solver_core.cpp`: C++ implementation of the Finite Difference solver.
-   `solver.py`: Python wrapper for the C++ library.
-   `scenarios/`: Directory containing all YAML geometry definitions.
-   `run_iso_tests.py`: ISO 10211 verification runner.
-   `geometry.py`: Core geometry classes (SketchGeometry, PolygonShape).
-   `elements.py`: Library of geometry macros (Walls, Insulation, Windows, etc.).
-   `mesh.py`: Adaptive and Uniform meshing logic.
-   `config.py`: Material properties and simulation constants.
-   `tests/`: Unit and integration tests.
-   `legacy/`: Archived geometry scripts and legacy code.

## trial js frontend/backend

uvicorn backend.app.main:app --reload --port 8000

npm run dev in frontend folder

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**.
See the [LICENSE](LICENSE) file for details.
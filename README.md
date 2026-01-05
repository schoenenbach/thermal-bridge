# Thermal Bridge Simulation (Fensterlaibung)

A high-performance, hybrid Python/C++ Finite Element Method (FEM) solver for calculating 2D thermal bridges, specifically tailored for window reveal details. This tool is verified against **ISO 10211** standards and supports declarative geometry definitions via YAML.

## Features

-   **Hybrid Solver**: Core thermal conduction logic implemented in C++ (OpenMP parallelized) for high speed, wrapped in Python for ease of use.
-   **Declarative Geometries**: Define simulation scenarios using simple **YAML** files. No Python coding required for new geometries.
    -   Support for Points, Polygons, and parametric Variables.
    -   Built-in macros for Walls, Insulation, Window Frames, and Shutter Rails.
-   **Adaptive Meshing**: Automatically refines the grid in critical areas (e.g., thermal breaks, thin layers) to ensure accuracy while maintaining performance.
-   **ISO 10211 Verified**: Validated against Test Cases 1 and 2 from the DIN EN ISO 10211 standard.
-   **Visual Output**: Generates temperature maps (with isotherms) and concise result summaries (Psi-values, fRsi factors).
-   **Web App**: Interactive Interface using Streamlit for easy sharing and parameter exploration.

## Installation

### Prerequisites
-   **Linux** (Tested on Ubuntu/Debian)
-   **Python 3.10+**
-   **G++** (or compatible C++ compiler)
-   Python dependencies: `numpy`, `matplotlib`, `pyyaml`

### Setup
1.  Clone the repository.
2.  Install Python dependencies:
    ```bash
    pip install numpy matplotlib pyyaml
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

### Boundary Conditions
You can optionally override the standard boundary conditions (Temperature and Surface Resistance) in the YAML file. If omitted, standard ISO values are used (Int: 20°C/Rsi=0.13, Ext: -5°C/Rse=0.04).

```yaml
boundary_conditions:
  convective:
    internal:
      T: 20.0
      R: 0.13  # Design Rsi
    external:
      T: -5.0
      R: 0.04
    internal_check:
      R: 0.25  # For fRsi/Condensation check (Pass 2)
```

## Project Structure

-   `simulation_engine.py`: Main entry point for running window simulations.
-   `declarative_geometry.py`: Loader that parses YAML files into geometry objects.
-   `thermal_solver_core.cpp`: C++ implementation of the Finite Difference solver.
-   `solver.py`: Python wrapper for the C++ library.
-   `scenarios/`: Directory containing all YAML geometry definitions.
-   `run_iso_tests.py`: ISO 10211 verification runner.
-   `geometry.py`: Core geometry classes (SketchGeometry, PolygonShape).
-   `mesh.py`: Adaptive and Uniform meshing logic.
-   `config.py`: Material properties and simulation constants.

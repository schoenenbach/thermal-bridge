# AGENTS.md

## Project Overview
This project is a thermal bridge simulation tool designed to calculate Psi-values and fRsi temperature factors for building components. It uses a finite difference method with a hybrid Python/C++ implementation for performance.

## Core Capabilities
- **2D Heat Transfer:** Solves steady-state heat conduction equations.
- **ISO 10211 Validation:** Includes test runners for standard validation cases (Case 1 & 2). These are defined in the underlying DIN specification.
- **Geometric Primitives:** Polygon-based geometry definition using `SketchGeometry` to create elements of the configuration that should be simulated, e.g. parts of a wall or window.
- **Material Management:** Automatic `grid_map` generation for thermal conductivities.
- **Visualization:** Generates temperature vs. depth plots with isotherm contours.

## Key Files & Structure
- `solver.py`: **[CRITICAL]** The core solver module. Handles C++ library loading, conductance calculation, solving loop, and result calculation. Single source of truth.
- `simulation_engine.py`: Main entry point for running window reveal scenarios. Defines geometry configurations (`CalculationConfig`) and orchestrates the simulation.
- `run_iso_tests.py`: Validation script. Runs ISO 10211 test cases to ensure solver correctness.
- `config.py`: Central configuration for material properties (Lambda), boundary conditions (Temperatures, R-values), and `WindowConfig`.
- `geometry.py`: Base classes (`GeometryBuilder`, `SketchGeometry`) and helper functions (`build_material_grid`).
- `mesh.py`: Mesh generation logic (`UniformMesh`, `AdaptiveMesh`).
- `scenarios/`: Directory containing all YAML geometry definitions for simulation scenarios.
- `streamlit_app/`: Streamlit-based UI for interactive simulation.

## Development & Usage

### Dependencies
- Python 3.x
- `numpy`
- `matplotlib`
- `ctypes` (Standard library)
- `thermal_solver_core.so`: Compiled C++ shared library (must be present in root).

### Running Simulations
```bash
# Run specific scenarios by index (1-based from --list)
python3 simulation_engine.py --scenarios 1,5,7

# Run with uniform mesh (default is adaptive)
python3 simulation_engine.py --scenarios 1 --use-uniform-mesh

# List all available scenarios
python3 simulation_engine.py --list

# Run all window reveal scenarios (standard behavior)
python3 simulation_engine.py --run-all

# Run ISO 10211 validation tests
python3 run_iso_tests.py all
```

### Plotting Features
- **Isotherms:** Default step is 2.0°C. 
- **Critical Isotherm:** The 12.6°C line (limit for $f_{Rsi} \ge 0.70$) is formatted as a **dashed line**.
- **Adaptive Labels:** Captions are placed only at the **bottom** and **left** boundaries to prevent overlapping with cluttered geometry or other axis labels.

### Extending the Project
- **New Element Library:** Use `elements.py` to create geometries by composing simple building blocks.
  ```python
  from elements import ElementBasedGeometry, add_wall, add_insulation
  
  def build_my_scenario(sketch):
      add_wall(sketch, x=0, y=0, width=360, height=250)
      add_insulation(sketch, x=360, y=0, width=200, height=250)
      
  geom = ElementBasedGeometry([build_my_scenario], canvas_bounds=(0, 600, 0, 500))
  ```

- **New Geometries:** Define shapes in YAML scenario files using the declarative geometry system.
- **New Window Types:** Update `WindowConfig` in `config.py` or pass a custom `WindowConfig` object to `CalculationConfig`.
- **Solver Improvements:** Modify `solver.py`. Ensure backward compatibility with `run_iso_tests.py`.
- **Making changes:** The project is git versioned. Before making changes you can have a look at the git history to see what changes were made in the past. After your changes are accepted you should wrap up into a git commit and push it to the repository. Adhere to Chris Beams commit message guidelines and describe the "why" of your changes.

## Code Style & Conventions
- **Solver Logic:** Keep all solving and C++ interfacing in `solver.py`. 
- **Geometry:** Use `SketchGeometry` for flexible polygon definitions. Avoid hardcoded grid indices.
- **Units:**
  - Lengths: Millimeters (mm) primarily, converted to meters (m) for calculation.
  - Temperature: Degrees Celsius (°C).
  - Conductivity: W/(m·K).
  - Stick to SI units where not better/more common alternative is used normally.


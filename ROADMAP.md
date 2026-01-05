# Project Roadmap & Implementation Strategy

This document outlines the strategic roadmap for the Thermal Bridge Simulation project. It details ten key feature proposals designed to transition the tool from a developer-focused prototype to a professional-grade engineering application.

## 1. Extensible Material Database [DONE]

**Objective:** Decouple material definitions from code (`config.py`) to allow for a flexible, user-extensible library of standardized construction materials.

**Implementation Strategy:**
*   **Data Structure:** Create a JSON/CSV-based schema for materials including properties: `id`, `name`, `category`, `lambda` (W/mK), `density` (kg/m³), `heat_capacity` (J/kgK), and `source` (e.g., DIN 4108-4).
*   **Storage:** Implement a file-based backend in `library/materials/`.
*   **Code Changes:**
    *   Deprecate `config.py` material constants.
    *   Create `MaterialRegistry` class to load and query materials.
    *   Update `declarative_geometry.py` to lookup materials by string ID (e.g., "concrete_reinforced") instead of enum.
*   **UI:** Add a "Material Browser" in Streamlit to view and edit properties.

## 2. Expanded Component Library [DONE]

**Objective:** Enhance the `elements.py` library with high-level architectural macros to speed up geometry creation.

**Implementation Strategy:**
*   **New Macros:**
    *   `RollerShutterBox`: Parametric box with inspection lid, insulation wedge, and variable position (top/front).
    *   `WindowSill`: Aluminum (external) and Stone/Wood (internal) sills with thermal breaks.
    *   `VenetianBlindBox`: Recessed box often found in renovated facades.
    *   `RoofJunction`: Eaves detail where wall meets roof (raffer tails, insulation connectivity).
*   **Refactoring:** Convert `elements.py` functions into a class-based hierarchy (e.g., `Element` -> `Window`, `Element` -> `Shutter`) to store default parameters and validation logic.

## 3. Professional PDF Report Generation [DONE]

**Objective:** Enable the generation of signed, branded PDF reports for documentation and client submission.

**Implementation Strategy:**
*   **Technology:** Use `WeasyPrint` (HTML-to-PDF) or `ReportLab` (Direct PDF).
*   **Report Structure:**
    *   **Header:** Project Name, Date, User/Company Logo.
    *   **Input Data:** Table of materials used, boundary conditions, and geometry parameters.
    *   **Visuals:** High-res temperature map and geometry outline.
    *   **Results:** Highlighted Psi-value, fRsi-factor, and min/max temperatures.
    *   **Validation:** Signature block or disclaimer.
*   **Integration:** Add an "Export PDF" button in Streamlit that triggers the generation and offers a file download.

## 4. Parametric Parameter Sweeps [DONE]

**Objective:** Allow users to optimize designs by simulating a range of values for a specific variable.

**Implementation Strategy:**
*   **Backend:** Create a `BatchSimulator` class that:
    1.  Accepts a base YAML scenario.
    2.  Accepts a target variable (e.g., `ins_thick`) and a range (start, end, step).
    3.  Generates temporary YAMLs, runs solvers in parallel (using `multiprocessing`).
    4.  Aggregates results (Psi-value vs. Variable).
*   **UI:** New "Optimization" tab in Streamlit.
    *   Dropdown to select variable from loaded YAML.
    *   Inputs for Range/Step.
    *   Plotly chart showing the trend (e.g., Insulation Thickness vs. Psi-value).

## 5. Interactive Geometry Builder [DONE]

**Objective:** Lower the barrier to entry by providing a visual interface for creating geometries, removing the need to write YAML manually.

**Implementation Strategy:**
*   **UI Component:** Implement a custom Streamlit Component (using React/TypeScript) or use `streamlit-drawable-canvas`.
*   **Interaction:**
    *   "Drag and Drop" walls and windows onto a canvas.
    *   Snapping grid for precision.
    *   Properties panel to edit dimensions of selected elements.
*   **Synchronization:** Two-way binding: The canvas updates the YAML state, and YAML edits update the canvas.

## 6. Transient Thermal Simulation [DONE]

- **Goal**: Enable time-dependent simulations (e.g., summer heat protection).
- **Tasks**:
  - [x] Implement Heat Equation with time derivative ($\rho c_p \frac{\partial T}{\partial t} = \dots$).
  - [x] Update solver mechanics (implicit stepping for stability).
  - [x] Output: Generate animations (GIF/MP4) of temperature distribution over 24-48 hours.
  - [x] Integrate into Streamlit App (Configuration & Visualization).
- **Status**: Completed. Implemented Implicit Euler solver, added material density/capacity, GIF generation, and Streamlit UI controls.

## 7. Mold & Condensation Risk Map [DONE]

- **Goal**: Enable ISO 13788 check for mold growth risk.
- **Tasks**:
  - [x] Implement Saturation Pressure (Magnus Formula).
  - [x] Implement Surface RH Calculation ($\phi_{surf} = p_v / p_{sat, surf}$).
  - [x] Visualization: "Traffic Light" Color Map (Green/Yellow/Red) + Isoline at $\phi=0.8$.
  - [x] Integrate into Streamlit App (New "Mold & Condensation Risk" panel).
- **Status**: Completed. Added `mold_analysis.py`, unit tests, and Streamlit integration.

## 8. Side-by-Side Scenario Comparison [DONE]

**Objective:** Facilitate decision-making by visually comparing two design variants.

**Implementation Strategy:**
*   **Data Management:** Allow Streamlit to hold two simulation results in memory (Reference vs. Proposed).
*   **Visualization:**
    *   **Split View:** Two sync-scrolling maps.
    *   **Delta Map:** Compute $T_{diff} = T_{proposed} - T_{reference}$ and plot the difference field to highlight heat flow changes.
    *   **Table:** Side-by-side comparison of Psi-values and fRsi factors with % improvement calculation.

## 9. DXF/CAD Import Integration [WIP]

**Objective:** Integrate with existing CAD workflows by allowing import of geometry from DXF files.

**Implementation Strategy:**
*   **Parsing:** Use `ezdxf` library to parse ASCII DXF files.
*   **Mapping UI:**
    *   User uploads DXF.
    *   System lists layers found (e.g., "Layer_Brick", "Layer_Insulation").
    *   User maps Layers to Material IDs.
*   **Geometry Conversion:**
    *   Extract polylines/polygons from layers.
    *   Convert to internal `Polygon` representation in `geometry.py`.
    *   (Optional) Simplify geometry (douglass-peucker) to remove excessive detail (e.g., screw threads) that complicates meshing.

*   **Note on DWG:** Direct DWG support requires external converters (e.g., ODA or LibreDWG). Current solution supports native DXF. Convert DWG to DXF before import.

## 10. Cloud & CI/CD Readiness

**Objective:** Professionalize the software delivery lifecycle and enable cloud hosting.

**Implementation Strategy:**
*   **Containerization:** Optimize `Dockerfile` for production (multi-stage build to keep image small).
*   **CI Pipeline (GitHub Actions):**
    *   **Build:** Compile C++ extension.
    *   **Test:** Run `pytest` suite including ISO verification cases.
    *   **Lint:** Check Python code style (flake8/black).
*   **Cloud Architecture:**
    *   Decouple Frontend (Streamlit) from Backend (Solver).
    *   Use a Task Queue (Celery/Redis) for long-running simulations so the web server doesn't time out during transient or parametric sweeps.

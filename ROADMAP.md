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

## 9. DXF/CAD Import Integration [DONE]

**Objective:** Integrate with existing CAD workflows by allowing import of geometry from DXF files.

**Completed Tasks:**
- [x] DXF parsing with `ezdxf` library (HATCH, POLYLINE, LINE, ARC entities)
- [x] Layer-to-Material mapping UI with intelligent defaults
- [x] Polygon extraction and stitching from disconnected lines
- [x] **Configurable simplification** (Douglas-Peucker tolerance slider: 0.1-10mm)
- [x] **Configurable min area threshold** (filter small polygons: 1-100mm²)
- [x] **Live geometry preview** with matplotlib visualization before conversion
- [x] **Import statistics** (polygon count, point count, total area, materials used)
- [x] Scenario generation with proper canvas bounds and boundary conditions
- [x] "Load into Editor" and "Download YAML" actions
- [x] Unit tests for tolerance and preview functionality

**UI Flow:**
```
Upload DXF → Map Layers → Preview (with stats) → Adjust Settings → Convert → Load/Download
```

*   **Note on DWG:** Direct DWG support requires external converters (e.g., ODA or LibreDWG). Current solution supports native DXF. Convert DWG to DXF before import.


## 10. Cloud & CI/CD Readiness [DONE]

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

## 11. Schema Architecture & IDE Integration [DONE]

**Objective:** Establish a stable, strongly-typed data structure for scenarios that enables IDE validation, strict runtime checking, and future frontend migration.

**Completed Tasks:**
- [x] Add `schema_version` field to `Scenario` model (defaults to "1.0")
- [x] Define typed param schemas for all element types: `RectParams`, `WallParams`, `AirParams`, `InsulationTaperedParams`, `WindowDetailParams`, `WindowSillParams`, `VenetianBlindParams`, `RoofJunctionParams`
- [x] Create `schema_export.py` to generate JSON Schema from Pydantic
- [x] Configure VS Code YAML extension (`.vscode/settings.json`)
- [x] Create `validate_scenarios.py` helper for scenario analysis
- [x] Add 17 unit tests in `test_schema_validation.py`

**Files Added:**
- `scenario.schema.json` - JSON Schema for IDE autocomplete
- `schema_export.py` - Schema export utility
- `validate_scenarios.py` - Scenario analysis tool
- `.vscode/settings.json` - VS Code YAML extension config

**IDE Setup:** Install Red Hat YAML extension: `ext install redhat.vscode-yaml`

---

## 12. UI Validation Layer [DONE]

**Objective:** Provide real-time schema validation feedback in the Streamlit editor.

**Completed Tasks:**
- [x] Wrap YAML parsing with Pydantic validation in `app.py`
- [x] Display validation errors with line numbers in sidebar
- [x] Show element-specific hints (e.g., "rect requires x, y, width, height")

**Remaining Tasks:**
- [x] Color-code YAML text area based on validity (green/red border)

**Effort Estimate:** 1-2 hours remaining

---

## 13. Frontend Migration (React/Angular) [WIP - Phase 1 Done]

**Objective:** Migrate from Streamlit to a modern SPA framework for better UX.

**Prerequisites:**
- Schema Architecture (Done - Item 11)
- REST API design based on Pydantic models

### Phase 1: REST API Foundation [DONE]
- [x] Design REST API contract (`/api/scenarios/validate`, `/api/simulate`, etc.)
- [x] Implement FastAPI application with CORS support
- [x] Scenarios endpoints (CRUD, validate, list)
- [x] Simulation endpoint (run, optimize)
- [x] Materials endpoint (list, lookup)
- [x] Generate OpenAPI spec (auto at `/docs`)
- [x] Add 11 API unit tests

**Files Added:**
- `api/main.py` - FastAPI application
- `api/models.py` - Request/Response Pydantic models
- `api/routes/scenarios.py` - Scenario CRUD and validation
- `api/routes/simulation.py` - Simulation execution
- `api/routes/materials.py` - Material registry access
- `tests/test_api.py` - API unit tests

**Run the API:**
```bash
uvicorn api.main:app --reload
# Open http://localhost:8000/docs for OpenAPI UI
```

### Phase 2: Frontend Framework [FUTURE]
- [x] Implement WebSocket for simulation progress updates
- [x] Use JSON Schema for dynamic form generation
- [ ] Evaluate React vs. Angular as alternative frontend frameworks

**Key Features to Implement (not feasible in Streamlit):**
- [ ] Visual element creation with drag-drop and click-to-place
- [ ] Resize handles and direct manipulation of geometry
- [ ] Click-to-select elements on canvas (bidirectional Canvas ↔ Inspector sync)
- [ ] Real-time collaborative editing (optional)

**Note:** This is a significant undertaking requiring architectural changes. Consider as a separate project phase.

---

## 14. Unified Scenario Studio [DONE]

**Objective:** Integrate YAML editor, geometry preview, and element inspector into a single cohesive workspace.

**Completed Tasks:**
- [x] Merge "Scenario Editor" and "Geometry Builder" tabs into single "Scenario Studio" 
- [x] Implement 3-column layout (YAML | Preview | Inspector)
- [x] Add live geometry preview on YAML validation
- [x] Add element highlighting via red dashed bounding box
- [x] Add variable sliders in inspector panel
- [x] Add `highlight_bbox` parameter to `plot_geometry` in `solver.py`
- [x] Add `get_element_bbox` helper in `geometry_builder.py`

**UI Layout:**
```
┌────────────┬──────────────┬─────────────┐
│ YAML       │  Geometry    │  Element    │
│ Editor     │  Preview     │  Inspector  │
│            │  + Highlight │  + Sliders  │
└────────────┴──────────────┴─────────────┘
```


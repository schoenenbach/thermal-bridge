# Project Roadmap & Implementation Strategy

This document outlines the strategic roadmap for the Thermal Bridge Simulation project. It details key feature proposals designed to transition the tool from a developer-focused prototype to a professional-grade engineering application.

---

## Critical Improvements (External Review Feedback)

The following items address shortcomings identified during external review that prevent the tool from being "certification-grade" (comparable to Flixo or Psi-Therm).

### C1. Replace SOR Solver with Sparse Direct Solver [HIGH PRIORITY]

**Problem:** The C++ SOR solver scales poorly ($O(N^{1.5})$ to $O(N^2)$) and struggles with stiff matrices (e.g., Steel λ=50 next to Insulation λ=0.035). Additionally, `thermal_solver_core.cpp` allocates a `std::vector<double>` inside `solve_step`, causing heap allocation on every call.

**Solution:** Replace the C++ extension with `scipy.sparse.linalg.spsolve` (SuperLU/UMFPACK backend).

**Implementation Strategy:**
- [ ] Build sparse matrix $A$ from conductance arrays in `solver.py`
- [ ] Replace iterative `solve()` with direct `spsolve(A, b)`
- [ ] Remove or deprecate C++ `thermal_solver_ext` module
- [ ] Validate: ISO 10211 Cases 1 & 2 must still pass
- [ ] Benchmark: Expect millisecond-scale solve times for <200k nodes

**Files Affected:**
- `backend/core/solver.py` - New sparse matrix assembly and direct solve
- `backend/solver/thermal_solver_core.cpp` - Deprecate or remove

---

### C2. Refactor Boundary Condition Assembly [HIGH PRIORITY]

**Problem:** Surface resistance ($R_{si}$, $R_{se}$) application is currently hardcoded in `run_iso_tests.py` (test script), not in the core solver. This means general user scenarios cannot properly apply boundary conditions.

**Solution:** Move boundary condition assembly into `mesh.py` or a dedicated `boundary.py` module.

**Implementation Strategy:**
- [ ] Create boundary condition detection in mesh layer (identify boundary cells)
- [ ] Apply film coefficient ($h = 1/R$) to conductance matrix during assembly
- [ ] Support interior ($R_{si}$) and exterior ($R_{se}$) surfaces per ISO standards
- [ ] Remove manual patches from `run_iso_tests.py`
- [ ] Validate: ISO 10211 Cases must pass using core logic only

**Files Affected:**
- `backend/core/mesh.py` - Add boundary detection and BC assembly
- `backend/core/run_iso_tests.py` - Remove manual conductance patches (lines 315-329)

---

### C3. Implement ISO 10077-2 Air Cavity Iteration [MEDIUM PRIORITY]

**Problem:** Air cavities currently use a static conductivity (`MAT_CAVITY_ISO = 0.25` in `config.py`). ISO 10077-2 mandates iterative calculation where $\lambda_{eq}$ depends on cavity aspect ratio and surface temperature difference (radiation + convection).

**Solution:** Implement an iterative cavity solver wrapper.

**Implementation Strategy:**
- [ ] Pre-process: Detect connected air cells via flood-fill to identify distinct cavities
- [ ] Calculate cavity geometry (dimensions, aspect ratio)
- [ ] Implement $\lambda_{eq}$ formula per ISO 10077-2:
  - Convective: $h_a = max(0.025/d, 0.73 \cdot (Ra^{0.25}))$
  - Radiative: $h_r = 4\sigma T_m^3 / (1/\epsilon_1 + 1/\epsilon_2 - 1)$
  - $\lambda_{eq} = d \cdot (h_a + h_r)$
- [ ] Outer solve loop: Run thermal solve → recalculate $\lambda_{eq}$ → update matrix → repeat until convergence
- [ ] Add emissivity property to MaterialRegistry

**Files Affected:**
- `backend/core/config.py` - Remove static `MAT_CAVITY_ISO`
- `backend/core/solver.py` - Add iterative wrapper
- `library/materials/` - Add emissivity to material definitions

---

### C4. Tighten Verification Tolerance [MEDIUM PRIORITY]

**Problem:** Current ISO 10211 Case 2 flux tolerance is 5% (`abs(flux - 9.5) < 0.5`), which is too loose. ISO validation typically requires <1% precision.

**Solution:** Tighten tolerance to 1% (0.1 W/m) and improve flux summation accuracy.

**Implementation Strategy:**
- [ ] Change `run_iso_tests.py` line 356: `flux_passed = abs(flux_in - 9.5) < 0.1`
- [ ] Review half-cell control volume handling in flux calculation
- [ ] If test fails with tighter tolerance, increase mesh resolution or refine numerics
- [ ] Document required mesh density for ISO compliance

**Files Affected:**
- `backend/core/run_iso_tests.py` - Tighten tolerance

---

### C5. Material Averaging (Anti-Aliasing) for Diagonal Lines [MEDIUM PRIORITY]

**Problem:** The current mesher assigns discrete material IDs per cell, causing "staircase effects" on diagonal geometry boundaries.

**Solution:** Implement sub-cell material averaging.

**Implementation Strategy:**
- [ ] For cells intersecting multiple materials, calculate area-weighted average $\lambda$
- [ ] Use sub-sampling (e.g., 4×4 grid within each cell) for coverage estimation
- [ ] Apply weighted harmonic mean for series conductivity, arithmetic mean for parallel

**Files Affected:**
- `backend/core/geometry.py` - Add sub-cell sampling in `build_material_grid`

---

### C6. Scenario-First Architecture [LOW PRIORITY]

**Problem:** `geometry_builder.py` attempts to reverse-engineer semantic Scenario from Canvas JSON objects (fragile "round-trip" conversion).

**Solution:** Make the YAML Scenario the single source of truth. Canvas should render the Scenario, not generate it.

**Implementation Strategy:**
- [ ] When user edits geometry in Canvas, update Scenario state first
- [ ] Re-render Canvas from updated Scenario
- [ ] Remove reverse-engineering logic from `geometry_builder.py`

**Files Affected:**
- `backend/core/geometry_builder.py`
- `frontend/src/components/editor/` - Update state flow

---

### C7. Client-Side Heatmap Rendering [LOW PRIORITY]

**Problem:** API returns static PNG for temperature visualization, preventing interactive features.

**Solution:** Return compressed temperature array to frontend; render with HTML5 Canvas/WebGL.

**Implementation Strategy:**
- [ ] API endpoint returns binary/JSON temperature data instead of PNG URL
- [ ] Frontend: Implement WebGL or Canvas-based heatmap renderer
- [ ] Add "Probe tool" for hovering to see values
- [ ] Add dynamic color scale controls
- [ ] Highlight mold risk areas (surfaces with $T < T_{dew}$ or $\phi > 80\%$)

**Files Affected:**
- `backend/app/routes/simulation.py` - Return temperature array data
- `frontend/src/components/` - New heatmap component

---

## Recommended Priority Order

1. **C1** (Solver) + **C2** (Boundary Conditions) - Foundation for accurate results
2. **C4** (Tolerance) - Quick win, validates improved numerics
3. **C3** (Air Cavities) - Required for ISO 10077-2 compliance
4. **C5** (Material Averaging) - Improves geometric accuracy
5. **C6** + **C7** (UX) - Usability improvements

---

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

## 13. Frontend Migration (React/Angular) [WIP - Phase 3B Done]

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

### Phase 2: Repository Restructuring (Phase 2A) [DONE]
- [x] Create directory structure (`backend/`, `legacy_app/`, `frontend/`)
- [x] Separate Core Logic from API and Streamlit UI
- [x] Update imports and Dockerfile

### Phase 3: Frontend Implementation (React + Vite)
**Phase 3A: Setup & Proof of Concept [DONE]**
- [x] Initialize React Project
- [x] Generate TypeScript Client from OpenAPI (Manual Fallback)
- [x] Implement Basic Scenario List & View

**Phase 3B: Interactive Geometry Editor (The Deep Dive) [DONE]**
- [x] Implement Canvas with `react-konva`
- [x] Implement Scene Graph <-> Schema synchronization (via local state)
- [x] Drag-and-Drop and Resize interactions

**Phase 3C: Professional UI & UX [DONE]**
*Objective:* Adopt a professional UI library to match the "engineered" look of the legacy app.
- [x] **Adopt UI Library**: Integrated **MUI (Material UI) v7** for consistent styling.
    - Replaced raw CSS buttons/inputs with MUI components.
    - Created `theme.ts` with compact density settings.
- [x] **Inspector Panel Refactor**: Re-implemented `Inspector.tsx` using MUI Accordion.
    - Collapsible sections for Grid, Simulation, Variables, and Element Properties.
    - MUI TextField with InputAdornments for units.

**Phase 3D: Performance & Optimization**
*Objective:* Ensure the app runs smoothly even during heavy simulations.
- [ ] **Simulation Throttling**:
    - Debounce WebSocket progress updates (max 10fps).
    - Throttle geometry canvas re-renders during drag operations.
- [ ] **React Optimization**:
    - Use `React.memo` for heavy components (GeometryEditor).
    - Virtualize the Scenario List if it gets too long.

**Phase 3E: Feature Parity & Completion**
*Objective:* Restore all features from the legacy Streamlit app.
- [ ] **Results Visualization**:
    - Re-implement "Temperature Map" using a canvas or simplified image overlay.
    - Re-implement "Mold Risk" traffic light view.
- [ ] **Material Browser**:
    - Frontend UI for searching/filtering the material API.
- [ ] **PDF Export**:
    - Trigger backend PDF generation and handle file download.

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


---

## 15. Advanced Mold Risk Assessment (VTT & Isopleths) [PLANNED]

**Objective:** Upgrade mold analysis from a simple stationary threshold to professional-grade hygrothermal assessment, leveraging the transient outputs of the new HAM solver.

**Implementation Strategy:**
*   **Dependency:** Requires **Hygrothermal Solver Engine** (Item 19) for accurate internal T/RH history.
*   **Material Sensitivity:** Add `mould_sensitivity` (Sensitive/Medium/Resistant) to `MaterialRegistry`.
*   **Bio-Hygrothermal Model:** Implement VTT Mould Index calculation:
    *   $M = f(T, RH, t, material)$
*   **Visualizations:**
    *   **Isopleth Diagram:** T/RH scatter plot with LIM (Lowest Isopleth for Mould) curves.
    *   **Mould Index History:** Time-series chart of index evolution (0-6 scale).

## 16. Usage Scenarios & Room Classes [DONE]

**Objective:** Simplify boundary condition setup by providing standard room profiles.

**Completed Tasks:**
- [x] **Room Profile Registry**: `library/room_profile_registry.py` (singleton pattern)
- [x] **Profile Data**: `library/room_profiles/room_profiles.json` with 8 presets
    - Living Room, Bedroom, Bathroom, Kitchen, Office, Warehouse, Swimming Pool, Laundry
    - T/RH values per DIN 4108-2 / EN ISO 13788
    - Humidity classes 1-5 per ISO 13788 Table 2
- [x] **Schema Update**: Added `room_type` field to `BoundaryConditions` in `scenario_schema.py`
- [x] **Streamlit UI**: Room Type dropdown in Inspector panel
- [x] **Unit Tests**: 15 tests in `tests/test_room_profiles.py`

**Files Added:**
- `library/room_profiles/room_profiles.json` - Room profile presets
- `library/room_profile_registry.py` - Registry singleton
- `tests/test_room_profiles.py` - Unit tests

**Run Tests:**
```bash
python3 -m pytest tests/test_room_profiles.py -v
```


## 17. Extended Validation & Benchmarks [DONE]

**Objective:** Ensure physical correctness through normative test cases (Stationary & Empirical).

**Completed Tasks:**
- [x] **Glaser Method (ISO 13788)**: Implemented interstitial condensation analysis
    - `glaser_method.py`: Layer dataclass, temperature/vapor profiles, monthly analysis
    - Humidity class calculations per ISO 13788 Table 2
- [x] **VTT Mould Index Model**: Implemented dynamic mold growth assessment
    - Extended `mold_analysis.py` with Hukka & Viitanen (1999) model
    - Material sensitivity classes (Very Sensitive → Resistant)
    - Critical RH curves, growth/decline rates, time-series simulation
- [x] **Test Suites**: 44 unit tests across 3 test files
    - `test_glaser_method.py`: 16 tests for ISO 13788 compliance
    - `test_vtt_benchmarks.py`: 25 tests for VTT model validation
    - Verified against published empirical data

**Files Added:**
- `backend/core/glaser_method.py` - ISO 13788 Glaser method implementation
- `tests/test_glaser_method.py` - Glaser method unit tests
- `tests/test_vtt_benchmarks.py` - VTT Mould Index benchmarks

**Run Tests:**
```bash
python3 -m pytest tests/test_glaser_method.py tests/test_vtt_benchmarks.py -v
```

---

## 18. Material Database 2.0 (Functional Properties) [PLANNED]

**Objective:** Support moisture-dependent material properties required for HAM simulation.

**Implementation Strategy:**
*   **Extended Schema:** Add support for functional definitions (tables/curves) instead of scalar constants.
    *   **Sorption Isotherm:** $w(\phi)$
    *   **Vapor Permeability:** $\delta(\phi)$
    *   **Liquid Conductivity:** $K(w)$
    *   **Thermal Conductivity:** $\lambda(w)$
*   **Interpolation:** Implement Cubic Spline interpolation for smooth derivatives during solving.

## 19. Hygrothermal Solver Engine (Coupled Heat & Moisture) [PLANNED]

**Objective:** Implement the coupled PDE system for heat and moisture transport (EN 15026 compliant).

**Implementation Strategy:**
*   **Physics:**
    *   **Mass Balance:** $\nabla \cdot (\delta_p \nabla p_v + K \nabla P_c)$
    *   **Energy Balance:** Includes latent heat of evaporation/condensation.
*   **Numerics:**
    *   **Primary Variables:** Temperature ($T$) and Capillary Pressure ($P_c$).
    *   **Time Integration:** Integrate **CVODE** (Sundials) for implicit, adaptive time-stepping to handle stiff systems.
    *   **Jacobian:** Analytical Jacobian for performance.

## 20. Advanced Boundary Conditions (Climate & Rain) [PLANNED]

**Objective:** Simulate real-world climatic loading including driving rain.

**Implementation Strategy:**
*   **Climate Loader:** Parser for `.epw` (EnergyPlus) and `.wac` (WUFI) weather files.
*   **Driving Rain:** Implement ISO 15927-3 model for wind-driven rain flux.
*   **Boundary Switching:** Dynamic switching between Flux (raining) and Dirichlet (saturation) boundaries.

## 21. Compliance Validation (HAMSTAD) [PLANNED]

**Objective:** Verify physical correctness against the specialized HAMSTAD benchmarks.

**Implementation Strategy:**
*   **Benchmark 1:** Interstitial Condensation (Insulated Roof).
*   **Benchmark 4:** Response Analysis (Driving Rain dynamics).
*   **EN 15026 Annex A:** Automated regression test for the analytical benchmark case.

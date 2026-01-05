# Scenario Migration Guide

This guide describes how to refactor legacy scenario files to conform to the new **Strict Scenario Schema** (enforced by `scenario_schema.py` and `declarative_geometry.py`).

## 1. Goal

The objective is to make every `scenario_*.yaml` file **fully self-contained**.
- **No dependencies** on `elements.py` hardcoded defaults.
- **No dependencies** on external library files (which have been deleted).
- **Explicit Materials**: Materials must be defined in the `materials` block.
- **Explicit Geometry**: Variables should be used for dimensions; "magic numbers" should be minimized.

## 2. The New standard

Reference Files:
- `scenarios/iso_case_1.yaml`: Simple, minimal example.
- `scenarios/scenario_1.yaml`: Complex example with variables, points, and polygons.

### Key Sections

#### A. Explicit Material Definitions
Every scenario **must** define its materials. This ensures the solver receives the correct Conductivity and ID, regardless of global defaults.

```yaml
materials:
  - id: WALL
    lambda: 0.8
    color: "#AAAAAA"
  - id: INSULATION
    lambda: 0.035
    color: "#FFCC00"
  - id: AIR_INT
    lambda: 0.025
    color: "#FFFFFF"
    solver_id: 1  # Reserved ID for Internal Air
```

**Common Reserved IDs:**
- `AIR_EXT`: 0
- `AIR_INT`: 1
- `WALL`: 2
- `INSULATION`: 3

#### B. Variables
Move all hardcoded dimensions into the `variables` block. Use variable substitution `${var}` in the geometry.

```yaml
variables:
  wall_thick: 360.0
  win_pos: 150.0
  # Calculated/Derived
  x_wall_ext: 410.0
```

#### C. Points (Optional but Recommended for Polygons)
Define named points for complex shapes.

```yaml
points:
  Wall_BL: [0.0, 0.0]
  Wall_TR: ["${x_wall_ext}", 500.0]
```

#### D. Elements
Instantiate elements using the local material IDs.

```yaml
elements:
  - type: rect
    material: WALL  # Matches 'id' in materials block
    params:
      x: 0.0
      y: 0.0
      width: ${wall_thick}
      height: 500.0
```

## 3. Migration Workflow for Future Agents

To refactor a legacy scenario (e.g., `scenario_4.yaml`):

1.  **Analyze the Legacy File**:
    - Identify used materials (look for `material: "WALL"`, etc.).
    - Identify hardcoded coordinates.
    - Check for `references:` comments (legacy).

2.  **Add `materials` Block**:
    - Copy the standard material block from `scenario_1.yaml`.
    - Remove unused materials to keep it clean (optional).

3.  **Create `variables` Block**:
    - Extract dimensions (wall thickness, insulation thickness, offsets).
    - Create derived variables for key X/Y coordinates to avoid math in `params`.

4.  **Refactor `elements`**:
    - Replace hardcoded numbers with `${variables}`.
    - Ensure `material` fields match the IDs in the `materials` block.
    - If `type: polygon` is used, ensure `points` are defined in the `points` block.

5.  **Verify**:
    - Run: `python3 simulation_engine.py --scenario-file scenarios/scenario_X.yaml`
    - Check the output logs for `[PASS]` (if measurements exist) or visually check the generated `result_*.png`.
    - Ensure `Psi` and `fRsi` values look reasonable (comparable to previous results).

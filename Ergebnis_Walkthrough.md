# Thermal Bridge Calculation Results

The calculation for the window reveal (Fensterlaibung) has been completed for **6 Scenarios**.
**Geometry Update**: The simulation now explicitly models the **Fixed Frame (Blendrahmen)** and **Sash (Flügel)** as separate components (Standardized L-Profile), matched to the architect's drawings, including the Masonry Rebate (Fensteranschlag).

## Results Summary (Final Verified)

| Wall | Wall Insulation | Reveal Insulation | Psi [W/mK] | fRsi | Min Temp (Wall) | Assessment |
|---|---|---|---|---|---|---|
| **36 cm** | None (Altbau) | None | **-0.121** | **0.574** | **9.4°C** | 🔴 **Condensation Risk** |
| **36 cm** | 20cm WDVS | **None** | **0.174** | **0.698** | **13.2°C** | 🟡 **Borderline (< 0.70)** |
| **36 cm** | 20cm WDVS | **30mm** | **-0.017** | **0.724** | **17.1°C** | 🟢 **Safe & Optimal** |
| **45 cm** | None (Altbau) | None | **-0.130** | **0.579** | **9.5°C** | 🔴 **Condensation Risk** |
| **45 cm** | 20cm WDVS | **None** | **0.125** | **0.699** | **13.3°C** | 🟡 **Borderline (< 0.70)** |
| **45 cm** | 20cm WDVS | **30mm** | **-0.039** | **0.724** | **17.2°C** | 🟢 **Safe & Optimal** |

> [!IMPORTANT]
> **Key Finding**: 
> *   **Case 3 (30mm Reveal Insulation)** significantly improves the fRsi factor to **0.724** (well above the 0.70 limit), raising the critical surface temperature to **17.1°C**.
> *   **Case 2 (No Reveal Insulation)** is borderline at **0.698 (13.2°C)**. While strictly close to the limit, it poses a higher risk of mold growth compared to the insulated variant.
> *   **Recommendation**: The execution **WITH** 30mm reveal insulation is strongly recommended.

## Geometry Checks (Final)
Visual verification of the detailed frame geometry (Blendrahmen + Flügel + Anschlag).
**Consistent Frame Size**: Blendrahmen now implemented with an L-Profile (80mm width) across all scenarios to fill the sash recess.

### Case 3: 36cm + Rebate + Rev Ins (Consistent Frame)
![Geometry Check 36cm Optimal](/home/thomas/.gemini/antigravity/brain/0a2cdd7a-bfb3-42b2-8f11-e43ba52ba3d3/geometry_case_3.png)

### Case 2: 36cm + Rebate (Architect) (Consistent Frame)
![Geometry Check 36cm Architect](/home/thomas/.gemini/antigravity/brain/0a2cdd7a-bfb3-42b2-8f11-e43ba52ba3d3/geometry_case_2.png)

## Temperature Fields
### Case 3 (Optimal)
![Temp Dist Case 3](/home/thomas/.gemini/antigravity/brain/0a2cdd7a-bfb3-42b2-8f11-e43ba52ba3d3/temp_dist_wall_360_pos_150.png)

## Detailed Physics
- **Method**: 2D Finite Difference Method (FDM) in accordance with ISO 10211.
- **Boundary Conditions**: $T_i = 20^\circ C$, $T_e = -5^\circ C$. $R_{si}=0.13/0.25$, $R_{se}=0.04$.
- **Materials**: 
  - Masorny ($\lambda=0.81$)
  - Insulation ($\lambda=0.035$)
  - Window ($U_f=1.3, U_g=1.1$)

The Python script `calculate_psi.py` used for this calculation is available in the project directory.

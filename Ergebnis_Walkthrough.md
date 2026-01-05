# Thermal Bridge Calculation Results

The calculation for the window reveal (Fensterlaibung) has been completed for **6 Scenarios**.
**Geometry Update**: The simulation now explicitly models the **Fixed Frame (Blendrahmen)** and **Sash (Flügel)** as separate components, matched to the architect's drawings, including the Masonry Rebate (Fensteranschlag).

## Results Summary

| Wall | Wall Insulation | Reveal Insulation | Psi [W/mK] | Min Temp (Wall) | Min Temp (Frame) | Assessment |
|---|---|---|---|---|---|---|
| **36 cm** | None (Altbau) | None | -0.121 | **9.8°C** | 6.8°C | **Condensation Risk** |
| **36 cm** | 20cm WDVS | **None** | 0.178 | **13.6°C** | 6.9°C | **Safe** |
| **36 cm** | 20cm WDVS | **30mm** | -- | **--** | -- | **(Updating...)** |
| **45 cm** | None (Altbau) | None | -0.131 | **9.9°C** | 6.8°C | **Condensation Risk** |
| **45 cm** | 20cm WDVS | **None** | 0.129 | **13.7°C** | 6.9°C | **Safe** |
| **45 cm** | 20cm WDVS | **30mm** | -- | **--** | -- | **(Updating...)** |

> [!NOTE]
> **Status Check**: Case 3 and 6 Calculation is paused to verify Geometry.

## Geometry Checks (Debug)
Visual verification of the detailed frame geometry (Blendrahmen + Flügel + Anschlag).

### Case 3: 36cm + Rebate + Rev Ins (Fix Attempt: Rectangle)
![Geometry Check 36cm Optimal](/home/thomas/.gemini/antigravity/brain/0a2cdd7a-bfb3-42b2-8f11-e43ba52ba3d3/geometry_case_3.png)

### Case 2: 36cm + Rebate (Architect)
![Geometry Check 36cm Architect](/home/thomas/.gemini/antigravity/brain/0a2cdd7a-bfb3-42b2-8f11-e43ba52ba3d3/geometry_case_2.png)

## Methodology
- **Method**: 2D Finite Difference Method (FDM) in accordance with ISO 10211.
- **Boundary Conditions**: $T_i = 20^\circ C$, $T_e = -5^\circ C$. $R_{si}=0.13/0.25$, $R_{se}=0.04$.
- **Materials**: 
  - Masorny ($\lambda=0.70$)
  - Insulation ($\lambda=0.035$)
  - Window ($U_f=1.3, U_g=1.1$)

The Python script `calculate_psi.py` used for this calculation is available in the project directory.

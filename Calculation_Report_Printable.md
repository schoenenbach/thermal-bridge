  # Thermal Bridge Calculation Report
**Project:** Window Reveal Renovation (Fensterlaibung)  
**Date:** 2025-12-18  
**Method:** 2D Finite Difference Method (FDM) according to ISO 10211

---

## Executive Summary

The thermal analysis compares the existing building condition ("Altbau") with two renovation scenarios for the window reveal:
1.  **Standard Renovation**: External Wall Insulation (WDVS) + New Window, but **NO** insulation on the reveal (Masonry Rebate only).
2.  **Optimized Renovation**: External Wall Insulation (WDVS) + New Window + **30mm Reveal Insulation**.

### Assessment
*   **Case 3 (Optimized with 30mm Reveal Insulation)** is the recommended solution. It raises the critical internal surface temperature to **17.1°C**, eliminating condensation and mold risk ($f_{Rsi} = 0.724 > 0.70$).
*   **Case 2 (Standard Renovation without Reveal Insulation)** is borderline safe. The surface temperature reaches **13.2°C** ($f_{Rsi} = 0.698$), which is just below the recommended safety limit of 0.70, leaving a residual risk of mold growth if indoor humidity is high.

---

## Detailed Results

### Simulation Parameters
*   **Interior Temperature:** 20.0 °C
*   **Exterior Temperature:** -5.0 °C
*   **Wall Construction:** solid Brick ($\lambda=0.81$).
*   **Window System:** $U_f=1.3$ W/m²K, $U_g=1.1$ W/m²K.
*   **Geometry:** High-Detail Frame including Masonry Rebate (Fensteranschlag) and Sash (Flügel).

### Results Table

| Scenario | Description | $\Psi$ Value [W/mK] | $f_{Rsi}$ Factor | Min Temp (Wall) | Min Temp (Frame) | Min Temp (Glass) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Case 1** | **Istzustand (36cm)** | -0.121 | **0.574** | **9.4 °C** | 10.2 °C | 13.1 °C |
| **Case 2** | **Dämmung Fassade (No Rev Ins)** | +0.174 | **0.698** | **13.2 °C** | 12.5 °C | 13.1 °C |
| **Case 3** | **Dämmung Fassade und Laibung (30mm Rev Ins)** | **-0.017** | **0.724** | **17.1 °C** | **14.6 °C** | 13.1 °C |


> **Note on $\Psi$-Values:** Negative $\Psi$-values indicate that the actual heat loss of the corner is *less* than the simplified 1D surface calculation would suggest (Geometry Bonus).

---

## Visual Documentation

### Case 3: Optimized Geometry (30mm Reveal Insulation)
The insulation (purple) continuously wraps the corner, keeping the masonry (red/orange) warm.
![Case 3 Geometry](/home/thomas/Desktop/Fensterlaibung_rollläden/geometry_case_3.png)

#### Temperature Field (Isotherms)
![Case 3 Temperature](/home/thomas/Desktop/Fensterlaibung_rollläden/temp_dist_wall_360_pos_150.png)

### Case 2: Standard Geometry (No Reveal Insulation)
The masonry rebate remains uninsulated.
![Case 2 Geometry](/home/thomas/Desktop/Fensterlaibung_rollläden/geometry_case_2.png)

---

## Conclusion
To ensure long-term freedom from mold and condensation, the execution of **Case 3 / Case 6 (30mm Reveal Insulation)** is strongly advised. The standard execution without reveal insulation (Case 2) does not provide a robust safety margin.

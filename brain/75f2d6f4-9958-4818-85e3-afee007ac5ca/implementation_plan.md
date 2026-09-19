
### 3. Battery Degradation (`src/hybrid_model.py`)
    - **Energy Balance**: Stacked Area Chart (Solar, Grid, Battery).
    - **Cashflow**: Waterfall or Bar chart for annual cashflows.
- **Layout**: Use `st.columns` more effectively to reduce scrolling.

## Verification Plan
### Automated Tests
- `test_phase7.py`: Verify Horizon, TOU, Civil calculations.

### Manual Verification
- Check if graphs look "Professional" (no default rainbow colors).
- Verify Layout Visualizer shows individual modules.

# Phase 9: 3D Realism (Ultra-High Fidelity)

## Goal
Achieve "most realistic possible" visualization of the PV array using Plotly 3D.

## Proposed Changes
### `src/design.py`
#### [MODIFY] `visualize_layout_3d`
- **Extruded Frame**: Add side faces to the frame mesh to give it physical thickness (30-40mm).
- **Racking Structure**: Add `go.Scatter3d` traces for vertical piles (posts) and horizontal torque tubes/rails.
- **Cell Grid**: Add faint grid lines to simulate individual cells on the module surface.
- **Materials**: Fine-tune lighting for glass-like reflection on cells and matte finish on frames.

## Verification
- **Visual Check**: Ensure panels look like physical objects with depth, not flat planes.
- **Performance**: Ensure the browser does not crash with the added geometry (optimize vertex counts).

### Potential Enhancements (Menu)
- **Environment**: Textured ground (grass/earth), Sky background.
- **Infrastructure**: 3D Inverter Stations (concrete pads + boxes), Perimeter Fencing, Access Roads.
- **Dynamic Elements**: Interactive Sun Position slider to show real-time shadowing.
- **Context**: 3D Human figure for scale, Compass Rose.
- **Ground Types**: Dropdown to select:
    - Grass (#4CAF50)
    - Sand/Desert (#E6C288)
    - Gravel (#9E9E9E)
    - Dirt (#795548)
    - Snow (#FFFFFF)
- **Details**: Cable trays, Combiner boxes at row ends.

# Phase 10: CAD Optimization (Performance)

## Goal
Enable rendering of large utility-scale arrays (10k+ modules) without browser lag or crashes.

## Proposed Changes
### `src/design.py`
#### [REFACTOR] `visualize_layout_3d`
- **Current State**: Creates 3 traces *per row* (Frame, Cells, Shadow). For 100 rows, that's 300 traces. Overhead is high.
- **New State**:
    1.  Pre-allocate Numpy arrays for all vertices and indices.
    2.  Vectorize the rotation and translation logic (remove inner loops).
    3.  Create exactly **3 Traces Total** for the array:
        -   `Global_Frames` (Silver)
        -   `Global_Cells` (Blue)
        -   `Global_Shadows` (Black transparent)
    4.  This reduces draw calls from N_rows * 3 to just 3, massively improving FPS and load time.

## Verification
- **Stress Test**: Set capacity to 1MW (approx 2000 modules) and verify smooth rotation.
- **Visuals**: Ensure no geometry artifacts (z-fighting) occur from merging.

# Phase 11: Ultra-Realistic Details (Visuals)

## Goal
Push the visual fidelity to the maximum possible within a web-based Plotly environment.

## Proposed Changes
### `src/design.py`
#### [NEW] `generate_racking_geometry`
-   **Piles**: Vertical cylinders (hexagonal prisms for performance) spaced every ~4m along the row.
-   **Torque Tube**: A long horizontal cylinder/box running the length of the row.
-   **Batching**: All piles and tubes will be merged into a single `Global_Structure` trace (Dark Grey Metal).

#### [NEW] `generate_vegetation`
-   **Trees**: Simple "Lollipop" or "Cone" trees placed randomly around the perimeter fence.
-   **Trace**: `Global_Vegetation` (Green).

#### [UPDATE] `visualize_layout_3d`
-   Integrate the new geometry generators.
-   **Lighting Tuning**:
    -   **Panels**: High `specular` (1.5), Low `roughness` (0.1) for glass reflection.
    -   **Ground**: Low `specular`, High `roughness` (matte).
    -   **Structure**: Medium `specular` (metallic).

# Phase 12: Ultimate Optimization & Utility (Final Polish) [COMPLETED]

## Goal
Achieve the theoretical maximum rendering performance and add critical engineering utilities.

## Proposed Changes
### `src/design.py`
#### [OPTIMIZE] `visualize_layout_3d`
-   **Face Coloring**: Currently, we use 2 traces (Frame, Cells) to get 2 colors.
    -   *New Approach*: Use a single `Mesh3d` trace. Construct a `facecolor` array.
    -   Assign "Silver" to frame faces and "Blue" to cell faces.
    -   **Benefit**: Halves the overhead of the heaviest part of the scene.

#### [NEW] Terrain & Structure Logic
-   **Sloped Ground**:
    -   Input: `slope_ns` (degrees), `slope_ew` (degrees).
    -   Calculate `z_ground(x, y)` based on slope plane.
    -   **Smart Piles**: Calculate pile top (fixed by array plane) and pile bottom (ground plane). Pile length = `z_array - z_ground`.
    -   This visualizes **Civils/Grading** requirements implicitly.

#### [NEW] eBOS Visualization
-   **Cable Trays**: A mesh running along the N-S axis (perpendicular to rows) to collect cables.
-   **Combiner Boxes**: Small boxes placed at the end of strings/rows.
-   **Trace**: `Global_eBOS` (Orange/Grey).
# Phase 13: Advanced Physics & Persistence [COMPLETED]

## Goal
Add final advanced engineering features and ensure project data can be saved/loaded.

## Proposed Changes
### `src/solar_model.py`
#### [UPDATE] `SolarSystem`
-   Add `bifaciality_factor` (default 0.7 for bifacial, 0.0 for monofacial).
-   Add `albedo` (ground reflection).
-   Update `calculate_generation` to estimate rear-side irradiance:
    -   `G_rear = G_ghi * albedo * (1 - shading_factor)`
    -   `P_rear = P_front * bifaciality_factor * (G_rear / 1000)`
    -   `P_total = P_front + P_rear`

### `app.py`
#### [NEW] Sidebar Persistence
-   **Save**: Button to download `project_state.pkl`.
-   **Load**: File uploader to restore state from `project_state.pkl`.
-   Use `st.session_state` to manage the full state dict.

### `README.md`
-   Rewrite to list all 13 phases and features.
-   Add screenshots (placeholders).

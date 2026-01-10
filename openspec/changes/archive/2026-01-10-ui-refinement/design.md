# UI Design Analysis: Svelte + Cesium vs. Alternatives

## Option A: Current Plan (Svelte + Cesium)
*   **Structure**: Svelte manages the application shell, navigation, and "static" pages (charts, tables). Cesium is loaded as a component on the "Map" page.
*   **Pros**: 
    *   Best-in-class 3D visualization (looks very impressive to VPs).
    *   Clear separation of concerns (Text vs. Map).
*   **Cons**:
    *   Cesium is heavy.
    *   State synchronization (e.g., clicking a flight in the table to focus it on the map) requires careful event bus management.

## Option B: Leaflet/Mapbox (Lightweight 2D)
*   **Structure**: Same as A, but using a lighter 2D map library.
*   **Pros**: Fast to build, mobile-friendly, familiar API.
*   **Cons**: Lacks the "Wow" factor of 3D globes for an executive demo.

## Option C: Simplified "Map-First" (Recommended)
*   **Structure**: The entire app is the Map. Svelte provides floating "HUD" panels for the data (Fleet Stats, Arrivals).
*   **Logic**:
    *   No separate "pages".
    *   The map *is* the application.
    *   "Static" displays become overlaid widgets.
*   **Why this simplifies**:
    *   Reduces state management (everything is "on the map").
    *   Eliminates context switching for the user.
    *   Makes the demo feel more immersive.

## Decision Record
We will proceed with **Option C (Map-First)** but keep Cesium (Phase 5) as the engine for the "Wow" factor, while strictly limiting Svelte's role to just the floating HUD overlays. This avoids the complexity of building a complex multi-page app.

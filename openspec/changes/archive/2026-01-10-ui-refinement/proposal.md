# UI Architecture Refinement

## Why
We need to validate if the proposed UI architecture (Svelte for static data + CesiumJS for the map) is the most efficient approach or if it introduces unnecessary complexity for a demo.

## What Changes
This proposal creates a design document to analyze the trade-offs of the current UI plan vs. simplified alternatives.

## Open Questions & Risks
1.  **Complexity Overhead**: Is maintaining two distinct visualization paradigms (Svelte DOM for stats vs. WebGL/Cesium for maps) too heavy for a demo?
    *   *Risk*: Development time doubles; synchronization between the "static" list and the "3D" map can be buggy.
2.  **Cesium "Overkill"**: Cesium is a heavy library (tens of MBs) designed for high-fidelity geospatial work.
    *   *Question*: Do we really need 3D terrain/buildings, or would a lightweight 2D library like Leaflet or Mapbox GL JS suffice?
3.  **Unified vs. Split**: Should the map be the *only* view?
    *   *Idea*: Instead of separate "static displays" and "map displays", overlay the stats (counts, alerts) directly on the map HUD (Head-Up Display) within the Cesium/Map view.
4.  **Svelte Integration**: Svelte is excellent for DOM manipulation, but Cesium takes over the DOM rendering canvas.
    *   *Question*: Will we fight the framework? (e.g., Svelte components drifting out of sync with Cesium entities).

## Recommendation
Consider simplifying to a **"Map-First" Dashboard**:
*   Use a single Svelte app where the Map is the background.
*   Overlay "cards" for the stats (Fleet Counts, Airport Arrivals) using absolute positioning.
*   This removes the need for separate "pages" or rigid layouts.

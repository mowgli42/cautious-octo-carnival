# Delta for UI Refinement

## MODIFIED Requirements

### Requirement: Svelte Dashboard
The user interface SHALL be a single-page "Map-First" application.

#### Scenario: Unified View
- WHEN the user loads the dashboard
- THEN they must see the 3D Map (Cesium) filling the background
- AND statistical data (Fleet Counts, Arrivals) must be presented as floating HUD overlays on top of the map
- AND there must be no separate navigation pages (single view experience)

## REMOVED Requirements
### Requirement: Cesium Visualization (Future)
(Merged into the main dashboard requirement above; no longer a separate future phase, but the core visualization engine).

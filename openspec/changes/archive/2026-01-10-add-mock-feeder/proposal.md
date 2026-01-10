# Add Mock Feeder

## Why
Live API feeds (like OpenSky) can be rate-limited or unreliable during critical demos. A deterministic "Mock Mode" ensures the demo always works perfectly for executives.

## What Changes
*   Add a configurable "Mock Mode" to the `adsb-feeder`.
*   The mock mode will replay a 20-minute loop of specific airlines (Delta, United, Southwest, Qantas, Emirates).

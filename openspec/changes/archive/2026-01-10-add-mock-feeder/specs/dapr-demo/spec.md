# Delta for Dapr Demo

## ADDED Requirements

### Requirement: Mock Feeder Mode
The `adsb-feeder` service SHALL support a configurable "Mock Mode" that generates synthetic flight data instead of connecting to the live API.

#### Scenario: Mock Data Generation
- WHEN the service is started with `MOCK_MODE=true`
- THEN it must ignore external API credentials
- AND it must generate flight update events for a predefined set of airlines

#### Scenario: Specific Airlines
- WHEN in Mock Mode
- THEN the generated flights must include aircraft from: Delta, United, Southwest, Qantas, and Emirates

#### Scenario: Playback Loop
- WHEN in Mock Mode
- THEN the flight data must follow a deterministic 20-minute loop
- AND the loop must repeat indefinitely without interruption

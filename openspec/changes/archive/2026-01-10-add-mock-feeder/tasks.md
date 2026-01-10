# Tasks for Mock Feeder

## 1. Feeder Service Update
- [ ] 1.1 Add `MOCK_MODE` environment variable support to `adsb-feeder`
- [ ] 1.2 Create `MockFlightGenerator` class to simulate ADS-B frames
- [ ] 1.3 Implement 20-minute flight path scenarios for required airlines (Delta, United, Southwest, Qantas, Emirates)
- [ ] 1.4 Ensure mock data matches the exact JSON schema of the live OpenSky data (so subscribers can't tell the difference)

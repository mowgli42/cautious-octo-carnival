# AGENTS.md - guide for AI coding agents

## Project context

cautious-octo-carnival is a Dapr demo stack with Go, Node, and Python services.
Read `README.md` and the relevant service directory before changing behavior.

## Local setup

Run from the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r services/flight-archiver/requirements.txt -r services/emergency-alert/requirements.txt -r services/fleet-stats/requirements.txt
(cd services/flight-dashboard && npm install)
(cd services/adsb-feeder && npm install)
(command -v go >/dev/null && cd services/airport-tracker && go mod download || true)
```

## Smoke test

```bash
.venv/bin/python -m compileall services/flight-archiver services/emergency-alert services/fleet-stats -q
node --check services/flight-dashboard/index.js
node --check services/adsb-feeder/index.js
(command -v go >/dev/null && cd services/airport-tracker && go build -o /dev/null . || true)
```

## Agent notes

- Keep service-specific changes inside the owning `services/<name>/` directory when possible.
- The full stack expects container/Dapr infrastructure; document which subset you tested.
- Preserve existing local user changes; stage only files you intentionally modify.

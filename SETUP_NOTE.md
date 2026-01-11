# Setup Note

## Running with Docker Compose

**Note:** Docker Compose setup with Dapr sidecars is complex. For learning and development, we recommend using the Dapr CLI locally first.

### Recommended: Local Development with Dapr CLI

See `GETTING_STARTED.md` for instructions on running services locally with Dapr CLI. This approach:
- Is simpler to understand
- Allows you to see Dapr sidecars running separately
- Makes debugging easier
- Better demonstrates the sidecar pattern

### Docker Compose Setup

The Docker Compose file is provided for convenience, but you'll need to:
1. Install Dapr CLI: https://docs.dapr.io/getting-started/install-dapr-cli/
2. Run `dapr init` locally first (this sets up required components)
3. Or manually configure Dapr sidecars in the compose file

For production deployments, consider using Kubernetes which has better Dapr integration.

## Next Steps

1. Start with local development using Dapr CLI (see GETTING_STARTED.md)
2. Once you understand how it works, we can refine the Docker Compose setup
3. The services are designed to work the same way in both environments


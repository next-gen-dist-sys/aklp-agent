# Skaffold Development Workflow

This document describes how to use Skaffold for local development with k3d.

## Prerequisites

1. **k3d** - Kubernetes in Docker
```bash
# Install k3d
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash

# Create a cluster
k3d cluster create aklp-dev --servers 1 --agents 2 -p "30001-30003:30001-30003@server:0"
```

2. **skaffold** - Development workflow tool
```bash
# Install skaffold
curl -Lo skaffold https://storage.googleapis.com/skaffold/releases/latest/skaffold-linux-amd64
sudo install skaffold /usr/local/bin/
```

3. **kubectl** - Kubernetes CLI
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

## Quick Start

### Development Mode

Run the service with auto-reload on file changes:

```bash
# Start development with auto-reload
skaffold dev

# Or with cleanup on exit
skaffold dev --cleanup=true

# With specific profile
skaffold dev --profile=dev
```

This will:
- Build Docker image
- Deploy to k3d cluster
- Watch for file changes
- Automatically rebuild and redeploy
- Stream logs to console

### Run Mode

Deploy once without watching:

```bash
# Deploy to cluster
skaffold run

# Deploy with specific profile
skaffold run --profile=prod

# Delete deployment
skaffold delete
```

### Debug Mode

Run with debug settings:

```bash
skaffold debug
```

## Skaffold Profiles

### default
- Local development with k3d
- No image push (uses local docker)
- File sync enabled for Python files

### dev
- Development profile
- DEBUG mode enabled
- Hot reload for Python files

### prod
- Production-ready build
- Pushes image to registry
- Optimized settings

### debug
- Debug mode with detailed logging
- File sync enabled
- Port forwarding

## File Sync

Skaffold can sync Python files without rebuilding:

```yaml
sync:
  manual:
    - src: "app/**/*.py"
      dest: /app/app
```

This means changes to `.py` files will be synced instantly without image rebuild.

## Port Forwarding

Skaffold automatically forwards ports:

```yaml
portForward:
  - resourceType: service
    resourceName: service-template
    port: 8000
    localPort: 8000
```

Access the service at: `http://localhost:8000`

## Configuration

### Update Image Repository

Edit `skaffold.yaml`:

```yaml
build:
  artifacts:
    - image: ghcr.io/YOUR_USERNAME/service-template  # Update this
```

### Update k3d Cluster

Ensure k3d cluster is created with correct port mappings:

```bash
k3d cluster create aklp-dev \
  --servers 1 \
  --agents 2 \
  -p "30001-30003:30001-30003@server:0"
```

This maps NodePorts 30001-30003 to localhost.

## Common Commands

```bash
# Check skaffold version
skaffold version

# Validate configuration
skaffold diagnose

# Build images only
skaffold build

# Render manifests (dry-run)
skaffold render

# View effective config
skaffold config list
```

## Workflow Example

1. **Start k3d cluster**
```bash
k3d cluster create aklp-dev --servers 1 --agents 2 -p "30001-30003:30001-30003@server:0"
```

2. **Start development**
```bash
cd service-template
skaffold dev
```

3. **Edit code**
- Edit Python files in `app/`
- Changes are automatically synced
- Watch logs in terminal

4. **Test changes**
```bash
# In another terminal
curl http://localhost:8000/health

# Or access via NodePort
curl http://localhost:30000/health
```

5. **Stop development**
- Press `Ctrl+C`
- Resources are automatically cleaned up

## Troubleshooting

### Image not found

```bash
# Check if image is built
docker images | grep service-template

# Manually build
skaffold build
```

### Port conflict

```bash
# Check what's using the port
sudo lsof -i :8000

# Change port in skaffold.yaml portForward section
```

### Cluster not accessible

```bash
# Check cluster
k3d cluster list
kubectl cluster-info

# Restart cluster
k3d cluster stop aklp-dev
k3d cluster start aklp-dev
```

### File sync not working

- Ensure file paths in `sync` match actual structure
- Check Skaffold version (file sync requires v1.20+)
- Try full rebuild: `skaffold dev --no-prune=false --cache-artifacts=false`

## Best Practices

1. **Use profiles** for different environments
2. **Enable file sync** for faster iteration
3. **Use port forwarding** for easy local access
4. **Run with cleanup** to avoid resource leaks
5. **Check logs** regularly for errors

## Integration with AKLP

For the complete AKLP platform:

1. Deploy PostgreSQL StatefulSet first
2. Run each service (note, task, agent) with Skaffold
3. Use different NodePorts (30001, 30002, 30003)
4. TUI client connects to NodePorts

### Multi-service Development

Create a root `skaffold.yaml` to manage all services:

```yaml
# Root skaffold.yaml
apiVersion: skaffold/v4beta11
kind: Config
requires:
  - path: service-template
    configs: [service-template]
  - path: aklp-note
    configs: [aklp-note]
  - path: aklp-task
    configs: [aklp-task]
  - path: aklp-agent
    configs: [aklp-agent]
```

Then run all services:

```bash
skaffold dev
```
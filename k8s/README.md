# Kubernetes Manifests

Kubernetes deployment manifests for the service-template.

## Files

- **deployment.yaml**: Deployment configuration with 2 replicas
- **service.yaml**: NodePort service for external access
- **configmap.yaml**: Configuration environment variables
- **kustomization.yaml**: Kustomize configuration for managing manifests

## Deployment

### Using kubectl

```bash
# Apply all manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get deployments
kubectl get pods
kubectl get services

# View logs
kubectl logs -l app=service-template -f

# Delete resources
kubectl delete -f k8s/
```

### Using kustomize

```bash
# Build and preview
kubectl kustomize k8s/

# Apply with kustomize
kubectl apply -k k8s/

# Delete with kustomize
kubectl delete -k k8s/
```

## Configuration

### Environment Variables

All environment variables are defined in `configmap.yaml`:

- `APP_NAME`: Application name
- `DEBUG`: Debug mode (true/false)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FORMAT`: Log format (json, text)
- `DATABASE_URL`: PostgreSQL connection string

### Resource Limits

Defined in `deployment.yaml`:

- **Requests**: 100m CPU, 128Mi memory
- **Limits**: 500m CPU, 512Mi memory

Adjust based on actual usage and cluster capacity.

### NodePort

The service uses NodePort type with port 30000 (default in template).

For actual services:

- **aklp-note**: NodePort 30001
- **aklp-task**: NodePort 30002
- **aklp-agent**: NodePort 30003

Update `service.yaml` accordingly.

## Health Checks

- **Liveness Probe**: GET /health (initial delay: 30s, period: 10s)
- **Readiness Probe**: GET /health (initial delay: 10s, period: 5s)

## Customization for Each Service

When creating manifests for actual services (aklp-note, aklp-task, aklp-agent):

1. **Update names**: Replace `service-template` with service name (e.g., `aklp-note`)
2. **Update image**: Change image repository and tag
3. **Update NodePort**: Set correct port (30001, 30002, 30003)
4. **Update DATABASE_URL**: Set correct database name (aklp_note, aklp_task, aklp_agent)
5. **Update labels**: Add service-specific labels if needed

### Example for aklp-note

```bash
# In deployment.yaml
name: aklp-note
labels:
  app: aklp-note

# In service.yaml
nodePort: 30001

# In configmap.yaml
APP_NAME: "aklp-note"
DATABASE_URL: "postgresql+asyncpg://postgres:postgres@postgres:5432/aklp_note"
```

## Scaling

Scale deployment:

```bash
kubectl scale deployment service-template --replicas=3
```

Or update `replicas` in `deployment.yaml` and reapply.

## Troubleshooting

View deployment events:

```bash
kubectl describe deployment service-template
```

View pod logs:

```bash
kubectl logs -l app=service-template --tail=100
```

Get pod details:

```bash
kubectl describe pod <pod-name>
```

Check service endpoints:

```bash
kubectl get endpoints service-template
```
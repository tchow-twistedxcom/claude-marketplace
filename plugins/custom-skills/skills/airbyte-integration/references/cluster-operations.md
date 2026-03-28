# Airbyte Cluster Operations

Airbyte runs in a kind Kubernetes cluster (`airbyte-abctl`) inside Docker container `airbyte-abctl-control-plane` on twistedx-docker (100.117.161.21).

## Command Prefixes

```bash
# From local machine (via Tailscale):
ssh 100.117.161.21 "docker exec airbyte-abctl-control-plane kubectl <cmd> -n airbyte-abctl"

# From twistedx-docker directly:
docker exec airbyte-abctl-control-plane kubectl <cmd> -n airbyte-abctl

# When kube-apiserver is down — use crictl directly in kind container:
docker exec airbyte-abctl-control-plane crictl ps | grep <name>
docker exec airbyte-abctl-control-plane crictl logs <container-id>
```

## Pod Status Quick Check

```bash
# All Airbyte pods
docker exec airbyte-abctl-control-plane kubectl get pods -n airbyte-abctl

# Just replication pods (active syncs)
docker exec airbyte-abctl-control-plane kubectl get pods -n airbyte-abctl | grep replication

# Resource usage
docker exec airbyte-abctl-control-plane kubectl top pods -n airbyte-abctl
```

## Restart Deployments

```bash
# After ConfigMap change (ALWAYS restart server; ConfigMap vars baked in at startup)
docker exec airbyte-abctl-control-plane kubectl rollout restart deployment/airbyte-abctl-server -n airbyte-abctl

# All control plane components
for DEPLOY in airbyte-abctl-server airbyte-abctl-workload-api-server airbyte-abctl-workload-launcher; do
  docker exec airbyte-abctl-control-plane kubectl rollout restart deployment/$DEPLOY -n airbyte-abctl
done

# Wait for ready
docker exec airbyte-abctl-control-plane kubectl rollout status deployment/airbyte-abctl-server -n airbyte-abctl
```

## Memory Limit Patches

**Current recommended limits (40Gi host, kind cluster):**

```bash
# Server: 4Gi (JVM -Xmx1200m + overhead > 2Gi under load)
docker exec airbyte-abctl-control-plane kubectl patch deployment -n airbyte-abctl airbyte-abctl-server --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/resources","value":{"requests":{"memory":"1Gi","cpu":"100m"},"limits":{"memory":"4Gi","cpu":"2"}}}]'

# Workload API Server: 2Gi
docker exec airbyte-abctl-control-plane kubectl patch deployment -n airbyte-abctl airbyte-abctl-workload-api-server --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/resources","value":{"requests":{"memory":"512Mi","cpu":"100m"},"limits":{"memory":"2Gi","cpu":"1"}}}]'

# Workload Launcher: 2Gi
docker exec airbyte-abctl-control-plane kubectl patch deployment -n airbyte-abctl airbyte-abctl-workload-launcher --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/resources","value":{"requests":{"memory":"512Mi","cpu":"100m"},"limits":{"memory":"2Gi","cpu":"1"}}}]'
```

> ⚠️ These patches are NOT persisted across `abctl local install` re-installs. Re-apply after upgrades.

## Liveness Probe Patches (JVM apps need generous thresholds)

```bash
# Apply to all three deployments — JVM GC pauses can cause health check latency spikes
for DEPLOY in airbyte-abctl-server airbyte-abctl-workload-api-server airbyte-abctl-workload-launcher; do
  docker exec airbyte-abctl-control-plane kubectl patch deployment -n airbyte-abctl $DEPLOY --type=json \
    -p '[
      {"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/failureThreshold","value":10},
      {"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/timeoutSeconds","value":30},
      {"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/failureThreshold","value":10},
      {"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/timeoutSeconds","value":30}
    ]'
done
```

**Default `failureThreshold: 3` × `periodSeconds: 10` = 30s total before kill — too tight for JVM startup (2+ min).**

## kube-apiserver Probe (static pod manifest)

```bash
# Increase from failureThreshold: 8 to 24 to survive thundering-herd reconnection storms
docker exec airbyte-abctl-control-plane sed -i \
  's/failureThreshold: 8/failureThreshold: 24/g' \
  /etc/kubernetes/manifests/kube-apiserver.yaml
# kubelet auto-restarts apiserver; this change persists across pod restarts (static pod manifest)
```

## ConfigMap: Job Container Resource Limits

```bash
# View current ConfigMap
docker exec airbyte-abctl-control-plane kubectl get configmap -n airbyte-abctl airbyte-abctl-airbyte-env -o yaml

# Edit ConfigMap (then RESTART SERVER for changes to take effect)
docker exec airbyte-abctl-control-plane kubectl edit configmap -n airbyte-abctl airbyte-abctl-airbyte-env
```

**Key ConfigMap values:**
```yaml
JOB_MAIN_CONTAINER_MEMORY_LIMIT: "8Gi"    # Source/destination container limit
JOB_MAIN_CONTAINER_MEMORY_REQUEST: "2Gi"
REPLICATION_ORCHESTRATOR_MEMORY_LIMIT: "4Gi"
REPLICATION_ORCHESTRATOR_MEMORY_REQUEST: "2Gi"
CONNECTOR_SPECIFIC_RESOURCE_DEFAULTS_ENABLED: "false"
```

> **CRITICAL**: ConfigMap changes require server pod restart. Server bakes `JOB_MAIN_CONTAINER_MEMORY_LIMIT` into each job's `SyncResourceRequirements` at creation time. Workload-launcher reads those baked values — NOT its own env vars.

**Verify server picked up new limits:**
```bash
docker exec airbyte-abctl-control-plane kubectl exec -n airbyte-abctl <server-pod> -- \
  env | grep JOB_MAIN_CONTAINER_MEMORY
```

## Replication Pod Management

```bash
# Check QoS class (should be Burstable, not BestEffort)
docker exec airbyte-abctl-control-plane kubectl get pod replication-job-<N>-attempt-0 \
  -n airbyte-abctl -o jsonpath='{.status.qosClass}'

# Check resource limits on replication pod containers
docker exec airbyte-abctl-control-plane kubectl get pod replication-job-<N>-attempt-0 \
  -n airbyte-abctl -o jsonpath='{.spec.containers[*].resources}'
# Expected: {"limits":{"cpu":"1","memory":"8Gi"},"requests":{"cpu":"...","memory":"2Gi"}} × 3

# Force-delete stale replication pods (unblocks workload-launcher MUTEX stage)
docker exec airbyte-abctl-control-plane kubectl delete pod \
  -n airbyte-abctl replication-job-<N>-attempt-0 --force
```

**Pod name format**: `replication-job-{job_id}-attempt-{attempt_number}`

## Load Custom Docker Image into Kind Cluster

```bash
# Build image
docker build -t airbyte/source-amazon-seller-partner:5.6.0-vc-fix5 /tmp/

# Load into KIND containerd (NOT host containerd — kind has its OWN containerd instance)
docker save airbyte/source-amazon-seller-partner:5.6.0-vc-fix5 | \
  docker exec -i airbyte-abctl-control-plane ctr -n k8s.io images import -

# Verify image available in kind cluster
docker exec airbyte-abctl-control-plane ctr -n k8s.io images ls | grep vc-fix
```

## Logs

```bash
# Server logs
docker exec airbyte-abctl-control-plane kubectl logs -n airbyte-abctl \
  deployment/airbyte-abctl-server --tail=100

# Workload launcher logs
docker exec airbyte-abctl-control-plane kubectl logs -n airbyte-abctl \
  deployment/airbyte-abctl-workload-launcher --tail=100

# Replication pod logs (all containers)
docker exec airbyte-abctl-control-plane kubectl logs \
  -n airbyte-abctl --selector=airbyte=replication \
  --all-containers=true --tail=300

# Specific replication pod
docker exec airbyte-abctl-control-plane kubectl logs \
  -n airbyte-abctl replication-job-<N>-attempt-0 -c orchestrator --tail=200
```

## Diagnosing When kubectl Fails

When kube-apiserver is down (connection refused / etcdserver timeout):
```bash
# Use crictl directly inside kind container
docker exec airbyte-abctl-control-plane crictl ps | grep kube-apiserver
docker exec airbyte-abctl-control-plane crictl logs <container-id>

# Check apiserver restart count
docker exec airbyte-abctl-control-plane crictl ps | grep apiserver
# Look at ATTEMPTS column — 30+ means thundering-herd storm
```

## abctl CLI

```bash
# Get admin credentials (email, password, client_id, client_secret)
ssh 100.117.161.21 "abctl local credentials"

# Check Airbyte deployment status
ssh 100.117.161.21 "abctl local status"

# Reinstall (preserves data volumes; re-apply all kubectl patches afterward)
ssh 100.117.161.21 "abctl local install"
```

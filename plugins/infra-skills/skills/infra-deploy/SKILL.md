---
name: infra-deploy
description: Deploy and manage Docker stacks/containers on the tchow homelab infrastructure. Use when the user wants to deploy a new service, update a stack, start/stop/restart containers, manage docker-compose stacks via Portainer, or perform infrastructure changes on twistedx-docker or twistedx-dockerprod. Covers stack creation, container lifecycle, and rollout verification.
---

# Infra Deploy

## Overview

Deploy and manage Docker stacks across the homelab. Uses Portainer MCP for container/stack management and Tailscale SSH for direct server access on Linux hosts.

## Environments

| Name | Host | Use For |
|------|------|---------|
| Docker-SSC | twistedx-docker | Dev/staging workloads |
| Docker-DMC | twistedx-docker (secondary) | Secondary services |
| Docker-PROD | twistedx-dockerprod | Production workloads |

Get current environment IDs: use Portainer MCP `listEnvironments`.

## Container Lifecycle (Portainer MCP)

Use Portainer MCP `dockerProxy` for Docker API calls:

```
POST /containers/{id}/start
POST /containers/{id}/stop
POST /containers/{id}/restart
GET  /containers/json?all=1         # List all containers
GET  /containers/{id}/json          # Container detail
```

Or use the dashboard at `http://100.90.23.64:3060/containers` for start/stop/restart with confirmation UI.

## Stack Management

### List stacks on an environment
Use Portainer MCP `listStacks` with the environment ID.

### Deploy/update a stack via SSH
```bash
tailscale ssh ntservice@twistedx-docker
cd /path/to/stack
sudo docker compose pull
sudo docker compose up -d --force-recreate
```

### Create a new stack via Portainer
Use Portainer MCP `createStack` with:
- `name`: stack name
- `stackFileContent`: docker-compose YAML content
- `environmentId`: target environment ID

## Deployment Workflow

1. **Identify target environment** — dev (Docker-SSC) or prod (Docker-PROD)
2. **For production changes** — always confirm with user before executing
3. **Deploy** — via Portainer MCP stack tools or `tailscale ssh` + docker compose
4. **Verify** — check container state via Portainer MCP or dashboard
5. **Monitor** — check NinjaOne alerts at `http://localhost:3050/api/alerts` for post-deploy issues

## SSH Access (Linux hosts only)

```bash
tailscale ssh ntservice@twistedx-docker      # Dev host
tailscale ssh ntservice@twistedx-dockerprod  # Prod host
```

Note: `ntservice` has sudo with password. Ask user for sudo password if needed for privileged operations.

## Safety Rules

- **Always ask before prod changes** — tag:production servers require explicit user confirmation
- **Prefer dashboard actions** for container start/stop/restart (built-in confirmation dialogs)
- **Check health after deploy** — run `infra-health` check or view dashboard after any deployment

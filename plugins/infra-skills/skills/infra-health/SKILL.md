---
name: infra-health
description: Infrastructure health check and monitoring for the tchow homelab. Use when the user asks about server status, container health, active alerts, infrastructure overview, or wants to know if anything is down/offline. Covers: Tailscale network devices, NinjaOne alerts, Portainer containers across Docker-SSC/Docker-DMC/Docker-PROD environments. Dashboard available at http://100.90.23.64:3060.
---

# Infra Health

## Overview

Check infrastructure health across Tailscale servers, NinjaOne alerts, and Portainer containers. Use the dashboard for visual monitoring, or run the CLI script for a quick terminal report.

## Quick Health Check

Run the bundled script for a terminal overview:

```bash
python3 ~/.claude/plugins/marketplaces/tchow-essentials/plugins/infra-skills/skills/infra-health/scripts/health_check.py
```

Options:
- `--servers` — Tailscale devices only
- `--alerts` — NinjaOne alerts only
- `--containers` — Portainer containers only

## Data Sources

| Source | Access | Data |
|--------|--------|------|
| **Tailscale** | `tailscale status --json` | Device inventory, online/offline, OS |
| **NinjaOne** | `GET http://localhost:3050/api/alerts` | Active alerts by severity |
| **Portainer** | Portainer MCP tools | Container state across all environments |
| **Dashboard** | `http://100.90.23.64:3060` | Unified visual view, auto-refreshes every 60s |

## NinjaOne API (port 3050)

The NinjaOne shared API runs on `localhost:3050`:

```
GET /api/devices                    # All devices with health
GET /api/devices/{id}               # Device detail
GET /api/devices/{id}/health        # CPU/memory/disk
GET /api/alerts                     # Active alerts
POST /api/alerts/{uid}/reset        # Acknowledge alert
GET /api/queries/device-health      # Fleet health report
GET /api/queries/disk-drives        # Disk inventory
GET /api/queries/os-patches         # Patch compliance
```

## Portainer MCP

Use Portainer MCP tools for container operations. Three environments:
- **Docker-SSC** (env ID 2) — twistedx-docker dev host
- **Docker-DMC** (env ID 3) — secondary host
- **Docker-PROD** (env ID ?) — twistedx-dockerprod production host

Use `listEnvironments` to confirm current environment IDs.

## Server Inventory

7 Linux + 5 Windows servers on Tailscale. Key hosts:
- `twistedx-docker` — dev Docker host (Portainer BE, dashboard)
- `twistedx-dockerprod` — production Docker host
- SSH access: `tailscale ssh ntservice@<hostname>` (Linux only, sudo with password)

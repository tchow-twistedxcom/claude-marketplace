---
name: infra-maintenance
description: Infrastructure maintenance for the tchow homelab. Use when the user wants to: check disk usage across servers, review patch compliance, run OS updates, clean up Docker resources, verify Veeam backups, or perform any routine maintenance task. Also use when asked about "disk space", "pending patches", "OS updates", "cleanup", or "backup status".
---

# Infra Maintenance

## Overview

Routine maintenance across Linux servers (via Tailscale SSH) and all monitored devices (via NinjaOne API). Windows servers are managed via NinjaOne only (no SSH).

## Disk Usage Check

```bash
python3 ~/.claude/plugins/marketplaces/tchow-essentials/plugins/infra-skills/skills/infra-maintenance/scripts/disk_report.py
python3 <path>/disk_report.py --threshold 85   # Custom warn threshold
python3 <path>/disk_report.py --critical        # >=90% only
```

Or via NinjaOne API directly:
```
GET http://localhost:3050/api/queries/disk-drives
```

## Patch Compliance

```bash
python3 <path>/patch_report.py                  # All pending patches
python3 <path>/patch_report.py --critical       # Critical/Important only
```

Or via API:
```
GET http://localhost:3050/api/queries/os-patches
```

## Linux Server Maintenance (SSH)

SSH access: `tailscale ssh ntservice@<hostname>` (sudo with password)

**OS updates:**
```bash
sudo apt update && sudo apt upgrade -y          # Ubuntu/Debian
sudo apt autoremove -y && sudo apt clean
```

**Docker cleanup:**
```bash
sudo docker system prune -f                     # Remove stopped containers, unused images
sudo docker volume prune -f                     # Remove unused volumes
sudo docker image prune -a -f                   # Remove all unused images
```

**Disk cleanup:**
```bash
sudo journalctl --vacuum-size=500M              # Trim systemd journal
sudo find /tmp -mtime +7 -delete               # Clear old tmp files
du -sh /* 2>/dev/null | sort -rh | head -20    # Find large directories
```

## Linux Servers

| Hostname | OS | Notes |
|----------|----|-------|
| twistedx-docker | Linux | Dev Docker host |
| twistedx-dockerprod | Linux | Prod Docker host |
| storage | Linux | NAS/storage |
| TWX-SFTPGO | Linux | SFTP server |

## Windows Servers

Windows maintenance is managed through NinjaOne policies (no direct SSH). For patch deployment, advise user to trigger via NinjaOne dashboard or create a NinjaOne maintenance window.

## Backup Verification

Veeam backups run on Windows servers. Check backup status via NinjaOne device health:
```
GET http://localhost:3050/api/devices/{id}/health
```

Look for `backupStatus` field or check NinjaOne alerts for backup failure alerts.

## Safety Rules

- Always `sudo apt upgrade -y` not `dist-upgrade` unless explicitly requested
- `docker system prune -a` removes ALL unused images — confirm with user before running on prod
- Never delete files in application directories without inspecting them first

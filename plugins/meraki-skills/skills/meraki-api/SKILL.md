---
name: meraki-api
description: |
  Cisco Meraki Dashboard API integration for network monitoring and management.

  Activates when user mentions:
  - Meraki, Cisco Meraki, Meraki Dashboard
  - MX appliance, MS switch, MR wireless, MV camera
  - Meraki network, Meraki device, Meraki organization
  - Network monitoring, wireless SSID management
  - Switch port configuration, firewall rules
  - VPN configuration, VLAN management
  - Client tracking, network events
---

# Meraki API Skill

Execute Cisco Meraki Dashboard API operations via Python CLI for network monitoring and management.

## Quick Reference

```bash
# Organization Operations
python meraki_api.py organizations list
python meraki_api.py organizations get --org-id ORG_ID
python meraki_api.py organizations inventory --org-id ORG_ID [--used-state used|unused] [--search MODEL]
python meraki_api.py organizations uplinks --org-id ORG_ID
python meraki_api.py organizations license --org-id ORG_ID

# Network Operations
python meraki_api.py networks list --org-id ORG_ID [--tags tag1,tag2]
python meraki_api.py networks get --network-id NET_ID
python meraki_api.py networks devices --network-id NET_ID
python meraki_api.py networks clients --network-id NET_ID [--timespan 86400]
python meraki_api.py networks alerts --network-id NET_ID
python meraki_api.py networks events --network-id NET_ID [--product-type wireless] [--timespan 7200]
python meraki_api.py networks health --network-id NET_ID
python meraki_api.py networks traffic --network-id NET_ID [--timespan 86400]

# Device Operations
python meraki_api.py devices get --serial Q2AB-1234-5678
python meraki_api.py devices uplink --serial Q2AB-1234-5678
python meraki_api.py devices lldp-cdp --serial Q2AB-1234-5678
python meraki_api.py devices clients --serial Q2AB-1234-5678 [--timespan 86400]

# Switch Operations
python meraki_api.py switch ports --serial Q2HP-1234-5678
python meraki_api.py switch port-statuses --serial Q2HP-1234-5678
python meraki_api.py switch routing --serial Q2HP-1234-5678
python meraki_api.py switch dhcp --network-id NET_ID
python meraki_api.py switch vlans --network-id NET_ID

# Wireless Operations
python meraki_api.py wireless ssids --network-id NET_ID
python meraki_api.py wireless status --network-id NET_ID
python meraki_api.py wireless clients --network-id NET_ID [--timespan 3600]
python meraki_api.py wireless channel-utilization --network-id NET_ID [--timespan 3600]
python meraki_api.py wireless health --network-id NET_ID [--timespan 3600]

# MX Appliance Operations
python meraki_api.py appliance vlans --network-id NET_ID
python meraki_api.py appliance firewall --network-id NET_ID
python meraki_api.py appliance uplinks --network-id NET_ID [--timespan 86400]
python meraki_api.py appliance vpn --network-id NET_ID
python meraki_api.py appliance dhcp --network-id NET_ID

# Camera Operations
python meraki_api.py camera snapshot --serial Q2GV-1234-5678
python meraki_api.py camera video-link --serial Q2GV-1234-5678
python meraki_api.py camera analytics --serial Q2GV-1234-5678 [--timespan 3600]
```

## Authentication

Simple API key. Configure in `config/meraki_config.json`:

```json
{
  "api_key": "YOUR_MERAKI_API_KEY",
  "api_url": "https://api.meraki.com/api/v1"
}
```

Or set `MERAKI_API_KEY` environment variable.

Find your API key in Meraki Dashboard → top-right user menu → **API access**.

## Regional API URLs

| Region | URL |
|--------|-----|
| Global (default) | `https://api.meraki.com/api/v1` |
| Europe | `https://api.eu.meraki.com/api/v1` |

## Output Formats

```bash
--format json     # Default: pretty-printed JSON
--format compact  # One line per item
--format count    # Count only
```

## Common Workflows

### Network Health Check
```bash
# List all orgs to get ORG_ID
python meraki_api.py organizations list

# List networks in org
python meraki_api.py networks list --org-id 12345

# Check WAN uplink status for all MX appliances
python meraki_api.py organizations uplinks --org-id 12345

# Check recent events on a network
python meraki_api.py networks events --network-id NET_ID --timespan 3600
```

### Wireless Troubleshooting
```bash
# List SSIDs
python meraki_api.py wireless ssids --network-id NET_ID

# Check failed connections
python meraki_api.py wireless health --network-id NET_ID --timespan 3600

# Check channel utilization
python meraki_api.py wireless channel-utilization --network-id NET_ID
```

### Switch Port Investigation
```bash
# List all ports with config
python meraki_api.py switch ports --serial Q2HP-XXXX-XXXX

# Check live port statuses (speed, PoE, traffic)
python meraki_api.py switch port-statuses --serial Q2HP-XXXX-XXXX
```

### Client Investigation
```bash
# All clients on network (last 24h)
python meraki_api.py networks clients --network-id NET_ID --timespan 86400

# Clients on a specific AP
python meraki_api.py devices clients --serial Q2PD-XXXX-XXXX
```

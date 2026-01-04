# NetSuite Script Deployments Skill

List and analyze script deployments to identify active vs inactive scripts.

## Quick Start

```bash
# List active deployments for inventory items
python3 scripts/list_deployments.py --record-type inventoryitem --active-only --env prod

# List all RESTlet deployments
python3 scripts/list_deployments.py --script-type restlet --env prod
```

**Why this matters:** Editing an inactive script wastes time - always check `--active-only` first!

See [SKILL.md](./SKILL.md) for full documentation.

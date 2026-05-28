# Integration Lifecycle Management (ILM) - Revisions

Celigo's ILM system lets you snapshot, diff, and revert integration state via revision objects
under `/v1/integrations/:id/revisions`.

## Revision Types

| Type | Description |
|---|---|
| `snapshot` | Captures current state as a named point-in-time checkpoint |
| `pull` | Pulls changes from a connected repository or upstream |

## CLI Commands

```bash
# List all revisions for an integration
python3 scripts/celigo_api.py integrations revisions-list <integration_id>

# Get a specific revision
python3 scripts/celigo_api.py integrations revision-get <integration_id> <revision_id>

# View diff (before/after) of a revision
python3 scripts/celigo_api.py integrations revision-diff <integration_id> <revision_id>

# Create a snapshot of current state
python3 scripts/celigo_api.py integrations revision-snapshot <integration_id>
python3 scripts/celigo_api.py integrations revision-snapshot <integration_id> \
  --description "Before Q3 pricing update"

# Pull remote changes
python3 scripts/celigo_api.py integrations revision-pull <integration_id>

# Apply (revert to) a specific revision
python3 scripts/celigo_api.py integrations revision-apply <integration_id> <revision_id>
```

## Workflow: Safe Deployment with Snapshots

```bash
# 1. Snapshot before making changes
python3 scripts/celigo_api.py integrations revision-snapshot <id> \
  --description "Pre-deployment $(date +%Y-%m-%d)"

# 2. List revisions to confirm
python3 scripts/celigo_api.py integrations revisions-list <id>

# 3. Make changes to flows, exports, imports...

# 4. If something breaks, view diff to compare
python3 scripts/celigo_api.py integrations revision-diff <id> <snapshot_rev_id>

# 5. Revert if needed
python3 scripts/celigo_api.py integrations revision-apply <id> <snapshot_rev_id>
```

## Revision Object Fields

| Field | Type | Description |
|---|---|---|
| `_id` | string | Revision ObjectId |
| `type` | string | `snapshot` or `pull` |
| `description` | string | Optional label |
| `_createdByUserId` | string | User who created the revision |
| `createdAt` | ISO 8601 | When the revision was created |
| `lastModified` | ISO 8601 | Last modification timestamp |

## API Endpoints (Reference)

```
GET  /v1/integrations/:id/revisions          - List revisions
GET  /v1/integrations/:id/revisions/:revId   - Get revision
POST /v1/integrations/:id/revisions          - Create revision (snapshot or pull)
GET  /v1/integrations/:id/revisions/:revId/diff  - View diff
PUT  /v1/integrations/:id/revisions/:revId   - Apply revision
```

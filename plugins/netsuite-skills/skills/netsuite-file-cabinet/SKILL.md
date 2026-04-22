---
name: netsuite-file-cabinet
description: Manage files in NetSuite File Cabinet - upload, find, delete, list, compare, and bulk download files. Use this skill when you need to upload scripts to NetSuite, find files by name or pattern, delete files or stale copies, list files in a folder, compare local vs remote file contents, download entire folder trees, or run PCI scans. Triggers include "upload file to NetSuite", "find NetSuite file", "delete NetSuite file", "list files in folder", "download attachments", "backup File Cabinet", "compare file", "PCI scan", or any File Cabinet operations.
---

# NetSuite File Cabinet Management Skill

## Overview

Manage files in the NetSuite File Cabinet via the NetSuite API Gateway. This skill provides tools for uploading, finding, and listing files without needing to access NetSuite directly.

**Authentication is handled automatically** by the NetSuite API Gateway using OAuth 1.0a.

**Use this skill when:**
- Uploading SuiteScript files to NetSuite after local modifications
- Finding files by name or pattern in the File Cabinet
- Listing all files in a specific folder
- Checking file metadata (size, last modified, folder path)

## Prerequisites

**NetSuite API Gateway** — the scripts default to the hosted prod gateway
`https://nsapi.twistedx.tech`. Set `NETSUITE_API_KEY` in your environment so
requests are authenticated. Override to a local Docker gateway only if you
need to (set `NETSUITE_GATEWAY_URL=http://localhost:3001` and run
`cd ~/NetSuiteApiGateway && docker compose up -d`).

Verify gateway is reachable:
```bash
curl https://nsapi.twistedx.tech/health
```

## File Upload

### Upload a File

```bash
# Upload script to production
python3 scripts/upload_file.py --file ./myScript.js --folder-id 137935 --env prod

# Upload with custom name
python3 scripts/upload_file.py --file ./local.js --name "remote.js" --folder-id 137935 --env sb2

# Upload with description
python3 scripts/upload_file.py --file ./script.js --folder-id 137935 --description "IT-12345: Bug fix" --env prod
```

### Options

| Option | Description | Required |
|--------|-------------|----------|
| `--file` | Local file path to upload | Yes |
| `--folder-id` | NetSuite folder internal ID | Yes |
| `--name` | Override filename in NetSuite | No |
| `--description` | File description | No |
| `--account` | Account (default: twistedx) | No |
| `--env` | Environment: prod, sb1, sb2 (default: sb2) | No |

### File Type Detection

File types are auto-detected from extension:

| Extension | NetSuite Type | Encoding |
|-----------|---------------|----------|
| `.js` | JAVASCRIPT | Plain text |
| `.json` | JSON | Plain text |
| `.xml` | XMLDOC | Plain text |
| `.html`, `.htm` | HTMLDOC | Plain text |
| `.css` | STYLESHEET | Plain text |
| `.txt` | PLAINTEXT | Plain text |
| `.csv` | CSV | Plain text |
| `.pdf` | PDF | Base64 |
| `.png` | PNGIMAGE | Base64 |
| `.jpg`, `.jpeg` | JPGIMAGE | Base64 |
| `.gif` | GIFIMAGE | Base64 |
| `.zip` | ZIP | Base64 |

### Important Notes

- Uses `fileCreate` procedure which **overwrites** existing files with the same name
- Text files use plain UTF-8 encoding (NOT base64)
- Binary files (PDF, images, ZIP) use base64 encoding
- Returns file ID on success

### Critical: File Cabinet Uploads Do NOT Trigger Script Recompilation

**Uploading a SuiteScript file via `upload_file.py` (fileCreate) overwrites file content in the File Cabinet, but the NetSuite runtime continues using the cached/compiled version of the script.** Your code changes will NOT take effect until you force recompilation.

**To activate script changes after upload, you MUST do one of:**
1. **Deploy via SDF** (recommended): `npx twx-deploy deploy sb2` — forces full recompilation
2. **Save the script record in the NetSuite UI** — open the script record and click Save

**What does NOT trigger recompilation:**
- File Cabinet upload alone (`fileCreate` API)
- `record.submitFields()` on the script or deployment record via API
- Saving the deployment record (only saves deployment metadata, not script compilation)

**How to verify your code is running:**
- Add a unique log message or response field in your new code
- Check if the response/log includes it after deployment
- If not, the old cached version is still running

## File Search

### Find Files

```bash
# Find file by exact name
python3 scripts/find_file.py --name "inventoryPartUserEvent.js" --env prod

# Find files by pattern (SQL LIKE syntax)
python3 scripts/find_file.py --pattern "twx_edi%" --env prod

# List all files in a folder
python3 scripts/find_file.py --folder-id 137935 --env prod

# Combine search criteria
python3 scripts/find_file.py --pattern "%.js" --folder-id 137935 --env sb2

# Output as JSON
python3 scripts/find_file.py --name "script.js" --format json --env prod
```

### Options

| Option | Description | Required |
|--------|-------------|----------|
| `--name` | Exact file name to search | One of name/pattern/folder-id |
| `--pattern` | SQL LIKE pattern (e.g., "twx_%") | One of name/pattern/folder-id |
| `--folder-id` | List files in specific folder | One of name/pattern/folder-id |
| `--account` | Account (default: twistedx) | No |
| `--env` | Environment: prod, sb1, sb2 (default: sb2) | No |
| `--limit` | Max results (default: 100) | No |
| `--format` | Output: table, json (default: table) | No |

### Output Fields

- `id` - NetSuite file internal ID
- `name` - File name
- `folder` - Folder internal ID
- `folder_name` - Folder display name
- `filesize` - File size in bytes
- `lastmodifieddate` - Last modification timestamp

## File Deletion

Every `--confirm` run **downloads each file to a local trash bin before deleting it**, and writes a restore manifest capturing the original folder ID, name, and metadata. Accidental deletions can be recovered by re-uploading from the trash bin to the folder listed in the manifest.

### Delete a File by ID

```bash
# Dry-run first — safe preview, no downloads, no changes
python3 scripts/delete_file.py --file-id 55342202 --name "stale_script.js" --dry-run --env sb2

# Execute: downloads to ./trash-bin/<timestamp>_<env>/files/ first, then deletes
python3 scripts/delete_file.py --file-id 55342202 --name "stale_script.js" --confirm --env sb2
```

| Option | Description | Required |
|--------|-------------|----------|
| `--file-id` | NetSuite file internal ID | Yes (alt: `--report`) |
| `--report` | Path to scan_report.json (e.g. from `pci_scan.py`) | Yes (alt: `--file-id`) |
| `--dry-run` / `--confirm` | Pick exactly one | Yes |
| `--name` | Name hint for manifest (used with `--file-id`) | Optional |
| `--trash-dir` | Parent trash directory (default: `./trash-bin` in CWD) | No |
| `--force-without-backup` | Delete even if local backup fails (DANGEROUS) | No |
| `--env` | prod, sb1, sb2 (default: production) | No |
| `--account` | NetSuite account (default: twistedx) | No |

### Trash bin layout

A new per-run directory is created on each `--confirm` execution, keyed by timestamp + environment to prevent collisions:

```
./trash-bin/
└── 20260420_193045_sandbox2/
    ├── restore_manifest.json       # folder_id, name, type, size, backup_path per file
    └── files/
        ├── 55342202_twx_CS_CommChannel.js
        └── 55342201_twx_CS_CommPref.js
```

### Restore a deleted file

Use the manifest to re-upload. For each entry in `operations[]`:

```bash
# Read folder_id and name from restore_manifest.json, then:
python3 scripts/upload_file.py \
  --file ./trash-bin/<run_dir>/files/<backup_filename> \
  --folder-id <folder_id_from_manifest> \
  --name "<original_name_from_manifest>" \
  --env <env>
```

### Critical notes

- **Backup is automatic.** On `--confirm`, every file is fetched via `fileGet` and written to the trash bin *before* `fileDelete` runs. If the backup fails, the deletion is skipped by default (safer to retry than to destroy unrecoverable state). Pass `--force-without-backup` only when you genuinely don't care about recovery.
- **`update_record.py` CANNOT delete files.** The gateway's upsert endpoint does not accept `file` as a record type — it returns `INVALID_RCRD_TYPE`. Always use `delete_file.py`.
- **No folder-delete support exists.** To delete an empty File Cabinet folder, ask the user to remove it manually via **Documents → Files → File Cabinet** in the NetSuite UI.
- **Manifest is written incrementally** after every operation, so partial runs (interrupted, network failure, etc.) still produce a usable restore record.
- Add `./trash-bin/` to `.gitignore` in whichever repo you run from — deleted file contents should not be committed.

## Bulk Download

### Download Files from Folder Tree

The unified `download.py` script handles downloading files from any folder or SuiteBundle with automatic strategy detection.

```bash
# Download a SuiteBundle
python3 scripts/download.py --bundle 311735 --output ./backup --env prod

# Download a large attachment folder
python3 scripts/download.py --folder-id 18625 --output ./backup --env prod

# Dry run to preview files without downloading
python3 scripts/download.py --folder-id 18625 --env prod --dry-run

# Resume an interrupted download
python3 scripts/download.py --folder-id 18625 --output ./backup --env prod --resume

# Force specific strategy
python3 scripts/download.py --folder-id 18625 --output ./backup --env prod --strategy hierarchical
```

### Download Options

| Option | Description | Required |
|--------|-------------|----------|
| `--bundle` | SuiteBundle number to download | One of bundle/folder-id |
| `--folder-id` | Folder ID to download | One of bundle/folder-id |
| `--output` | Local output directory | Yes (for download) |
| `--account` | Account (default: twistedx) | No |
| `--env` | Environment: prod, sb1, sb2 (default: prod) | No |
| `--dry-run` | Preview files without downloading | No |
| `--resume` | Continue from last downloaded file ID | No |
| `--offset` | Start from specific file ID | No |
| `--limit` | Limit number of files to download | No |
| `--strategy` | Force strategy: auto, recursive, hierarchical | No |
| `--format` | Output format: table, json | No |

### Strategy Auto-Detection

The script automatically selects the optimal download strategy:

| Strategy | When Used | Best For |
|----------|-----------|----------|
| **Recursive** | <100 subfolders AND <500 files | Small bundles, shallow folders |
| **Hierarchical** | >100 subfolders OR >500 files | Large attachment folders, deep trees |

**Hierarchical strategy** uses a single SuiteQL query with `CONNECT BY PRIOR` to efficiently traverse the entire folder tree without recursive API calls.

### Key Features

- **Auto-detection**: Chooses recursive vs hierarchical based on folder size
- **Resume support**: `--resume` continues from last successful download
- **Rate limiting**: 0.2s delay between downloads to prevent API throttling
- **Deduplication**: Prevents duplicate downloads with ID-based pagination
- **Skip existing**: Automatically skips already-downloaded files
- **Manifest**: Generates `_manifest.json` tracking all downloaded files

### Download Output Structure

```
output_directory/
├── FolderName1/
│   ├── file1.pdf
│   └── file2.docx
├── FolderName2/
│   └── image.png
└── _manifest.json
```

### Important: Hierarchical Query Pagination

⚠️ **Critical Finding**: OFFSET pagination does NOT work with `CONNECT BY` hierarchical queries. The script uses **ID-based pagination** instead:

```sql
-- WRONG: Returns duplicates with CONNECT BY
SELECT ... OFFSET 1000 ROWS FETCH NEXT 1000 ROWS ONLY

-- CORRECT: ID-based pagination
SELECT ... WHERE f.id > {last_id} ORDER BY f.id FETCH FIRST 1000 ROWS ONLY
```

This is a fundamental SuiteQL/Oracle limitation. The unified script handles this automatically.

## Quick Reference

```bash
# Upload file
python3 scripts/upload_file.py --file ./script.js --folder-id 137935 --env prod

# Find by name
python3 scripts/find_file.py --name "myScript.js" --env prod

# Find by pattern
python3 scripts/find_file.py --pattern "twx_%" --env prod

# List folder contents (subfolders + files)
python3 scripts/list_folder.py --folder-id 137935 --env prod

# Delete a file (auto-backs up to ./trash-bin/ before deleting — dry-run first)
python3 scripts/delete_file.py --file-id 55342202 --name "old_script.js" --dry-run --env sb2
python3 scripts/delete_file.py --file-id 55342202 --name "old_script.js" --confirm --env sb2

# Compare local file vs NetSuite version
python3 scripts/compare_file.py --file ./script.js --file-id 55342202 --env sb2

# Download folder tree
python3 scripts/download.py --folder-id 18625 --output ./backup --env prod

# Download bundle
python3 scripts/download.py --bundle 311735 --output ./backup --env prod

# PCI scan for sensitive data in File Cabinet
python3 scripts/pci_scan.py --folder-id 137935 --env prod
```

## Common Use Cases

### Deploy a Modified Script

```bash
# 1. Find the file to get folder ID
python3 scripts/find_file.py --name "inventoryPartUserEvent.js" --env prod

# 2. Upload the modified version
python3 scripts/upload_file.py --file ./inventoryPartUserEvent.js --folder-id 137935 --env prod
```

### Search for Scripts by Pattern

```bash
# Find all EDI-related scripts
python3 scripts/find_file.py --pattern "%edi%" --env prod

# Find all user event scripts
python3 scripts/find_file.py --pattern "%userEvent%" --env prod
```

### Verify Upload Success

```bash
# Upload file
python3 scripts/upload_file.py --file ./script.js --folder-id 137935 --env prod
# Output: SUCCESS: File uploaded
#   File ID: 265294
#   Name: script.js
#   Folder: 137935

# Verify it exists
python3 scripts/find_file.py --name "script.js" --folder-id 137935 --env prod
```

## Error Handling

### Common Errors

**File not found locally:**
```
ERROR: File not found: ./nonexistent.js
```
→ Check the local file path

**Invalid folder ID:**
```
ERROR: HTTP 400: Invalid folder ID
```
→ Verify the folder ID exists in NetSuite

**Gateway not running:**
```
ERROR: Gateway connection error: Connection refused
```
→ Start the gateway: `cd ~/NetSuiteApiGateway && docker compose up -d`

**Wrong record type for file operations:**
```
ERROR: INVALID_RCRD_TYPE on update_record.py file <id>
```
→ The upsert endpoint does not support the `file` record type. Use `delete_file.py --file-id <id>` for deletion, or `upload_file.py --file-id <id>` to overwrite a specific file.

## Resources

### scripts/upload_file.py
Upload files to NetSuite File Cabinet:
- Auto-detects file type from extension
- Plain text for text files, base64 for binary
- Uses `fileCreate` which overwrites existing files

### scripts/find_file.py
Search for files in NetSuite File Cabinet:
- Search by exact name, pattern (SQL LIKE), or folder ID
- Returns file metadata including folder path
- Multiple output formats (table, json)

### scripts/download.py
Unified bulk download tool for File Cabinet:
- Downloads entire folder trees or SuiteBundles
- Auto-detects optimal strategy (recursive vs hierarchical)
- Resume support for interrupted downloads
- Rate limiting and deduplication built-in
- Generates manifest for tracking

### scripts/list_folder.py
List folder contents and subfolders:
- Shows files and subfolders in a specific folder
- Useful for exploring File Cabinet structure and verifying target folder IDs

### scripts/delete_file.py
Delete files from NetSuite File Cabinet (general-purpose, restore-capable):
- Requires `--dry-run` (preview) or `--confirm` (execute) — no accidental deletes
- Target by `--file-id` (single file) or `--report` (bulk from pci_scan output)
- **Auto-backups each file locally to `./trash-bin/<timestamp>_<env>/files/` before deletion**
- Writes `restore_manifest.json` with folder_id/name/type/size/backup_path per file
- Skips deletion if backup fails (override with `--force-without-backup`)
- **Cannot delete folders** — ask user to delete empty folders via NetSuite UI

### scripts/compare_file.py
Compare local file vs version stored in NetSuite:
- Detects whether a local edit has been deployed
- Useful for verifying an upload took effect

### scripts/pci_scan.py
Scan File Cabinet for files containing PCI-sensitive data:
- Produces `scan_report.json` consumed by `delete_file.py` for bulk deletion
- Useful before PCI audits or after incidents involving sensitive data

### Deprecated Scripts
The following scripts are superseded by `download.py`:
- `download_bundle.py` - Use `download.py --bundle` instead
- `download_folder_tree.py` - Use `download.py --folder-id` instead

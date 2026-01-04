---
name: netsuite-file-cabinet
description: Manage files in NetSuite File Cabinet - upload, find, and list files. Use this skill when you need to upload scripts to NetSuite, find files by name or pattern, or list files in a folder. Triggers include "upload file to NetSuite", "find NetSuite file", "list files in folder", or any File Cabinet operations.
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

**NetSuite API Gateway** must be running:
```bash
cd ~/NetSuiteApiGateway
docker compose up -d
```

Verify gateway is running:
```bash
curl http://localhost:3001/health
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

## Quick Reference

```bash
# Upload file
python3 scripts/upload_file.py --file ./script.js --folder-id 137935 --env prod

# Find by name
python3 scripts/find_file.py --name "myScript.js" --env prod

# Find by pattern
python3 scripts/find_file.py --pattern "twx_%" --env prod

# List folder contents
python3 scripts/find_file.py --folder-id 137935 --env prod
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

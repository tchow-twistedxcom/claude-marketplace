# CRE2 CLI Reference

Quick reference for all CRE2 and related NetSuite CLI scripts.

**Last updated**: 2026-01-27

## Script Locations

| Category | Base Path |
|----------|-----------|
| CRE2 | `~/.claude/plugins/marketplaces/tchow-essentials/plugins/netsuite-skills/skills/netsuite-cre2/scripts/` |
| SuiteQL | `~/.claude/plugins/marketplaces/tchow-essentials/plugins/netsuite-skills/skills/netsuite-suiteql/scripts/` |
| File Cabinet | `~/.claude/plugins/marketplaces/tchow-essentials/plugins/netsuite-skills/skills/netsuite-file-cabinet/scripts/` |

---

## query_netsuite.py (SuiteQL)

**⚠️ Query string MUST be the FIRST positional argument. Options come AFTER.**

```bash
# ✅ CORRECT argument order
python3 query_netsuite.py 'SELECT id FROM customer WHERE ROWNUM <= 5' --env sb2

# ❌ WRONG - options before query string
python3 query_netsuite.py --env sb2 'SELECT id FROM customer WHERE ROWNUM <= 5'
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `<query>` | Yes (positional) | - | SuiteQL query string (MUST be first arg) |
| `--account` / `-a` | No | twistedx | Account: `twx`, `twistedx`, `dm`, `dutyman` |
| `--env` / `-e` | No | sandbox2 | Environment: `prod`, `sb1`, `sb2` |
| `--params` | No | - | Comma-separated `?` placeholder values |
| `--all-rows` | No | false | Fetch all rows with auto-pagination |
| `--format` | No | table | Output: `json`, `table`, `csv` |
| `--list-accounts` | No | - | List available accounts |

---

## upload_file.py (File Cabinet)

**⚠️ Use `--file-id` for existing files (updates in place). Use `--folder-id` only for NEW files.**

```bash
# ✅ Update existing file by ID (PREFERRED - no duplicates)
python3 upload_file.py --file ./myScript.js --file-id 52794157 --env sb2

# ✅ Create new file in folder
python3 upload_file.py --file ./newTemplate.html --folder-id 1285029 --env sb2

# ❌ DANGER - using --folder-id for existing file creates DUPLICATE
python3 upload_file.py --file ./twx_CRE2_EDI_DataExtractor.js --folder-id 1284929 --env sb2
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--file` | Yes | - | Local file path to upload |
| `--file-id` | One of | - | Update existing file by internal ID |
| `--folder-id` | One of | - | Create/overwrite by name in folder |
| `--name` | No | - | Override filename in NetSuite |
| `--description` | No | - | File description |
| `--account` | No | twistedx | Account |
| `--env` | No | sandbox2 | Environment |

**Key difference:** `--folder-id` overwrites by *filename match* within the folder. If the filename doesn't exist there, it creates a NEW file. `--file-id` always updates the exact file.

---

## render_pdf.py (CRE2)

```bash
python3 render_pdf.py --profile-id 635 --record-id 9425522 --env sb2 --open-browser
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--profile-id` / `-p` | Yes | - | CRE2 profile internal ID |
| `--record-id` / `-r` | Yes | - | Source record to render |
| `--account` / `-a` | No | twistedx | Account |
| `--env` / `-e` | No | sandbox2 | Environment |
| `--open-browser` / `-o` | No | false | Open PDF in default browser |
| `--quiet` / `-q` | No | false | Only output URL on success |

**Output:** Returns JSON with `fullPdfUrl` - an external URL that does NOT require NetSuite login.

---

## find_test_records.py (CRE2)

```bash
python3 find_test_records.py --tp-id 22 --doc-type 850 --env sb2
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--tp-id` | Yes | - | Trading partner ID |
| `--doc-type` | No | - | EDI document type (810, 850, etc.) |
| `--env` | No | sandbox2 | Environment |

---

## download_file.py (File Cabinet)

```bash
python3 download_file.py --file-id 52794157 --output ./local_copy.js --env sb2
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--file-id` | Yes | - | NetSuite file internal ID |
| `--output` / `-o` | No | stdout | Local output path |
| `--env` | No | sandbox2 | Environment |

---

## render_test_matrix.py (CRE2)

Batch-render PDFs across multiple trading partners and document types for validation.

```bash
python3 render_test_matrix.py --doc-type 850 --env sb2 --open-browser
python3 render_test_matrix.py --tp-name Runnings --env sb2 --open-browser
python3 render_test_matrix.py --env sb2  # All partners, all doc types
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--doc-type` | No | all | Filter by EDI doc type (810, 850, 855, 856, 860) |
| `--tp-name` | No | all | Filter by trading partner name |
| `--env` | No | sandbox2 | Environment |
| `--open-browser` | No | false | Open each PDF in browser |
| `--output-html` | No | - | Generate HTML report of all rendered PDFs |

**Output:** Renders PDFs for all matching profile/record combinations. With `--output-html`, generates a clickable report page.

---

## Common Workflows

### Update Data Extractor → Render → Verify

```bash
CRE2=~/.claude/plugins/marketplaces/tchow-essentials/plugins/netsuite-skills/skills/netsuite-cre2/scripts
FC=~/.claude/plugins/marketplaces/tchow-essentials/plugins/netsuite-skills/skills/netsuite-file-cabinet/scripts

# 1. Upload JS (ALWAYS use --file-id 52794157)
python3 $FC/upload_file.py --file ./twx_CRE2_EDI_DataExtractor.js --file-id 52794157 --env sb2

# 2. Upload template (use --file-id for existing, --folder-id 1285029 for new)
python3 $FC/upload_file.py --file ./TWX_EDI_850_RUNNINGS_PDF.html --file-id 52794683 --env sb2

# 3. Render PDF
python3 $CRE2/render_pdf.py --profile-id 635 --record-id 9425522 --env sb2 --open-browser
```

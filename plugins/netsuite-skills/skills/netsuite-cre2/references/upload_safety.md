# CRE2 Upload Safety Guide

## Pre-Upload Checklist

Before uploading ANY file to NetSuite, complete these checks:

### 1. Identify the Correct Target

**Data Extractor (JS):**
- **Canonical file ID: 52794157** (folder 1284929 "CRE2")
- ALL CRE2 profiles reference this file via `custrecord_pri_cre2_js_override`
- ALWAYS use `--file-id 52794157`, NEVER `--folder-id`

**Templates (HTML):**
- Check if template already exists: read the `CRE2_NetSuite_Folders` memory for file IDs
- For existing templates: use `--file-id <ID>`
- For new templates: use `--folder-id 1285029`

### 2. Verify Before Upload

**For the Data Extractor:**
```sql
-- Verify which file profiles actually reference
SELECT TOP 1 custrecord_pri_cre2_js_override
FROM customrecord_pri_cre2_profile
WHERE isinactive = 'F'
```
Expected result: **52794157**

**For Templates:**
```bash
# Check if a file with this name already exists in the templates folder
python3 list_folder.py --folder-id 1285029 --env sb2 | grep "TEMPLATE_NAME"
```

### 3. Use `--file-id` Over `--folder-id`

| Method | Behavior | Risk |
|--------|----------|------|
| `--file-id 52794157` | Updates exact file in place | ✅ Safe - no duplicates |
| `--folder-id 1284929` | Overwrites by filename match | ⚠️ Creates duplicate if name differs |
| `--folder-id <WRONG>` | Creates new file in wrong folder | ❌ DUPLICATE - hard to detect |

### 4. Post-Upload Verification

After uploading, verify the file was updated:
```bash
# Download and compare
python3 download_file.py --file-id 52794157 --output /tmp/verify.js --env sb2
diff /tmp/verify.js ./twx_CRE2_EDI_DataExtractor.js
```

---

## Duplicate Prevention

### How Duplicates Happen

1. Using `--folder-id` with the wrong folder ID
2. Using `--folder-id` when `--file-id` should be used
3. Uploading to a folder where the filename doesn't match an existing file (creates new)
4. Uploading the same file to multiple folders across sessions

### Detection

If a PDF render doesn't reflect your changes:

1. **Don't assume caching** - NetSuite doesn't cache JS overrides
2. **Check which file the profile uses:**
   ```sql
   SELECT custrecord_pri_cre2_js_override
   FROM customrecord_pri_cre2_profile
   WHERE id = <PROFILE_ID>
   ```
3. **Compare the file ID you uploaded to vs the one the profile references**
4. **Search for duplicates:**
   ```bash
   python3 find_file.py --name "twx_CRE2_EDI_DataExtractor.js" --env sb2
   ```
   If more than 1 result, you have duplicates.

### Recovery

If duplicates are found:
1. Identify the canonical file (the one profiles reference)
2. Upload your changes to the canonical file using `--file-id`
3. Delete the duplicates (user must do this manually or via script)

---

## Common Mistakes & Fixes

### "My changes aren't showing up in the PDF"

**Checklist:**
1. Did you upload to the correct file ID? (52794157 for JS)
2. Did you use `--file-id` or `--folder-id`?
3. Query the profile to verify which file it references
4. Search for duplicate files with the same name

**It's NOT a cache issue.** If changes don't appear, you uploaded to the wrong file.

### "I created a duplicate file"

**Fix:**
1. Upload to the correct file: `--file-id 52794157`
2. Delete the duplicate (manually in NetSuite or via API)
3. Update the `CRE2_NetSuite_Folders` memory with any new file IDs

### "I don't know the file ID for a template"

**Find it:**
```bash
python3 find_file.py --name "TWX_EDI_850_RUNNINGS_PDF.html" --env sb2
```
Or check the `CRE2_NetSuite_Folders` memory.

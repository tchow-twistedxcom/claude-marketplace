---
date: 2026-04-16
topic: netsuite-pci-file-scrubbing
---

# NetSuite Filing Cabinet PCI Compliance File Scrubbing

## Problem Frame

The Twisted X Attachments directory (NetSuite Filing Cabinet folder ID 18625) contains ~66,562 files — mostly PDFs, plus Excel, Word, and images. An automated scan previously identified 500+ files that may contain credit card data. These files must be validated and then permanently deleted from the Filing Cabinet for PCI-DSS compliance.

The original downloaded files no longer exist locally. Files must be re-downloaded from NetSuite for validation before deletion.

## Requirements

**ID Resolution & Download**
- R1. Accept a user-provided list of file names/paths and resolve each to a NetSuite internal file ID using the existing inventory (`netsuite-attachments-inventory-clean.json`, 66,562 entries)
- R2. Report any list entries that cannot be matched to the inventory (typos, renamed files, missing entries)
- R3. Batch download only the matched files from NetSuite via the API gateway (`fileGet` action)

**PCI Validation Scan**
- R4. Extract text from downloaded files based on type: text extraction for PDFs, OCR fallback for scanned/image PDFs, cell extraction for Excel (.xlsx/.xls), text extraction for Word docs
- R5. Scan extracted text for credit card patterns (Visa, Mastercard, Amex, Discover) using regex + Luhn checksum validation to minimize false positives
- R6. Classify each file as CONFIRMED (card data found), NOT_FOUND (no card data detected), or ERROR (extraction/processing failed)
- R7. For CONFIRMED files, include redacted context snippets showing where the match was found (e.g., "Found on page 3: 4111-XXXX-XXXX-1111")

**Reporting**
- R8. Generate a structured report (JSON + human-readable summary) with per-file results, match counts, and categorization breakdown
- R9. Clearly separate CONFIRMED files (ready for deletion) from NOT_FOUND files (original scan may have been a false positive) and ERROR files (need manual review)

**Deletion**
- R10. Delete confirmed files from NetSuite Filing Cabinet using the existing RESTlet `fileDelete` endpoint via the API gateway
- R11. Support dry-run mode that reports what would be deleted without executing
- R12. Log every deletion attempt with file ID, name, timestamp, and result (success/failure) for PCI audit trail

**Safety**
- R13. Require explicit user confirmation before executing any deletions (no auto-delete)
- R14. Generate a pre-deletion manifest that the user reviews and approves
- R15. Handle API errors gracefully — skip failed deletions, continue with remaining files, report failures at the end

## Success Criteria

- Every file on the user's list is either validated (CONFIRMED/NOT_FOUND) or flagged as ERROR with a reason
- Zero files are deleted without explicit user approval
- A complete audit log exists documenting what was scanned, what was found, and what was deleted
- Files that the original scan flagged but our re-scan does NOT confirm are surfaced for human decision

## Scope Boundaries

- **In scope:** Validation scan + deletion of files on the user's provided list only
- **Out of scope:** Scanning the entire 66,562-file attachment directory for additional PCI data
- **Out of scope:** Redacting card data from files (we delete, not redact)
- **Out of scope:** Modifying NetSuite records that reference deleted attachments (may need separate cleanup)

## Key Decisions

- **Full re-scan over sampling:** Every flagged file gets independently verified. PCI compliance requires defensible evidence of what was deleted and why.
- **Download-then-scan over NetSuite-side scanning:** NetSuite has no built-in PCI scanning capability. Files must be downloaded locally for text extraction and pattern matching.
- **Delete over redact:** Simpler, lower risk, and fully eliminates the PCI exposure. Redaction would require re-uploading modified files and is error-prone for scanned PDFs.

## Dependencies / Assumptions

- NetSuite API gateway is running on `localhost:3001` and the RESTlet supports `fileDelete` (verified — exists in `suiteapi.restlet.js`)
- No Python `delete_file.py` wrapper exists yet — needs to be created (RESTlet backend is ready)
- OCR requires Tesseract and poppler to be installed for scanned PDF support
- The inventory JSON (`netsuite-attachments-inventory-clean.json`) is current enough to resolve file IDs — if files were added/removed since Feb 2026, some matches may fail

## Outstanding Questions

### Deferred to Planning
- [Affects R4][Needs research] Which Python libraries to use for text extraction (pdfplumber vs PyPDF2, pytesseract setup, openpyxl vs xlrd for older .xls files)
- [Affects R1][Technical] How to handle ambiguous matches (e.g., same filename in different folders) — match on full path or require user disambiguation?
- [Affects R10][Technical] Rate limiting for `fileDelete` calls — NetSuite may throttle bulk API operations
- [Affects R4][Needs research] Whether Tesseract/poppler are already installed or need setup
- [Affects scope][Technical] Whether NetSuite records (transactions, entities) that reference deleted attachments need cleanup or will gracefully handle missing files

## Next Steps

-> `/ce:plan` for structured implementation planning

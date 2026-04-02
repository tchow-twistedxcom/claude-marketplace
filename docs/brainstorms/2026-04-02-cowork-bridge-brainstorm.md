---
title: Claude Code ↔ Cowork Bridge
date: 2026-04-02
topic: cowork-bridge
status: complete
---

# Brainstorm: Claude Code ↔ Cowork Bridge

## What We're Building

A **shared workspace system** that lets Claude Code generate structured artifacts (analysis reports, structured data, code + docs) that Claude Cowork can consume and transform into polished **client deliverables** (reports, proposals, dashboards/decks).

### Components

1. **Shared folder** at `~/cowork-bridge/` with convention-based structure
2. **Claude Code plugin** (`cowork-bridge`) in tchow-essentials marketplace
3. **SharePoint sync** via `abraunegg/onedrive` for cross-device access
4. **Manifest system** tracking artifacts and status
5. **Templates** guiding Cowork behavior for each deliverable type

## Why This Approach

- **SharePoint as shared layer** — enterprise-grade, works across devices, Cowork native connector
- **abraunegg/onedrive** (12k stars) — purpose-built Linux OneDrive/SharePoint client, bidirectional, real-time
- **Zero custom infrastructure** — just folder conventions + sync tool
- **Portable** — plugin in tchow-essentials, versioned, reusable

## Key Decisions

| Decision | Choice | Reasoning |
|---|---|---|
| Shared folder | `~/cowork-bridge/` | Dedicated top-level, clean separation |
| Sync | abraunegg/onedrive → SharePoint | Enterprise-grade, bidirectional, real-time |
| Cowork access | SharePoint connector (native) | No folder-scoping required |
| Template format | Pure markdown | Simple, editable, Cowork consumes naturally |
| Packaging | tchow-essentials plugin | Versioned, follows existing patterns |
| Archive policy | Manual | User decides when to archive |

## Architecture

```
Linux Server                    SharePoint Online                  Cowork
~/cowork-bridge/ ──sync──► SP Document Library ◄──connector── Claude Cowork
 (Claude Code writes)      (abraunegg/onedrive)               (reads & produces)
```

## Deliverable Pipelines

| Pipeline | Code Generates | Cowork Produces |
|---|---|---|
| Audit → Report | Findings md, JSON evidence, severity | Client-facing PDF/DOCX with exec summary |
| Integration → Proposal | API analysis, flow diagrams, capability matrix | Proposal with timeline, costs, architecture |
| Data → Deck | Structured JSON/CSV, metrics, trends | Presentation deck or visual summary |

## Resolved Questions

1. **Template format** → Pure markdown
2. **Archive policy** → Manual
3. **SharePoint sync tool** → abraunegg/onedrive (over rclone — bidirectional is default, not beta)
4. **Folder location** → `~/cowork-bridge/`
5. **Packaging** → New plugin in tchow-essentials marketplace

---
status: pending
priority: p3
issue_id: "110"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 110 — `server.py` line 2248: `except Exception: pass` should be `except ValueError: pass`

## Problem Statement

`server.py` line 2248 uses `except Exception: pass` to silently swallow a specific expected error. The context is a JSON/value parsing step where only `ValueError` (and possibly `KeyError`) is expected. Using `except Exception` swallows broader errors (network failures, `AttributeError`, `TypeError`) that should propagate. This is the standard overly-broad exception anti-pattern.

## Findings

- **`server.py` ~line 2248**: `except Exception: pass` in a parsing context
- Only `ValueError` (bad format) is the expected failure mode
- Broader exceptions should propagate for debugging
- Flagged by: kieran-python-reviewer (7th review pass)

## Proposed Solutions

### Option A: Narrow to `except (ValueError, KeyError): pass`

Replace with the specific expected exceptions.

- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria

- [ ] `except Exception: pass` at line 2248 replaced with `except (ValueError, KeyError): pass` or narrower

## Work Log

- 2026-04-08: Identified in 7th code review pass (kieran-python-reviewer)

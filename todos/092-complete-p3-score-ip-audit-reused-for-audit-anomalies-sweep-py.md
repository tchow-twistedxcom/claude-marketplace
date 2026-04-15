---
status: complete
priority: p3
issue_id: "092"
tags: [code-review, quality, azure-ad, sweep]
dependencies: []
---

# 092 — `_SCORE_IP_AUDIT` constant reused for `audit_anomalies` in sweep.py

## Problem Statement

`sweep.py` has a `_SCORE_IP_AUDIT` constant that is reused for `audit_anomalies` scoring, conflating two semantically different scoring purposes. The constant name implies IP-based scoring but it is applied to a different detection type. Separate constants improve clarity and allow independent tuning.

## Findings

- **sweep.py**: `_SCORE_IP_AUDIT` used for `audit_anomalies` detection — misleading name
- Two different detection types sharing one constant makes independent tuning harder
- Flagged by: code-simplicity-reviewer

## Proposed Solutions

### Option A: Add separate `_SCORE_AUDIT_ANOMALY` constant
```python
_SCORE_IP_AUDIT = 25        # for IP-based audit events
_SCORE_AUDIT_ANOMALY = 25   # for audit anomaly detection (can be tuned independently)
```
Replace the `_SCORE_IP_AUDIT` usage in `audit_anomalies` with `_SCORE_AUDIT_ANOMALY`.
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [x] `_SCORE_IP_AUDIT` used only for IP-based audit scoring
- [x] `_SCORE_AUDIT_ANOMALY` (or similar) used for audit anomaly scoring
- [x] Both constants have equal values initially (no behavioral change)

## Work Log
- 2026-04-08: Identified in 6th code review pass (code-simplicity-reviewer)
- 2026-04-08: Fixed — added `_SCORE_AUDIT_ANOMALY = 1` alongside `_SCORE_IP_AUDIT = 1`; replaced `_SCORE_IP_AUDIT` with `_SCORE_AUDIT_ANOMALY` in the `audit_anomalies` branch of `compute_confidence`. Commit: refactor(sweep): separate audit anomaly score constant; fix typing (todos 092, 098)

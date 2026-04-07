---
status: complete
priority: p3
issue_id: "032"
tags: [code-review, bug, azure-ad, sweep]
dependencies: []
---

# 032 — sweep.py progress output goes to stdout — corrupts --json output when piped

## Problem Statement

`sweep.py` prints progress messages (`[1/5] IP sweep...`, `[2/5] MFA fatigue...`, etc.) to `stdout` rather than `stderr`. When an agent runs `python3 sweep.py --hours 48 --json` and pipes the output for parsing, the progress lines appear mixed into the JSON output, causing `json.loads()` to fail.

## Findings

- **File**: `plugins/m365-skills/skills/azure-ad/scripts/sweep.py`, lines 207, 223, 229, 248, 272, 288
- **Agent**: agent-native-reviewer (Warning)

```python
print(f"\n[1/5] IP sweep ({len(suspect_ips)} IPs)...")  # stdout — breaks --json
print(f"  [✓] {len(all_sign_ins)} sign-ins from {len(suspect_ips)} IPs")
```

Command that fails:
```bash
python3 sweep.py --hours 48 --json | python3 -c "import sys,json; data=json.load(sys.stdin)"
# Fails: json.decoder.JSONDecodeError: Extra data
```

## Proposed Solutions

### Option A: Move all progress prints to stderr (Recommended)
```python
print(f"\n[1/5] IP sweep ({len(suspect_ips)} IPs)...", file=sys.stderr)
```

### Option B: Suppress progress when --json flag is set
```python
if not args.json:
    print(f"\n[1/5] IP sweep...")
```

## Recommended Action

Option A — route all progress/status output to `stderr`. `--json` mode is explicitly for machine consumption; status messages belong on `stderr` by POSIX convention.

## Acceptance Criteria

- [x] All progress lines in `run_sweep()` use `file=sys.stderr`
- [x] `python3 sweep.py --hours 48 --json | python3 -c "import sys,json; json.load(sys.stdin)"` succeeds

## Work Log

- 2026-04-07: Identified by agent-native-reviewer
- 2026-04-07: Fixed — added `file=sys.stderr` to all six `print()` progress statements in `run_sweep()` (lines covering [1/5] through [5/5] steps, both the active and skipped/empty branches). Also improved bare `except: continue` to `except Exception as e:` with stderr logging. Committed in 94b6d3c as part of fix(sweep) commit covering todos 032 and 033.

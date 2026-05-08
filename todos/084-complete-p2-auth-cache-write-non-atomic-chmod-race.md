---
status: complete
priority: p2
issue_id: "084"
tags: [code-review, security, azure-ad, credentials]
dependencies: []
---

# 084 — Non-atomic token cache write in `auth.py`: brief 0o644 window before chmod 600

## Problem Statement

`_save_token_cache` in `auth.py` writes the token cache with a two-step pattern: `open(..., 'w')` (which creates the file with umask permissions, typically `0o644`) then `os.chmod(path, 0o600)`. There is a brief race window between file creation and permission tightening where any process running as the same OS user can read the access token. Additionally, if the process is killed between `open` and `json.dump` completing, the token file is left empty or truncated.

## Findings

- **auth.py lines 163-171**:
```python
def _save_token_cache(self, cache: dict[str, Any]):
    try:
        with open(self.token_cache_path, 'w') as f:   # creates at 0o644 (umask)
            json.dump(cache, f, indent=2)              # write may be interrupted
        os.chmod(self.token_cache_path, 0o600)         # too late — race window exists
```
- On Linux, file creation and `chmod` are separate syscalls — not atomic
- If file didn't previously exist: window between `open()` and `chmod()` has 0o644 permissions
- Flagged by: security-sentinel (low severity)

## Proposed Solutions

### Option A: Atomic write via temp file + os.replace (Recommended)
```python
import tempfile
tmp_fd, tmp_path = tempfile.mkstemp(dir=self.token_cache_path.parent, suffix='.tmp')
try:
    os.chmod(tmp_path, 0o600)          # chmod before writing
    with os.fdopen(tmp_fd, 'w') as f:
        json.dump(cache, f, indent=2)
    os.replace(tmp_path, self.token_cache_path)  # atomic rename
except Exception:
    os.unlink(tmp_path)
    raise
```
- `chmod` before write; atomic rename eliminates both races
- **Effort**: Small | **Risk**: Low

### Option B: Pre-create file with correct permissions
```python
# Create file with 0o600 before writing (if not exists)
if not self.token_cache_path.exists():
    self.token_cache_path.touch(mode=0o600)
with open(self.token_cache_path, 'w') as f:
    json.dump(cache, f, indent=2)
os.chmod(self.token_cache_path, 0o600)  # re-apply in case it existed with wrong perms
```
- Reduces (but doesn't eliminate) the race for new files
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [ ] Token cache file is never readable by same-user processes between creation and permissions setting
- [ ] Write is atomic: no partial/empty token files on process interruption
- [ ] Temp file is cleaned up on failure

## Work Log
- 2026-04-08: Identified in 6th code review pass (security-sentinel)
- 2026-04-08: Resolved — replaced open+chmod pattern with tempfile.mkstemp+os.replace atomic write; chmod applied before write; cleanup on exception; _get_token_cache_path now returns Path. Commit: 37954cf

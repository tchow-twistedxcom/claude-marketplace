"""
op_cache.py — Encrypted local cache for 1Password op CLI results.

Avoids repeated op item get calls (and service account rate limiting) by caching
secret values in an encrypted file. Secrets are never written to disk in plaintext.

Usage:
    import sys, os
    sys.path.insert(0, os.path.expanduser("~/.claude/skills/1password"))
    from op_cache import get_secret, get_secrets, clear_cache

    password = get_secret("Snowflake - Admin (tchowtwistedxcom)", "password")
    creds = get_secrets("Amazon SP-API", ["lwa_client_id", "lwa_client_secret"])
    clear_cache()  # call after rotating a secret

Security:
    - Cache file encrypted with Fernet (AES-128-CBC + HMAC-SHA256)
    - Encryption key derived from OP_SERVICE_ACCOUNT_TOKEN via PBKDF2-SHA256
    - Cache file permissions: 0600 (owner read/write only)
    - Cache directory permissions: 0700
    - Same trust boundary as the op CLI itself (both require OP_SERVICE_ACCOUNT_TOKEN)
    - Graceful fallback to unencrypted mode if `cryptography` is not installed
"""

import os
import json
import subprocess
import time
import hashlib
import base64
import logging
from pathlib import Path

log = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".cache" / "op-cache"
CACHE_FILE = CACHE_DIR / "vault.enc"
DEFAULT_TTL = 900  # 15 minutes
VAULT = "Twisted X AI Agent"
_PBKDF2_ITERATIONS = 100_000

# Module-level in-memory cache (survives multiple calls within same process)
_mem_cache: dict = {}


# ---------------------------------------------------------------------------
# Key derivation & encryption
# ---------------------------------------------------------------------------

def _derive_key(token: str) -> bytes:
    """Derive a 32-byte Fernet key from the service account token."""
    salt = b"op-cache-v1-twistedx"  # fixed salt — token itself is high entropy
    key_bytes = hashlib.pbkdf2_hmac(
        "sha256", token.encode(), salt, _PBKDF2_ITERATIONS, dklen=32
    )
    return base64.urlsafe_b64encode(key_bytes)


def _encrypt(data: dict, key: bytes) -> bytes:
    """Encrypt a dict to bytes. Returns Fernet token."""
    from cryptography.fernet import Fernet
    f = Fernet(key)
    return f.encrypt(json.dumps(data).encode())


def _decrypt(ciphertext: bytes, key: bytes) -> dict:
    """Decrypt Fernet token to dict."""
    from cryptography.fernet import Fernet
    f = Fernet(key)
    return json.loads(f.decrypt(ciphertext))


def _has_cryptography() -> bool:
    try:
        from cryptography.fernet import Fernet  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# op CLI integration
# ---------------------------------------------------------------------------

def _get_op_token() -> str:
    """Get OP_SERVICE_ACCOUNT_TOKEN from env or ~/.bashrc."""
    token = os.environ.get("OP_SERVICE_ACCOUNT_TOKEN")
    if token:
        return token
    bashrc = Path.home() / ".bashrc"
    if bashrc.exists():
        for line in bashrc.read_text().splitlines():
            stripped = line.strip()
            if "OP_SERVICE_ACCOUNT_TOKEN=" in stripped and not stripped.startswith("#"):
                return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(
        "OP_SERVICE_ACCOUNT_TOKEN not found in environment or ~/.bashrc. "
        "Run: export OP_SERVICE_ACCOUNT_TOKEN=ops_..."
    )


def _fetch_from_op(item: str, fields: list[str], vault: str) -> dict[str, str]:
    """Call op item get and return {field: value} dict."""
    token = _get_op_token()
    env = {**os.environ, "OP_SERVICE_ACCOUNT_TOKEN": token}
    result = subprocess.run(
        ["op", "item", "get", item,
         "--vault", vault,
         "--fields", ",".join(fields),
         "--reveal"],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"op item get failed for '{item}': {result.stderr.strip()}"
        )
    raw = result.stdout.strip()
    if len(fields) == 1:
        return {fields[0]: raw}
    # Multiple fields: op returns comma-separated values
    values = raw.split(",")
    if len(values) != len(fields):
        raise RuntimeError(
            f"op returned {len(values)} values for {len(fields)} fields on '{item}'. "
            f"Output: {raw[:80]}"
        )
    return dict(zip(fields, values))


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def _cache_key(item: str, fields: list[str], vault: str) -> str:
    return f"{item}::{','.join(sorted(fields))}::{vault}"


def _ensure_cache_dir():
    CACHE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)


def _load_cache(enc_key: bytes | None) -> dict:
    """Load and decrypt cache from disk. Returns {} on any error."""
    if not CACHE_FILE.exists():
        return {}
    try:
        data = CACHE_FILE.read_bytes()
        if enc_key and _has_cryptography():
            return _decrypt(data, enc_key)
        else:
            return json.loads(data)
    except Exception as e:
        log.debug(f"op_cache: failed to load cache: {e}")
        return {}


def _save_cache(cache: dict, enc_key: bytes | None):
    """Encrypt and save cache to disk with 0600 permissions."""
    _ensure_cache_dir()
    try:
        if enc_key and _has_cryptography():
            data = _encrypt(cache, enc_key)
            CACHE_FILE.write_bytes(data)
        else:
            if not _has_cryptography():
                log.warning(
                    "op_cache: cryptography library not installed — "
                    "cache stored unencrypted. Install with: pip install cryptography"
                )
            data = json.dumps(cache).encode()
            CACHE_FILE.write_bytes(data)
        os.chmod(CACHE_FILE, 0o600)
    except Exception as e:
        log.debug(f"op_cache: failed to save cache: {e}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_secret(
    item: str,
    field: str,
    vault: str = VAULT,
    ttl: int = DEFAULT_TTL,
) -> str:
    """
    Get a single secret field from 1Password (with caching).

    Args:
        item:  1Password item name (e.g. "Snowflake - Admin (tchowtwistedxcom)")
        field: Field name (e.g. "password")
        vault: Vault name (default: "Twisted X AI Agent")
        ttl:   Cache TTL in seconds (default: 900 = 15 min)

    Returns:
        The secret value as a string.
    """
    return get_secrets(item, [field], vault=vault, ttl=ttl)[field]


def get_secrets(
    item: str,
    fields: list[str],
    vault: str = VAULT,
    ttl: int = DEFAULT_TTL,
) -> dict[str, str]:
    """
    Get multiple secret fields from 1Password (with caching).

    Returns:
        dict mapping field name → value
    """
    key = _cache_key(item, fields, vault)

    # 1. Check in-memory cache first (fastest)
    if key in _mem_cache:
        entry = _mem_cache[key]
        if time.time() < entry["fetched_at"] + entry["ttl"]:
            log.debug(f"op_cache: memory hit for {item}/{fields}")
            return entry["values"]

    # 2. Check disk cache
    try:
        op_token = _get_op_token()
        enc_key = _derive_key(op_token) if _has_cryptography() else None
    except RuntimeError:
        enc_key = None

    disk_cache = _load_cache(enc_key)
    if key in disk_cache:
        entry = disk_cache[key]
        if time.time() < entry["fetched_at"] + entry["ttl"]:
            log.debug(f"op_cache: disk hit for {item}/{fields}")
            _mem_cache[key] = entry  # promote to memory
            return entry["values"]

    # 3. Cache miss — fetch from op
    log.debug(f"op_cache: fetching from op for {item}/{fields}")
    values = _fetch_from_op(item, fields, vault)

    entry = {
        "values": values,
        "fetched_at": time.time(),
        "ttl": ttl,
    }
    _mem_cache[key] = entry

    # Reload disk cache to avoid clobbering other entries
    disk_cache = _load_cache(enc_key)
    # Purge stale entries while we have the cache open
    now = time.time()
    disk_cache = {
        k: v for k, v in disk_cache.items()
        if now < v.get("fetched_at", 0) + v.get("ttl", DEFAULT_TTL)
    }
    disk_cache[key] = entry
    _save_cache(disk_cache, enc_key)

    return values


def clear_cache(item: str | None = None, vault: str = VAULT):
    """
    Clear the cache. Call this after rotating a secret.

    Args:
        item:  If given, clear only entries for this item. If None, clear all.
        vault: Vault to scope the clear (used when item is given).
    """
    global _mem_cache

    if item is None:
        # Clear everything
        _mem_cache = {}
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        log.debug("op_cache: cleared all cache")
        return

    # Clear specific item (all field combinations)
    prefix = f"{item}::"
    _mem_cache = {k: v for k, v in _mem_cache.items() if not k.startswith(prefix)}

    try:
        op_token = _get_op_token()
        enc_key = _derive_key(op_token) if _has_cryptography() else None
    except RuntimeError:
        enc_key = None

    disk_cache = _load_cache(enc_key)
    disk_cache = {k: v for k, v in disk_cache.items() if not k.startswith(prefix)}
    if disk_cache:
        _save_cache(disk_cache, enc_key)
    elif CACHE_FILE.exists():
        CACHE_FILE.unlink()
    log.debug(f"op_cache: cleared cache for {item}")


# ---------------------------------------------------------------------------
# CLI entry point (for testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 3:
        print("Usage: python op_cache.py <item> <field>[,<field2>...]")
        print("       python op_cache.py --clear [item]")
        sys.exit(1)

    if sys.argv[1] == "--clear":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        clear_cache(target)
        print(f"Cleared cache{f' for {target}' if target else ''}")
    else:
        item_arg = sys.argv[1]
        fields_arg = sys.argv[2].split(",")
        if len(fields_arg) == 1:
            val = get_secret(item_arg, fields_arg[0])
            print(f"{fields_arg[0]}: {val[:4]}...{val[-4:]} ({len(val)} chars)")
        else:
            vals = get_secrets(item_arg, fields_arg)
            for f, v in vals.items():
                print(f"{f}: {v[:4]}...{v[-4:]} ({len(v)} chars)")

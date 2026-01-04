# API Integration Skills - Established Patterns

Reference document for creating API integration skills following the patterns established in tchow-essentials marketplace.

## Directory Structure

```
skills/<skill-name>/
├── SKILL.md                     # Skill definition (YAML frontmatter)
├── README.md                    # Setup guide for users
├── config/
│   ├── <skill>_config.template.json   # ✓ Checked into git
│   ├── <skill>_config.json            # ✗ NOT checked in (user creates)
│   └── .<skill>_tokens.json           # ✗ NOT checked in (auto-generated)
├── scripts/
│   ├── auth.py                        # Authentication module
│   ├── <skill>_api.py                 # Main CLI/API client
│   └── formatters.py                  # Output formatting (optional)
└── references/
    ├── <resource>_api.md              # API reference docs
    └── filters_api.md                 # Filter/query patterns
```

## Config Template Pattern

### Template File (checked in)
`config/<skill>_config.template.json` - Safe to commit, contains placeholders:

```json
{
  "accounts": {
    "production": {
      "name": "Production",
      "api_url": "https://api.example.com/v1",
      "api_key": "YOUR_API_KEY",
      "api_secret": "YOUR_API_SECRET"
    }
  },
  "defaults": {
    "account": "production",
    "timeout": 30,
    "max_retries": 3
  },
  "aliases": {
    "prod": "production"
  }
}
```

### Live Config (NOT checked in)
User copies template and fills in real credentials:
```bash
cp config/<skill>_config.template.json config/<skill>_config.json
# Edit with real credentials
```

## Multi-Account/Environment Support

Support multiple accounts with aliases for convenience:

```json
{
  "accounts": {
    "production": {
      "name": "Production",
      "api_url": "https://api.example.com/v1",
      "api_key": "prod-key-xxx"
    },
    "staging": {
      "name": "Staging",
      "api_url": "https://staging-api.example.com/v1",
      "api_key": "stg-key-xxx"
    }
  },
  "defaults": {
    "account": "production"
  },
  "aliases": {
    "prod": "production",
    "stg": "staging",
    "dev": "staging"
  }
}
```

Usage in auth module:
```python
def resolve_account(self, alias):
    """Resolve account alias to canonical name."""
    if alias is None:
        alias = self.config.get('defaults', {}).get('account', 'production')
    aliases = self.config.get('aliases', {})
    return aliases.get(alias.lower(), alias.lower())
```

## Token Cache Convention

**Pattern**: `.<skill>_tokens.json`

All skills use skill-specific token cache files:
- `.plytix_tokens.json`
- `.atlassian_tokens.json`
- `.shopify_tokens.json`

### Token Cache Structure
```json
{
  "production": {
    "token": "access-token-here",
    "expiry": 1703001600,
    "obtained_at": 1702998000
  }
}
```

### Implementation Pattern
```python
TOKEN_CACHE_PATH = Path(__file__).parent.parent / 'config' / '.<skill>_tokens.json'
TOKEN_REFRESH_BUFFER = 300  # Refresh 5 min before expiry

def _load_token_cache(self):
    """Load persistent token cache from disk."""
    if TOKEN_CACHE_PATH.exists():
        try:
            with open(TOKEN_CACHE_PATH, 'r') as f:
                cache = json.load(f)
                # Validate and remove expired entries
                valid_cache = {}
                current_time = time.time()
                for account, data in cache.items():
                    if isinstance(data, dict) and 'token' in data and 'expiry' in data:
                        if data['expiry'] > current_time + TOKEN_REFRESH_BUFFER:
                            valid_cache[account] = data
                return valid_cache
        except (json.JSONDecodeError, IOError):
            pass
    return {}

def _save_token_cache(self):
    """Save token cache to disk for persistence."""
    try:
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp_path = TOKEN_CACHE_PATH.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(self._token_cache, f, indent=2)
        temp_path.replace(TOKEN_CACHE_PATH)  # Atomic write
    except IOError as e:
        print(f"Warning: Could not save token cache: {e}", file=sys.stderr)
```

## Authentication Patterns

### Pattern 1: API Key + Password → Access Token (Plytix)
```python
# Auth URL: POST with JSON body
data = json.dumps({
    'api_key': account_config['api_key'],
    'api_password': account_config['api_password']
}).encode('utf-8')

# Response: {"data": [{"access_token": "...", "expires_in": 3600}]}
```

### Pattern 2: OAuth 2.0 Refresh Token (Atlassian, Shopify)
```python
# Refresh token exchange
data = urlencode({
    'grant_type': 'refresh_token',
    'client_id': oauth['client_id'],
    'client_secret': oauth['client_secret'],
    'refresh_token': oauth['refresh_token']
}).encode('utf-8')

# Handle token rotation (save new refresh token if provided)
if 'refresh_token' in result and result['refresh_token'] != oauth['refresh_token']:
    self._update_refresh_token(result['refresh_token'])
```

### Pattern 3: Static API Key (Celigo)
```python
# Bearer token, no refresh needed
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}
# No token caching required - key is static
```

## Retry Logic Pattern

```python
TOKEN_RETRIES = 3
TOKEN_BACKOFF = 1.0  # Base backoff in seconds

def _get_token_with_retry(self, account, retries=None, backoff=None):
    retries = retries if retries is not None else TOKEN_RETRIES
    backoff = backoff if backoff is not None else TOKEN_BACKOFF

    last_error = None
    for attempt in range(retries):
        try:
            return self._do_get_token(account)
        except AuthError as e:
            error_str = str(e).lower()
            # Permanent failures - don't retry
            if 'invalid' in error_str and ('key' in error_str or 'credential' in error_str):
                raise AuthError(f"Invalid credentials: {e}")
            if '401' in error_str or 'unauthorized' in error_str:
                raise AuthError(f"Unauthorized: {e}")
            # Transient failures - retry with exponential backoff
            last_error = e
            if attempt < retries - 1:
                sleep_time = backoff * (2 ** attempt)
                time.sleep(sleep_time)
    raise last_error
```

## Gitignore Requirements

Add to root `.gitignore`:

```gitignore
# Skill credentials (live configs - NOT templates)
**/shopify_config.json
**/plytix_config.json
**/atlassian_config.json
**/celigo_config.json
**/<new_skill>_config.json

# Token caches (all skills use .<skill>_tokens.json pattern)
**/*_tokens.json
```

## Auth Module Checklist

When creating a new API integration skill's auth.py:

- [ ] Config path constants (`DEFAULT_CONFIG_PATH`, `TOKEN_CACHE_PATH`)
- [ ] Custom exception class (`<Skill>AuthError`)
- [ ] Config loading with validation
- [ ] Multi-account support with `resolve_account()`
- [ ] Token caching with expiry checking
- [ ] Atomic file writes (temp file + rename)
- [ ] Retry logic with exponential backoff
- [ ] Distinguish permanent vs transient failures
- [ ] `get_headers()` convenience method
- [ ] `get_api_url()` for base URL resolution
- [ ] `list_accounts()` for user info
- [ ] `clear_cache()` for debugging
- [ ] `test_connection()` for validation
- [ ] CLI test mode when run as `__main__`

## Reference Documentation Pattern

Create `references/<resource>_api.md` files with:

1. **Endpoint Table**: Method, Endpoint, Description
2. **CLI Commands**: With examples and options
3. **Object Schema**: JSON structure with field descriptions
4. **Common Patterns**: Frequent use cases with bash examples

Example structure:
```markdown
# Resource API Reference

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/resource` | List resources |
| POST | `/resource` | Create resource |

## CLI Commands

### List Resources
\`\`\`bash
python scripts/<skill>_api.py resource list [options]
\`\`\`

## Resource Object

\`\`\`json
{
  "id": "uuid",
  "name": "Resource Name",
  "created": "2024-01-20T14:45:00Z"
}
\`\`\`

## Common Patterns

\`\`\`bash
# Export all resources
python scripts/<skill>_api.py resource list --format json > resources.json
\`\`\`
```

## Existing Skills Reference

| Skill | Auth Type | Token Cache | Multi-Account |
|-------|-----------|-------------|---------------|
| plytix-api | API Key → Token | `.plytix_tokens.json` | Yes |
| atlassian-api | OAuth 2.0 Refresh | `.atlassian_tokens.json` | Yes (multi-site) |
| shopify-* | OAuth 2.0 Refresh | `.shopify_tokens.json` | Yes |
| celigo-* | Static Bearer Key | None needed | Single account |
| netsuite-* | OAuth 2.0 / TBA | Varies | Yes |

---

*Last updated based on plytix-skills, atlassian-skills, shopify-workflows, celigo-integration patterns.*

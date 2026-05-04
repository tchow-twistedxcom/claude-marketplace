# Vendor Information

Source: https://github.com/oracle/netsuite-suitecloud-sdk
Path: packages/agent-skills/
Pinned commit: aacec97486ff7dbc3a4b07b19d3687408f91c866
Commit date: 2026-04-30
Vendor date: 2026-05-04
License: Universal Permissive License (UPL), Version 1.0

## Integrity baseline

Computed over all files under `skills/` (sha256 of sorted-path sha256s):

```
9edc3b3bc0c90149addd75ee77fe92b1016fe8345facb570a875c9aed7cec49d
```

To verify:
```bash
find plugins/netsuite-oracle-skills/skills -type f | sort | xargs sha256sum | awk '{print $1}' | sha256sum
```

## Refresh procedure

```bash
# 1. Clone upstream at the new commit SHA
NEWSHA=<new-sha>
mkdir -p /tmp/ns-vendor && cd /tmp/ns-vendor
git init -q && git remote add origin https://github.com/oracle/netsuite-suitecloud-sdk.git
git sparse-checkout init --cone && git sparse-checkout set packages/agent-skills
git fetch --depth=1 origin "$NEWSHA" && git checkout FETCH_HEAD

# 2. Replace skill directories
DEST=/home/tchow/.claude/plugins/marketplaces/tchow-essentials/plugins/netsuite-oracle-skills
rm -rf "$DEST/skills"
mkdir -p "$DEST/skills"
for skill in netsuite-ai-connector-instructions netsuite-owasp-secure-coding \
  netsuite-sdf-project-documentation netsuite-sdf-roles-and-permissions \
  netsuite-suitescript-records-reference netsuite-suitescript-upgrade \
  netsuite-uif-spa-reference; do
  cp -r /tmp/ns-vendor/packages/agent-skills/$skill "$DEST/skills/"
done
cp /tmp/ns-vendor/LICENSE.txt "$DEST/LICENSE.upstream"

# 3. Update this file: Pinned commit, Commit date, Vendor date, Integrity baseline
# 4. Bump plugin.json version
# 5. Update marketplace.json version entry
# 6. Commit: feat(netsuite-oracle-skills): refresh Oracle agent-skills @ <NEWSHA>
```

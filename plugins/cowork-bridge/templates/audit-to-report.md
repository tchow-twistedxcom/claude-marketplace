# Template: Security Audit → Client Report

This document instructs Claude Cowork on how to transform a Claude Code security audit
into a polished client-facing report.

---

## Your Task

You have been handed off a security audit artifact. Your goal is to produce a professional,
client-ready report suitable for an executive audience.

## Step 1: Read the Artifact Files

Read the following files from the artifact folder (paths provided in your prompt):

1. **`metadata.json`** — Start here. Contains: client name, project scope, audit date, severity
   summary counts, engagement context.
2. **`analysis.md`** — Detailed findings: vulnerability descriptions, affected components,
   reproduction steps, severity ratings, evidence references.
3. **`data.json`** — Structured evidence: raw findings array, CVE references, CVSS scores,
   affected endpoints/scripts, remediation recommendations.

## Step 2: Produce the Report

Create a DOCX (or PDF if DOCX unavailable) with the following structure:

### Cover Page
- Client name and logo placeholder
- Report title: "Security Audit Report — [Project Name]"
- Date: [audit date from metadata.json]
- Prepared by: TwistedX / Claude Code AI Analysis

### Executive Summary (1 page, non-technical)
- What was assessed (scope)
- Overall risk posture (1–2 sentences)
- Critical finding count, high count, medium count, low count
- Top 3 recommended actions
- Tone: confident, clear, no jargon

### Scope & Methodology
- Systems and integrations assessed
- Audit approach (static analysis, API testing, configuration review)
- Limitations and out-of-scope items

### Findings Summary Table
| # | Finding | Severity | Status | CVSS |
|---|---------|----------|--------|------|
Each row: finding title, severity (Critical/High/Medium/Low), status (Open), CVSS score if available.

### Detailed Findings (one section per finding)
For each finding:
- **Title** (e.g., "Unencrypted credential storage in flow configurations")
- **Severity**: Critical / High / Medium / Low
- **Description**: What the vulnerability is (technical, 2–3 sentences)
- **Evidence**: Quote or reference from data.json
- **Business Impact**: What could go wrong if exploited (non-technical, 1–2 sentences)
- **Recommendation**: Specific remediation step

Order findings by severity (Critical first, then High, Medium, Low).

### Remediation Roadmap
Prioritized action table:
| Priority | Action | Effort | Timeline |
|----------|--------|--------|----------|
P1 = Critical findings (address within 30 days)
P2 = High findings (address within 60 days)
P3 = Medium/Low (address within 90 days or next sprint)

### Appendix
- Full data.json findings (formatted as table or code block)
- Tool versions or audit environment details (from metadata.json if present)

## Step 3: Save Output

Save the completed report to:
```
~/cowork-bridge/outbox/{date}-{project}-audit-report.docx
```
Where `{date}` = today's date (YYYYMMDD) and `{project}` = project name from metadata.json.

## Step 4: Write Completion Marker

After saving, write a brief summary to:
```
~/cowork-bridge/outbox/{artifact-id}-done.md
```
Content:
```markdown
# Handoff Complete

- **Artifact**: {artifact-id}
- **Completed**: {ISO timestamp}
- **Output**: outbox/{date}-{project}-audit-report.docx
- **Findings**: {N} total ({critical} critical, {high} high, {medium} medium, {low} low)
```

---

## Tone Guidelines

- **Executive Summary**: Non-technical, confident, action-oriented. Avoid CVE numbers and technical acronyms.
- **Detailed Findings**: Technical precision — developers and security engineers will read this section.
- **Remediation Roadmap**: Business language — "address within 30 days" not "patch immediately".
- **Overall**: Professional consulting report style. No casual language.

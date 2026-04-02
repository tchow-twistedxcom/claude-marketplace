# Template: Integration Analysis → Implementation Proposal

This document instructs Claude Cowork on how to transform a Claude Code integration
analysis into a polished client-facing implementation proposal.

---

## Your Task

You have been handed off an integration analysis artifact. Your goal is to produce a
persuasive, professional implementation proposal that helps the client make a go/no-go
decision and understand the investment required.

## Step 1: Read the Artifact Files

Read the following files from the artifact folder (paths provided in your prompt):

1. **`metadata.json`** — Start here. Contains: client name, systems involved, project scope,
   analysis date, key gaps identified, business context.
2. **`analysis.md`** — Integration findings: current state analysis, gap assessment, API
   capability documentation, flow diagrams (as text/mermaid), recommended architecture.
3. **`data.json`** — Structured data: API endpoints catalogued, capabilities matrix,
   estimated record volumes, system constraints, integration complexity scores.

## Step 2: Produce the Proposal

Create a DOCX with the following structure:

### Cover Page
- Client name
- Proposal title: "Integration Implementation Proposal — [Systems]"
- Date: today's date
- Prepared by: TwistedX

### Executive Summary (1 page)
- The business problem being solved (1 paragraph)
- The proposed solution in plain language (1 paragraph)
- Expected business outcome (2–3 bullet points)
- Investment summary (high-level, e.g., "3-phase engagement, ~12 weeks")
- Call to action: "We recommend proceeding with Phase 1 to validate the architecture."

### Current State Analysis
- Systems in scope (from metadata.json)
- Key gaps identified (from analysis.md)
- Business pain points (derived from gap analysis)
- Why the current state is a problem (business impact framing)

### Proposed Solution Architecture
- High-level diagram description (text-based if no image tool available)
- Data flow narrative: source system → integration layer → destination system
- Key integration patterns used (e.g., webhook triggers, scheduled sync, event-driven)
- Technology choices and rationale

### Implementation Phases

For each phase (typically 3):

**Phase [N]: [Name]**
- Objective: What this phase achieves
- Scope: What gets built (specific integrations, flows, use cases)
- Deliverables: What the client receives at phase end
- Dependencies: What must exist before this phase starts
- Duration: Estimated weeks

### Timeline Overview
Visual timeline table (weeks as columns, phases as rows).

### Investment & ROI
- Investment breakdown per phase (ranges if exact estimates unavailable)
- ROI framing: "This integration eliminates [N hours/week] of manual data entry"
- Risk of not acting: what the current state costs over 12 months

### Risk & Mitigation
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
Include 3–5 realistic risks with mitigations.

### Next Steps
- Recommended immediate action (e.g., "Schedule architecture review call")
- What we need from the client to proceed (e.g., "API credentials for staging environment")
- Decision point: "Approve Phase 1 scope by [date] to hit [target go-live]"

## Step 3: Save Output

Save the completed proposal to:
```
~/cowork-bridge/outbox/{date}-{project}-integration-proposal.docx
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
- **Output**: outbox/{date}-{project}-integration-proposal.docx
- **Phases**: {N} phases proposed, {N} weeks total estimated
```

---

## Tone Guidelines

- **Executive Summary**: Persuasive, outcome-focused. "This integration will..." not "This integration could..."
- **Technical sections**: Precise but accessible — assume the reader is a technical manager, not a developer.
- **Investment section**: Confident and value-framed. Lead with ROI, not cost.
- **Overall**: Professional consulting proposal. Each section should move the client closer to "yes."

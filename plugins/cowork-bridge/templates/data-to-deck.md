# Template: Data Analysis → Presentation Deck

This document instructs Claude Cowork on how to transform Claude Code data analysis
outputs into a polished slide deck outline for client presentations.

---

## Your Task

You have been handed off a data analysis artifact. Your goal is to produce a slide-by-slide
deck outline that a human can use to build the final presentation (in PowerPoint or Google Slides).

## Step 1: Read the Artifact Files

Read the following files from the artifact folder (paths provided in your prompt):

1. **`metadata.json`** — Start here. Contains: client name, data source, analysis scope,
   date range covered, key metrics, presentation context (e.g., "QBR", "board meeting").
2. **`analysis.md`** — Narrative analysis: trend interpretations, anomalies, key findings,
   recommendations, context and caveats.
3. **`data.json`** — Structured data: metrics arrays, time-series data, comparison tables,
   percentages, counts. The raw numbers that back the narrative.

## Step 2: Produce the Deck Outline

Create a DOCX with a slide-by-slide outline. For each slide, include:
- **Slide title**
- **Key message** (the one thing the audience should take away)
- **Content**: bullet points or data to include
- **Visualization type**: what chart/graphic would work best (e.g., "line chart", "bar chart", "data callout")
- **Speaker notes**: what to say aloud (2–4 sentences)

### Slide Structure

**Slide 1: Title**
- Title: "[Client Name] — [Topic] Review"
- Subtitle: "[Date range] | Prepared by TwistedX"
- Visual: client logo placeholder + clean background

**Slide 2: Agenda**
- 4–5 bullet points listing the sections
- Speaker notes: "Today we'll cover [summary]"

**Slide 3: Executive Summary / TL;DR**
- 3 key takeaways (the most important findings)
- Key metric callouts (large numbers, e.g., "+23% YoY")
- Visual: 3-column callout layout or summary table
- Speaker notes: "If you only remember 3 things from today..."

**Slides 4–N: Key Findings (one per major theme)**
For each significant finding from analysis.md:
- Title: The finding as a statement (e.g., "Order volume peaked in Q4 but declined 15% in Q1")
- Content: Supporting data points from data.json
- Visualization: The most appropriate chart type for this data
- Insight callout: "What this means for [client]"
- Speaker notes: Context, caveat if any, recommended action

**Slide N+1: Trends**
- Time-series comparison if applicable
- YoY or period-over-period delta
- Trend line description
- Speaker notes: "This trend suggests..."

**Slide N+2: Recommendations**
- 3–5 specific, actionable recommendations
- Each with: Action | Expected Impact | Priority
- Visual: prioritized action table
- Speaker notes: "Based on this data, we recommend..."

**Slide N+3: Next Steps**
- Immediate actions (this week)
- Short-term actions (next 30 days)
- Who owns what (if known from metadata.json)
- Speaker notes: "Before our next meeting..."

**Slide N+4: Appendix / Data Detail**
- Full data tables (from data.json)
- Methodology notes
- Data source and date range
- Speaker notes: "This appendix is available for reference"

## Step 3: Save Output

Save the completed deck outline to:
```
~/cowork-bridge/outbox/{date}-{project}-deck.docx
```
Where `{date}` = today's date (YYYYMMDD) and `{project}` = project name from metadata.json.

Note: If you have PPTX creation capability, create a `.pptx` instead and update the filename.

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
- **Output**: outbox/{date}-{project}-deck.docx
- **Slides**: {N} slides outlined ({N} key findings sections)
```

---

## Tone Guidelines

- **Title and summary slides**: High-level, confident, outcome-oriented.
- **Finding slides**: Data-first — let the numbers speak, add brief interpretation.
- **Recommendation slides**: Action-oriented. "Do X to achieve Y" not "Consider doing X."
- **Speaker notes**: Conversational, natural — written as if you're coaching the presenter.
- **Overall**: Executive presentation style. Each slide should have one key message. No walls of text.

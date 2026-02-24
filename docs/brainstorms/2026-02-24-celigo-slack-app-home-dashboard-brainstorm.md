---
title: Celigo Health Monitor Dashboard
date: 2026-02-24
status: decided
---

# Celigo Health Monitor Dashboard

## What We're Building

A persistent health monitoring dashboard for Celigo integrations, delivered via:
1. **Web dashboard** in the existing B2bDashboard app — full React UI with charts, historical data, drill-down, resolve/retry actions
2. **Slack App Home tab** — persistent Block Kit status board with action buttons and activity log
3. **Chat notifications** — existing Health Digest (Flow A) continues posting AI summaries to Slack channel

Inspired by [StatusPal's Status Center](https://www.statuspal.io/status-center/slack) for the Slack-side UX.

## Why This Approach

We evaluated three architectures:

| Approach | Verdict |
|----------|---------|
| **Celigo-only** (8 scripts, 3 flows, Block Kit dashboard) | Too complex, limited (no charts, no history, 100-block max, 2-5s latency) |
| **FOSS status page** (Uptime Kuma, Cachet) | Wrong fit — designed for URL uptime, not Celigo error counts |
| **Extend B2bDashboard** | Best fit — mature React+Express+MongoDB app already handles EDI integrations |

The B2bDashboard (`~/B2bDashboard`) is a production app with:
- React 18 + TypeScript + Vite + shadcn/ui + Tailwind
- Express.js backend with 46+ API endpoints
- MongoDB Atlas + Redis
- Docker Compose deployment
- Existing Slack webhook notification support
- WebSocket (Socket.IO) real-time updates
- Scheduled worker pattern (StatsAggregatorWorker with circuit breaker)

Extending it means: standard web dev, full debugging, historical data in MongoDB, charts, <1s Slack render, zero new infrastructure.

## Key Decisions

1. **Extend B2bDashboard** over building new Celigo flows or deploying FOSS tools
2. **B2bDashboard polls Celigo API directly** — zero changes to existing Celigo Flow A
3. **CeligoHealthWorker** runs on 60s interval with circuit breaker pattern (matches existing StatsAggregatorWorker)
4. **Slack App Home** via `views.publish` from the server (not Celigo hooks)
5. **Resolve/Retry from both web and Slack** — server calls Celigo API, logs activity, refreshes views
6. **Historical data in MongoDB** with TTL indexes (90-day snapshots, 30-day activity log)

## Resolved Questions

- Dashboard type: Slack App Home tab + full web dashboard (both)
- Backend host: B2bDashboard (existing app, no new infrastructure)
- FOSS status pages: Not a fit (URL monitoring ≠ Celigo error data)
- Celigo changes: None required (server polls API directly)
- Data persistence: MongoDB with TTL-based cleanup
- Real-time: WebSocket for web dashboard, views.publish for Slack on status change

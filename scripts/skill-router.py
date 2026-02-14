#!/usr/bin/env python3
"""
Skill Router - Auto-detects and activates relevant skills based on prompt content.

This hook analyzes the user's prompt and injects activation instructions
for any matching skills from the tchow-essentials marketplace.
"""
import json
import sys
import re
import subprocess
from pathlib import Path

# Claude-code skill auto-update script location
CLAUDE_CODE_UPDATE_SCRIPT = Path(__file__).parent.parent / 'plugins' / 'claudekit-skills' / 'skills' / 'claude-code' / 'scripts' / 'skill_autoupdate.py'

# Skill detection patterns and metadata
SKILLS = {
    # ============================================================
    # CLAUDE CODE & DEVELOPMENT TOOLS
    # ============================================================
    "claude-code": {
        "patterns": [
            r"\b(which|what)\s+(tool|agent)\b.*\b(should|use|best)\b",
            r"\b(read|edit|grep|glob|bash|multiedit)\b.*\b(vs|or|versus)\b",
            r"\b(task|subagent)\s+(type|agent)\b",
            r"\b(mcp|model\s*context\s*protocol)\b.*\b(server|config|setup)\b",
            r"\b(hook|hooks)\b.*\b(claude|code|setup|config)\b",
            r"\b(claude\s*code)\b.*\b(feature|how|can|does|configure)\b",
            r"\b(agent|agents)\b.*\b(parallel|orchestrat|select|choose)\b",
            r"\b(tool\s*selection|select.*tool)\b",
            r"\b(explore|plan|root-cause|code-reviewer)\s+agent\b",
            r"\benterpla?n\s*mode\b",
        ],
        "skill_name": "claudekit-skills:claude-code",
        "description": "Claude Code mastery (tool selection, 30+ agents, MCP servers, hooks, workflows)"
    },
    "mcp-builder": {
        "patterns": [
            r"\b(build|create|make)\b.*\b(mcp)\b.*\b(server)\b",
            r"\b(mcp)\b.*\b(server|tool)\b.*\b(build|create|implement)\b",
            r"\b(fastmcp|fast-mcp)\b",
            r"\b(model\s*context\s*protocol)\b.*\b(build|create|develop)\b",
            r"\b(mcp)\b.*\b(typescript|python)\b.*\b(server)\b",
        ],
        "skill_name": "claudekit-skills:mcp-builder",
        "description": "Build MCP servers (FastMCP Python, TypeScript SDK, tool design)"
    },
    "skill-creator": {
        "patterns": [
            r"\b(create|build|make)\b.*\b(skill)\b",
            r"\b(skill)\b.*\b(template|structure|format)\b",
            r"\b(write|design)\b.*\b(skill\.md|skill\s+file)\b",
            r"\b(skill)\b.*\b(best\s*practice|pattern)\b",
        ],
        "skill_name": "claudekit-skills:skill-creator",
        "description": "Create Claude Code skills (SKILL.md format, best practices, triggers)"
    },
    "repomix": {
        "patterns": [
            r"\b(repomix)\b",
            r"\b(pack|package)\b.*\b(repo|repository|codebase)\b.*\b(ai|llm|claude)\b",
            r"\b(codebase)\b.*\b(context|snapshot|export)\b.*\b(ai|llm)\b",
            r"\b(repository)\b.*\b(single\s*file|one\s*file)\b",
        ],
        "skill_name": "claudekit-skills:repomix",
        "description": "Pack repositories into AI-friendly single files for LLM context"
    },
    "docs-seeker": {
        "patterns": [
            r"\b(llms\.txt)\b",
            r"\b(find|search|get)\b.*\b(documentation|docs)\b.*\b(library|framework|package)\b",
            r"\b(latest|current)\b.*\b(docs|documentation)\b.*\b(for)\b",
            r"\b(documentation)\b.*\b(llm|ai\s*friendly)\b",
        ],
        "skill_name": "claudekit-skills:docs-seeker",
        "description": "Search documentation via llms.txt, GitHub repos, and parallel exploration"
    },

    # ============================================================
    # FRONTEND & UI FRAMEWORKS
    # ============================================================
    "nextjs": {
        "patterns": [
            r"\b(next\.?js|nextjs)\b",
            r"\b(app\s*router|pages\s*router)\b",
            r"\b(server\s*component|client\s*component|rsc)\b",
            r"\b(getServerSideProps|getStaticProps|generateStaticParams)\b",
            r"\b(next)\b.*\b(config|middleware|api\s*route)\b",
            r"\b(use\s*server|use\s*client)\b",
        ],
        "skill_name": "claudekit-skills:nextjs",
        "description": "Next.js framework (App Router, Server Components, data fetching, middleware)"
    },
    "tailwindcss": {
        "patterns": [
            r"\b(tailwind|tailwindcss)\b",
            r"\b(utility\s*class|utility-first)\b",
            r"\b(tw-|@apply)\b",
            r"\b(responsive)\b.*\b(sm:|md:|lg:|xl:)\b",
            r"\b(dark\s*mode|dark:)\b.*\b(tailwind|class)\b",
        ],
        "skill_name": "claudekit-skills:tailwindcss",
        "description": "Tailwind CSS (utility classes, responsive design, dark mode, custom themes)"
    },
    "shadcn-ui": {
        "patterns": [
            r"\b(shadcn|shadcn[-/]ui)\b",
            r"\b(radix)\b.*\b(ui|component)\b",
            r"\b(cn\s*\(|clsx)\b.*\b(component)\b",
            r"\b(button|dialog|dropdown|toast|form)\b.*\b(shadcn|radix)\b",
            r"\b(ui\s*component)\b.*\b(accessible|a11y)\b",
        ],
        "skill_name": "claudekit-skills:shadcn-ui",
        "description": "shadcn/ui components (Radix UI, accessible, copy-paste components)"
    },
    "remix-icon": {
        "patterns": [
            r"\b(remix[-\s]?icon|remixicon)\b",
            r"\b(ri-[a-z]+-line|ri-[a-z]+-fill)\b",
            r"\b(icon)\b.*\b(library|set)\b.*\b(react|vue|svg)\b",
        ],
        "skill_name": "claudekit-skills:remix-icon",
        "description": "RemixIcon library (3100+ icons, React/Vue/SVG, outlined/filled styles)"
    },
    "canvas-design": {
        "patterns": [
            r"\b(canvas)\b.*\b(design|art|poster|visual)\b",
            r"\b(create|make|generate)\b.*\b(poster|artwork|visual\s*design)\b",
            r"\b(png|pdf)\b.*\b(design|art|create)\b",
            r"\b(generative\s*art|algorithmic\s*art)\b",
        ],
        "skill_name": "claudekit-skills:canvas-design",
        "description": "Visual design and art creation (posters, PNG/PDF, canvas-based design)"
    },

    # ============================================================
    # MEDIA PROCESSING
    # ============================================================
    "ffmpeg": {
        "patterns": [
            r"\b(ffmpeg|ffprobe)\b",
            r"\b(convert|encode|decode|transcode)\b.*\b(video|audio|mp4|mp3|mkv|avi|wav)\b",
            r"\b(video|audio)\b.*\b(compress|extract|merge|split|trim|cut)\b",
            r"\b(stream|codec|bitrate|framerate|fps)\b.*\b(video|audio)\b",
            r"\b(subtitle|caption)\b.*\b(extract|embed|burn)\b",
            r"\b(gif)\b.*\b(create|convert|from\s*video)\b",
        ],
        "skill_name": "claudekit-skills:ffmpeg",
        "description": "FFmpeg media processing (video/audio conversion, encoding, streaming, filters)"
    },
    "imagemagick": {
        "patterns": [
            r"\b(imagemagick|magick|convert)\b.*\b(image)\b",
            r"\b(image)\b.*\b(resize|crop|rotate|compress|convert|watermark)\b",
            r"\b(png|jpg|jpeg|gif|webp|svg|tiff)\b.*\b(convert|resize|optimize)\b",
            r"\b(batch)\b.*\b(image|photo)\b.*\b(process|convert)\b",
            r"\b(thumbnail|montage|composite)\b.*\b(image)\b",
        ],
        "skill_name": "claudekit-skills:imagemagick",
        "description": "ImageMagick image processing (resize, convert, crop, watermark, batch ops)"
    },

    # ============================================================
    # AUTHENTICATION & SECURITY
    # ============================================================
    "better-auth": {
        "patterns": [
            r"\b(better[-\s]?auth)\b",
            r"\b(auth|authentication)\b.*\b(typescript|framework|library)\b",
            r"\b(oauth|oauth2|oidc)\b.*\b(implement|setup|configure)\b",
            r"\b(2fa|two[-\s]?factor|totp|passkey)\b.*\b(auth|implement)\b",
            r"\b(session|jwt|token)\b.*\b(auth|management)\b",
            r"\b(social\s*login|google\s*auth|github\s*auth)\b",
        ],
        "skill_name": "claudekit-skills:better-auth",
        "description": "Better Auth framework (TypeScript auth, OAuth, 2FA, passkeys, sessions)"
    },

    # ============================================================
    # MONOREPO & BUILD TOOLS
    # ============================================================
    "turborepo": {
        "patterns": [
            r"\b(turborepo|turbo)\b",
            r"\b(monorepo)\b.*\b(build|cache|pipeline)\b",
            r"\b(workspace|workspaces)\b.*\b(npm|pnpm|yarn)\b.*\b(monorepo)\b",
            r"\b(turbo\.json)\b",
            r"\b(remote\s*cache|build\s*cache)\b.*\b(monorepo)\b",
        ],
        "skill_name": "claudekit-skills:turborepo",
        "description": "Turborepo monorepo management (build pipelines, caching, workspaces)"
    },

    # ============================================================
    # BROWSER & E2E TESTING
    # ============================================================
    "e2e-testing": {
        "patterns": [
            r"\b(e2e|end[-\s]?to[-\s]?end)\b.*\b(test|testing)\b",
            r"\b(playwright|puppeteer|cypress)\b.*\b(test)\b",
            r"\b(browser)\b.*\b(test|automation|automate)\b",
            r"\b(visual\s*regression|screenshot\s*test)\b",
            r"\b(test)\b.*\b(user\s*flow|login\s*flow|checkout)\b",
        ],
        "skill_name": "chrome-devtools:e2e-testing-patterns",
        "description": "E2E browser testing patterns (Playwright, user flows, visual testing)"
    },

    # ============================================================
    # ENTERPRISE INTEGRATIONS
    # ============================================================
    "atlassian-skills": {
        "patterns": [
            r"\b(jira|confluence)\b",
            r"\b(ticket|issue|sprint|backlog)\b",
            r"\b(wiki|page|space)\b",
            r"\b(atlassian|jql|cql)\b",
            r"\bcreate\s+(a\s+)?(confluence|jira|ticket|page|issue)\b",
            r"\b(document|documentation)\b.*\b(confluence|wiki)\b",
        ],
        "skill_name": "atlassian-skills:atlassian-api",
        "description": "Atlassian Confluence/Jira operations (pages, issues, search, JQL)"
    },
    "shopify-workflows": {
        "patterns": [
            r"\b(shopify)\b",
            r"\b(store|storefront)\b.*\b(product|order|customer)\b",
            r"\b(product|order|collection|discount|theme)\b.*\b(shopify|store)\b",
            r"\b(e-?commerce|graphql)\b.*\b(admin|api)\b",
            r"\b(merchant|inventory|fulfillment)\b",
        ],
        "skill_name": "shopify-workflows:shopify-developer",
        "description": "Shopify Admin API (products, orders, discounts, GraphQL)"
    },
    "netsuite-sdf-deployment": {
        "patterns": [
            r"\b(twx[-\s]?deploy|netsuite[-\s]?deploy)\b",
            r"\b(@twisted-x/netsuite-deploy)\b",
            r"\b(sdf|suitecloud)\b.*\b(deploy|bundle|project)\b",
            r"\b(certificate.*auth|tba|machine[-\s]?to[-\s]?machine)\b",
            r"\b(authid|auth[-\s]?id|ci[-\s]?passkey)\b",
            r"\b(monorepo|multi[-\s]?project)\b.*\b(deploy|sdf|netsuite)\b",
            r"\b(github.*action|ci/cd)\b.*\b(netsuite|sdf)\b",
            r"\b(twx-sdf\.config|\.sdfcli\.json|project\.json)\b",
            r"\b(credential.*refresh|stale.*credential)\b",
            r"\b(deploy|bundle)\b.*\b(netsuite|sdf)\b",
        ],
        "skill_name": "netsuite-skills:netsuite-sdf-deployment",
        "description": "NetSuite SDF deployment (twx-deploy, CI/CD, TBA auth, monorepo)"
    },
    "netsuite-suiteql": {
        "patterns": [
            r"\b(suiteql)\b",
            r"\b(execute|test|run)\b.*\b(query)\b.*\b(netsuite)\b",
            r"\b(netsuite)\b.*\b(query|data)\b",
            r"\b(record\s*display)\b.*\b(query|data)\b",
            r"\b(transaction.*chain|flowchart.*data)\b",
            r"\b(suitescript)\b.*\b(query|search)\b",
            r"\b(saved\s*search|workflow|script)\b.*\b(netsuite|erp)\b",
        ],
        "skill_name": "netsuite-skills:netsuite-suiteql",
        "description": "NetSuite SuiteQL queries (Record Display, data validation, saved searches)"
    },
    "netsuite-file-cabinet": {
        "patterns": [
            r"\b(upload|find|search)\b.*\b(file|script)\b.*\b(netsuite|file\s*cabinet)\b",
            r"\b(netsuite)\b.*\b(file\s*cabinet|upload|find\s*file)\b",
            r"\b(fileCreate|fileUpdate|fileGet)\b",
            r"\b(deploy|push)\b.*\b(script|suitescript)\b.*\b(prod|production|sandbox)\b",
            r"\b(folder[-\s]?id)\b.*\b(netsuite)\b",
        ],
        "skill_name": "netsuite-skills:netsuite-file-cabinet",
        "description": "NetSuite File Cabinet (upload, find, list files)"
    },
    "netsuite-script-deployments": {
        "patterns": [
            r"\b(script)\b.*\b(deployment|deployed|active|inactive)\b",
            r"\b(list|check|find)\b.*\b(deployment)\b",
            r"\b(user\s*event|restlet|suitelet|scheduled)\b.*\b(deployment|deployed)\b",
            r"\b(active[-\s]?only|isdeployed)\b",
            r"\b(record[-\s]?type)\b.*\b(script|deployment)\b",
            r"\b(which\s*script|wrong\s*script|inactive\s*script)\b",
        ],
        "skill_name": "netsuite-skills:netsuite-script-deployments",
        "description": "NetSuite script deployments (active/inactive, record types)"
    },
    "netsuite-debugger": {
        "patterns": [
            r"\b(INVALID_RCRD_TYPE|UNEXPECTED_ERROR|INSUFFICIENT_PERMISSION)\b",
            r"\b(netsuite)\b.*\b(error|fail|invalid|debug|troubleshoot)\b",
            r"\b(gateway|multi[-\s]?tenant)\b.*\b(routing|environment)\b",
            r"\b(environment)\b.*\b(routing|mismatch|header)\b",
            r"\b(record\s*type)\b.*\b(invalid|not\s*found|missing)\b",
            r"\b(X-NetSuite-Environment|sandbox2|sb2)\b.*\b(header|routing)\b",
            r"\b(deployment)\b.*\b(verify|check)\b.*\b(netsuite|sb2)\b",
        ],
        "skill_name": "netsuite-debugger",
        "description": "NetSuite API Gateway debugging (environment routing, multi-tenant, error diagnosis)"
    },
    "pri-container-tracking": {
        "patterns": [
            r"\b(pri|prolecto)\b",
            r"\b(container|freight|vessel)\b.*\b(tracking|status|lock|sync)\b",
            r"\b(queue.*stuck|stuck.*queue|dates.*not.*syncing)\b",
            r"\b(application.*setting)\b.*\b(pri|container|netsuite)\b",
            r"\b(landed.*cost|lc.*template|allocation)\b",
            r"\b(production.*po|blanket.*po|item.*version)\b",
            r"\b(ir.*to.*linker|container.*distribution)\b",
            r"\b(bundle\s*125246|bundle\s*132118|bundle\s*168443)\b",
        ],
        "skill_name": "netsuite-skills:pri-container-tracking",
        "description": "PRI Container Tracking (logistics, PPO, landed cost, app settings)"
    },
    "netsuite-cre2": {
        "patterns": [
            r"\b(cre[-\s]?2|cre2|cre\s*2\.0)\b",
            r"\b(content\s*renderer)\b",
            r"\b(freemarker)\b.*\b(template|netsuite)\b",
            r"\b(pdf\s*template|html\s*template)\b.*\b(netsuite)\b",
            r"\b(customer\s*statement)\b.*\b(pdf|template|generate)\b",
            r"\b(email\s*template)\b.*\b(netsuite|freemarker)\b",
            r"\b(document\s*generation)\b.*\b(netsuite)\b",
            r"\b(prolecto)\b.*\b(template|cre|render)\b",
            r"\b(render)\b.*\b(pdf|html)\b.*\b(netsuite)\b",
            r"\b(customrecord_cre2|customrecord_pri_cre2)\b",
            r"\b(netsuite)\b.*\b(statement|invoice|credit\s*letter)\b.*\b(template|pdf)\b",
        ],
        "skill_name": "netsuite-skills:netsuite-cre2",
        "description": "CRE 2.0 document generation (FreeMarker templates, PDF/HTML, SuiteQL data sources)"
    },
    "celigo-integration": {
        "patterns": [
            r"\b(celigo)\b",
            r"\b(integrator\.io)\b",
            r"\b(integration|integrator)\b.*\b(flow|connector)\b",
            r"\b(data\s*sync|etl|ipaas)\b",
            r"\b(flow|export|import)\b.*\b(celigo|integration)\b",
            r"\b(connection|mapping)\b.*\b(integration)\b",
            r"\b(lookup\s*cache|script|hook)\b.*\b(integration)\b",
            r"\b(job|error)\b.*\b(celigo|integration)\b",
        ],
        "skill_name": "celigo-integration:celigo-integrator",
        "description": "Celigo Integrator.io REST API (full CRUD for integrations, flows, connections, jobs, errors, scripts, lookups)"
    },
    "plytix-skills": {
        "patterns": [
            r"\b(plytix)\b",
            r"\b(pim)\b.*\b(product|asset|catalog)\b",
            r"\b(product\s*information\s*management)\b",
            r"\b(product)\b.*\b(catalog|attribute|variant)\b.*\b(manage|create|update)\b",
            r"\b(digital\s*asset)\b.*\b(manage|upload|product)\b",
            r"\b(sku|gtin|ean|upc)\b.*\b(product|catalog)\b",
        ],
        "skill_name": "plytix-skills:plytix-api",
        "description": "Plytix PIM operations (products, assets, categories, variants, attributes)"
    },
    "ninjaone-skills": {
        "patterns": [
            r"\b(ninjaone|ninja\s*one|ninjarmm|ninja\s*rmm)\b",
            r"\b(rmm)\b.*\b(device|endpoint|monitor|agent)\b",
            r"\b(remote\s*monitoring)\b.*\b(management|device)\b",
            r"\b(it\s*management)\b.*\b(device|endpoint|patch|alert)\b",
            r"\b(msp)\b.*\b(device|endpoint|ticket|alert)\b",
            r"\b(endpoint)\b.*\b(monitor|manage|patch|alert)\b",
        ],
        "skill_name": "ninjaone-skills:ninjaone-api",
        "description": "NinjaOne RMM operations (devices, alerts, patches, ticketing, management)"
    },
    "m365-skills": {
        "patterns": [
            r"\b(azure\s*ad|entra\s*id|entra|azure\s*active\s*directory)\b",
            r"\b(microsoft\s*365|m365|office\s*365|o365)\b.*\b(user|group|directory)\b",
            r"\b(aad)\b.*\b(user|group|device|directory)\b",
            r"\b(graph\s*api)\b.*\b(user|group|device)\b",
            r"\b(tenant)\b.*\b(user|group|directory|license)\b",
            r"\b(entra)\b.*\b(user|group|device|role)\b",
            r"\b(directory\s*role|admin\s*role)\b.*\b(azure|entra|m365)\b",
        ],
        "skill_name": "m365-skills:azure-ad",
        "description": "Azure AD/Entra ID operations (users, groups, devices, directory, licenses)"
    },
    "amazon-spapi": {
        "patterns": [
            r"\b(amazon)\b.*\b(sp[-\s]?api|selling\s*partner)\b",
            r"\b(amazon)\b.*\b(vendor|seller)\b.*\b(api|order|ship|invoice)\b",
            r"\b(vendor\s*central|seller\s*central)\b.*\b(api|order|report)\b",
            r"\b(amazon)\b.*\b(po|purchase\s*order|asn|invoice)\b",
            r"\b(amazon)\b.*\b(catalog|listing|inventory|fulfillment)\b",
            r"\b(amazon)\b.*\b(report|feed|notification)\b",
            r"\b(lwa|login\s*with\s*amazon)\b.*\b(oauth|auth)\b",
            r"\b(asin|fnsku|msku)\b.*\b(amazon)\b",
        ],
        "skill_name": "amazon-spapi:spapi-integration-patterns",
        "description": "Amazon SP-API (Vendor/Seller orders, shipments, catalog, inventory, reports, feeds)"
    },
    "mimecast-skills": {
        "patterns": [
            r"\b(mimecast)\b",
            r"\b(email\s*security)\b.*\b(protection|gateway|filter)\b",
            r"\b(ttp)\b.*\b(url|attachment|protection)\b",
            r"\b(targeted\s*threat\s*protection)\b",
            r"\b(held\s*message|quarantine)\b.*\b(email)\b",
            r"\b(blocked\s*sender|permitted\s*sender)\b",
            r"\b(email)\b.*\b(policy|audit|siem)\b",
            r"\b(anti[-\s]?phishing|anti[-\s]?malware)\b.*\b(email)\b",
        ],
        "skill_name": "mimecast-skills:mimecast-api",
        "description": "Mimecast email security (TTP, held messages, policies, SIEM integration)"
    },

    # ============================================================
    # WORKFLOW AUTOMATION (n8n)
    # ============================================================
    "n8n-workflow-manager": {
        "patterns": [
            r"\b(n8n)\b.*\b(workflow|upload|import|update|manage)\b",
            r"\b(upload|import|update)\b.*\b(workflow)\b.*\b(n8n)\b",
            r"\b(n8n)\b.*\b(api|deploy|sync)\b",
            r"\b(workflow)\b.*\b(n8n)\b.*\b(json|file)\b",
        ],
        "skill_name": "n8n-integration:n8n-workflow-manager",
        "description": "n8n workflow management (upload, import, update, sync workflows)"
    },
    "n8n-workflow-builder": {
        "patterns": [
            r"\b(build|create|design)\b.*\b(n8n)\b.*\b(workflow)\b",
            r"\b(n8n)\b.*\b(workflow)\b.*\b(build|create|new)\b",
            r"\b(n8n)\b.*\b(node|trigger|action)\b.*\b(add|configure)\b",
            r"\b(automation)\b.*\b(n8n)\b.*\b(workflow)\b",
        ],
        "skill_name": "n8n-integration:n8n-workflow-builder",
        "description": "n8n workflow creation (build new workflows, configure nodes, triggers)"
    },
    "n8n-troubleshooter": {
        "patterns": [
            r"\b(n8n)\b.*\b(error|fail|issue|problem|debug|troubleshoot)\b",
            r"\b(troubleshoot|debug|fix)\b.*\b(n8n)\b",
            r"\b(n8n)\b.*\b(execution|webhook|trigger)\b.*\b(not\s*working|broken|fail)\b",
            r"\b(n8n)\b.*\b(log|stuck|timeout)\b",
        ],
        "skill_name": "n8n-integration:n8n-troubleshooter",
        "description": "n8n troubleshooting (debug errors, webhook issues, execution failures)"
    },
    "n8n-integration-patterns": {
        "patterns": [
            r"\b(n8n)\b",
            r"\b(workflow\s*automation)\b.*\b(platform|tool)\b",
            r"\b(n8n)\b.*\b(pattern|best\s*practice|example)\b",
            r"\b(data\s*table|credential|connection)\b.*\b(n8n)\b",
        ],
        "skill_name": "n8n-integration:n8n-integration-patterns",
        "description": "n8n patterns and best practices (integrations, data tables, credentials)"
    },

    # ============================================================
    # DEBUGGING & PROBLEM SOLVING
    # ============================================================
    "debugging-systematic": {
        "patterns": [
            r"\b(debug|debugging)\b.*\b(systematic|methodical|approach)\b",
            r"\b(systematic)\b.*\b(debug|troubleshoot|diagnose)\b",
            r"\b(bug|error|issue)\b.*\b(systematic|step[-\s]?by[-\s]?step)\b",
            r"\b(root\s*cause)\b.*\b(analysis|trace|find)\b",
            r"\b(defense\s*in\s*depth)\b",
            r"\b(verification)\b.*\b(before\s*completion|complete)\b",
        ],
        "skill_name": "claudekit-skills:debugging/systematic-debugging",
        "description": "Systematic debugging approach (root cause, defense in depth, verification)"
    },
    "problem-solving": {
        "patterns": [
            r"\b(stuck|blocked)\b.*\b(how|what|help)\b",
            r"\b(problem[-\s]?solving)\b.*\b(technique|approach|method)\b",
            r"\b(inversion)\b.*\b(thinking|exercise|approach)\b",
            r"\b(collision\s*zone|scale\s*game)\b",
            r"\b(simplification)\b.*\b(cascade|approach)\b",
            r"\b(meta[-\s]?pattern)\b.*\b(recognition)\b",
            r"\b(think|approach)\b.*\b(different|creative|lateral)\b",
        ],
        "skill_name": "claudekit-skills:problem-solving/when-stuck",
        "description": "Problem-solving techniques (inversion, collision zone, simplification, meta-patterns)"
    },

    # ============================================================
    # DOCUMENT PROCESSING
    # ============================================================
    "document-docx": {
        "patterns": [
            r"\b(docx|word\s*document)\b.*\b(create|edit|read|convert|export)\b",
            r"\b(create|generate|make)\b.*\b(docx|word\s*document)\b",
            r"\b(microsoft\s*word|ms\s*word)\b.*\b(file|document)\b",
            r"\b(tracked\s*changes|comments)\b.*\b(document|word)\b",
        ],
        "skill_name": "claudekit-skills:document-skills/docx",
        "description": "Word document processing (create, edit, tracked changes, comments)"
    },
    "document-xlsx": {
        "patterns": [
            r"\b(xlsx|excel|spreadsheet)\b.*\b(create|edit|read|analyze|formula)\b",
            r"\b(create|generate|make)\b.*\b(xlsx|excel|spreadsheet)\b",
            r"\b(formula|pivot|chart)\b.*\b(excel|spreadsheet)\b",
            r"\b(csv|tsv)\b.*\b(import|export|convert)\b.*\b(excel)\b",
        ],
        "skill_name": "claudekit-skills:document-skills/xlsx",
        "description": "Excel/spreadsheet processing (formulas, charts, data analysis, CSV import)"
    },
    "document-pptx": {
        "patterns": [
            r"\b(pptx|powerpoint|presentation)\b.*\b(create|edit|read|slide)\b",
            r"\b(create|generate|make)\b.*\b(pptx|powerpoint|presentation|slides)\b",
            r"\b(slide)\b.*\b(deck|presentation|template)\b",
            r"\b(speaker\s*notes)\b.*\b(presentation)\b",
        ],
        "skill_name": "claudekit-skills:document-skills/pptx",
        "description": "PowerPoint/presentation processing (create, edit, layouts, speaker notes)"
    },
    "document-pdf": {
        "patterns": [
            r"\b(pdf)\b.*\b(create|edit|read|fill|merge|split|extract)\b",
            r"\b(create|generate|make)\b.*\b(pdf)\b",
            r"\b(pdf\s*form)\b.*\b(fill|create|extract)\b",
            r"\b(merge|split|combine)\b.*\b(pdf)\b",
            r"\b(extract)\b.*\b(text|table|image)\b.*\b(pdf)\b",
        ],
        "skill_name": "claudekit-skills:document-skills/pdf",
        "description": "PDF processing (create, fill forms, merge, split, extract text/tables)"
    },

    # ============================================================
    # GOOGLE AI & AGENTS
    # ============================================================
    "google-adk": {
        "patterns": [
            r"\b(google\s*adk|agent\s*development\s*kit)\b",
            r"\b(google)\b.*\b(agent|adk)\b.*\b(python|build|create)\b",
            r"\b(vertex\s*ai)\b.*\b(agent)\b",
            r"\b(gemini)\b.*\b(agent|function|tool)\b",
        ],
        "skill_name": "claudekit-skills:google-adk-python",
        "description": "Google Agent Development Kit (agents, Gemini integration, Vertex AI)"
    },

    # ============================================================
    # COMPOUND ENGINEERING WORKFLOWS
    # ============================================================
    "compound-brainstorm": {
        "patterns": [
            r"\b(let'?s\s*brainstorm)\b",
            r"\b(brainstorm)\b.*\b(feature|idea|approach|requirement)\b",
            r"\b(help\s*me\s*think\s*through)\b",
            r"\b(what\s*should\s*we\s*build)\b",
            r"\b(explore\s*approaches)\b",
            r"\b(multiple\s*valid\s*interpretations)\b",
        ],
        "skill_name": "compound-engineering:workflows:brainstorm",
        "description": "Compound brainstorming (explore WHAT to build before planning HOW)"
    },
    "compound-plan": {
        "patterns": [
            r"\b(plan)\b.*\b(feature|implementation|project|build)\b",
            r"\b(create|write|make)\b.*\b(plan|implementation\s*plan)\b",
            r"\b(implementation)\b.*\b(plan|strategy|roadmap)\b",
            r"\b(break\s*down)\b.*\b(feature|task|project)\b",
            r"\b(how\s*should\s*we\s*implement)\b",
        ],
        "skill_name": "compound-engineering:workflows:plan",
        "description": "Compound planning (structured implementation plans with research)"
    },
    "compound-review": {
        "patterns": [
            r"\b(review)\b.*\b(code|pr|pull\s*request|branch|changes)\b",
            r"\b(code\s*review)\b",
            r"\b(multi[-\s]?agent)\b.*\b(review)\b",
            r"\b(check)\b.*\b(security|performance|architecture)\b.*\b(code|pr)\b",
            r"\b(review)\b.*\b(before\s*merge|before\s*pushing)\b",
        ],
        "skill_name": "compound-engineering:workflows:review",
        "description": "Compound review (15+ parallel agents: security, performance, architecture, etc.)"
    },
    "compound-work": {
        "patterns": [
            r"\b(execute|implement)\b.*\b(plan|feature)\b.*\b(worktree|parallel|quality)\b",
            r"\b(start\s*working)\b.*\b(plan)\b",
            r"\b(build\s*the\s*plan)\b",
            r"\b(work\s*on)\b.*\b(plan|implementation)\b.*\b(now|start)\b",
        ],
        "skill_name": "compound-engineering:workflows:work",
        "description": "Compound work execution (implement plans with worktrees, quality gates)"
    },
    "compound-compound": {
        "patterns": [
            r"\b(that\s*worked|it'?s\s*fixed|problem\s*solved)\b",
            r"\b(document)\b.*\b(solution|fix|what\s*we\s*learned)\b",
            r"\b(compound)\b.*\b(knowledge|learning|solution)\b",
            r"\b(capture)\b.*\b(solution|learning|insight)\b",
            r"\b(save)\b.*\b(solution|learning)\b.*\b(future)\b",
        ],
        "skill_name": "compound-engineering:workflows:compound",
        "description": "Compound knowledge capture (document solved problems for future reuse)"
    },
    "compound-swarm": {
        "patterns": [
            r"\b(swarm)\b.*\b(agent|mode|parallel)\b",
            r"\b(multi[-\s]?agent)\b.*\b(orchestrat|parallel|team)\b",
            r"\b(parallel)\b.*\b(agent|execution|task)\b",
            r"\b(spawn|launch)\b.*\b(agent|team|swarm)\b",
            r"\b(lfg|slfg)\b",
        ],
        "skill_name": "compound-engineering:workflows:work",
        "description": "Compound swarm orchestration (parallel multi-agent execution)"
    },
    "compound-resolve-pr": {
        "patterns": [
            r"\b(resolve|fix|address)\b.*\b(pr|pull\s*request)\b.*\b(comment|feedback|review)\b",
            r"\b(pr\s*comment|review\s*comment)\b.*\b(resolve|fix|address)\b",
            r"\b(resolve)\b.*\b(todo|todos)\b.*\b(parallel)\b",
        ],
        "skill_name": "compound-engineering:resolve_todo_parallel",
        "description": "Compound parallel resolution (fix PR comments and TODOs in parallel)"
    },
    "compound-deepen": {
        "patterns": [
            r"\b(deepen|enhance|enrich)\b.*\b(plan)\b",
            r"\b(research)\b.*\b(plan|each\s*section)\b",
            r"\b(plan)\b.*\b(more\s*detail|deeper|research)\b",
        ],
        "skill_name": "compound-engineering:deepen-plan",
        "description": "Compound plan deepening (parallel research agents enhance each plan section)"
    },
    "compound-gemini-image": {
        "patterns": [
            r"\b(gemini)\b.*\b(image|generate|edit)\b",
            r"\b(generate|create|make)\b.*\b(image)\b.*\b(gemini|google)\b",
            r"\b(ai\s*image)\b.*\b(generat|edit|composi)\b",
        ],
        "skill_name": "compound-engineering:gemini-imagegen",
        "description": "Gemini AI image generation (text-to-image, editing, multi-turn refinement)"
    },
    "compound-git-worktree": {
        "patterns": [
            r"\b(worktree|work[-\s]?tree)\b",
            r"\b(parallel)\b.*\b(branch|development|feature)\b",
            r"\b(isolated)\b.*\b(branch|development)\b",
        ],
        "skill_name": "compound-engineering:git-worktree",
        "description": "Git worktree management (parallel isolated development branches)"
    },

    # ============================================================
    # PORTABLE CONFIGURATION
    # ============================================================
    "portable-setup": {
        "patterns": [
            r"\b(portable[-\s]?setup)\b",
            r"\b(export|sync|import)\b.*\b(claude\s*code)\b.*\b(config|settings|setup)\b",
            r"\b(claude\s*code)\b.*\b(config|settings)\b.*\b(export|sync|backup)\b",
            r"\b(dotfiles)\b.*\b(claude|sync)\b",
            r"\b(tarball)\b.*\b(config|setup)\b",
        ],
        "skill_name": "portable-setup:portable-setup",
        "description": "Claude Code configuration portability (export, sync, backup settings)"
    },
}


def detect_skills(prompt: str) -> list:
    """Detect which skills are relevant based on prompt content."""
    prompt_lower = prompt.lower()
    detected = []

    for skill_id, config in SKILLS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, prompt_lower):
                detected.append({
                    "id": skill_id,
                    "name": config["skill_name"],
                    "description": config["description"]
                })
                break  # Only match once per skill

    return detected


def spawn_claude_code_update_check():
    """
    Spawn background update check for claude-code skill.

    This runs asynchronously and doesn't block skill activation.
    Uses stale-while-revalidate pattern for minimal latency.
    """
    if not CLAUDE_CODE_UPDATE_SCRIPT.exists():
        return

    try:
        subprocess.Popen(
            [sys.executable, str(CLAUDE_CODE_UPDATE_SCRIPT), '--check'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception:
        # Silently fail - don't block skill activation
        pass


def build_activation_context(detected_skills: list) -> str:
    """Build the activation instruction context."""
    if not detected_skills:
        return ""

    # Build skill list
    skill_list = "\n".join([
        f"  - **{s['name']}**: {s['description']}"
        for s in detected_skills
    ])

    # Build evaluation checklist
    eval_checklist = "\n".join([
        f"  - [ ] {s['name']}: YES/NO - [reason]"
        for s in detected_skills
    ])

    # Build activation calls
    activation_calls = "\n".join([
        f'  - Skill(skill="{s["name"]}")'
        for s in detected_skills
    ])

    context = f"""
<skill-router-detected>
## Detected Relevant Skills

{skill_list}

---

## MANDATORY SKILL ACTIVATION PROTOCOL

**Step 1 - EVALUATE**: For each detected skill, state YES/NO with reason:
{eval_checklist}

**Step 2 - ACTIVATE**: For each YES skill, use the Skill tool NOW:
{activation_calls}

**Step 3 - IMPLEMENT**: Only proceed with implementation AFTER skill activation completes.

---

**CRITICAL**: The evaluation is WORTHLESS unless you ACTIVATE the skills.
Do NOT skip Step 2. Do NOT proceed to implementation without activation.
</skill-router-detected>
"""
    return context.strip()


def main():
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)
        prompt = input_data.get("prompt", "")

        if not prompt:
            sys.exit(0)

        # Detect relevant skills
        detected = detect_skills(prompt)

        if not detected:
            # No skills detected, pass through
            sys.exit(0)

        # Spawn background update check if claude-code skill detected
        if any(s['id'] == 'claude-code' for s in detected):
            spawn_claude_code_update_check()

        # Build activation context
        context = build_activation_context(detected)

        # Output structured response
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context
            }
        }

        print(json.dumps(output))
        sys.exit(0)

    except json.JSONDecodeError:
        # No valid JSON input, pass through
        sys.exit(0)
    except Exception as e:
        # Log error but don't block
        print(f"skill-router error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()

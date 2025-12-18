#!/usr/bin/env python3
"""
Skill Router - Auto-detects and activates relevant skills based on prompt content.

This hook analyzes the user's prompt and injects activation instructions
for any matching skills from the tchow-essentials marketplace.
"""
import json
import sys
import re

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
    "netsuite-skills": {
        "patterns": [
            r"\b(netsuite)\b",
            r"\b(erp|suitescript|sdf|suiteql)\b",
            r"\b(invoice|purchase\s*order|vendor\s*bill)\b",
            r"\b(saved\s*search|workflow|script)\b.*\b(netsuite|erp)\b",
            r"\b(deploy|bundle)\b.*\b(netsuite|sdf)\b",
            r"\b(pri|prolecto|container)\b",
        ],
        "skill_name": "netsuite-skills:netsuite-sdf-deployment",
        "description": "NetSuite ERP (SuiteScript, SDF deployment, SuiteQL, Prolecto)"
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

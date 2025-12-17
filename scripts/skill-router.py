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
            r"\b(integration|integrator)\b.*\b(flow|connector)\b",
            r"\b(data\s*sync|etl|ipaas)\b",
            r"\b(flow|export|import)\b.*\b(celigo|integration)\b",
            r"\b(connection|mapping)\b.*\b(integration)\b",
        ],
        "skill_name": "celigo-integration:celigo-integration-patterns",
        "description": "Celigo iPaaS (integrations, flows, connections, data sync)"
    }
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

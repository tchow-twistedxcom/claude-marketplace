---
name: slack-messaging
description: "Guidance for composing well-formatted Slack messages using mrkdwn syntax. Use when writing, drafting, or formatting any Slack message."
---

# Slack Messaging Best Practices

Apply this skill whenever composing, drafting, or helping the user write a Slack message — including when using `slack_send_message`, `slack_send_message_draft`, or `slack_create_canvas`.

## Slack Formatting (mrkdwn)

Slack uses its own markup syntax called **mrkdwn**, which differs from standard Markdown:

| Format | Syntax | Notes |
|--------|--------|-------|
| Bold | `*text*` | Single asterisks, NOT double |
| Italic | `_text_` | Underscores |
| Strikethrough | `~text~` | Tildes |
| Code (inline) | `` `code` `` | Backticks |
| Code block | `` ```code``` `` | Triple backticks |
| Quote | `> text` | Angle bracket |
| Link | `<url\|display text>` | Pipe-separated in angle brackets |
| User mention | `<@U123456>` | User ID in angle brackets |
| Channel mention | `<#C123456>` | Channel ID in angle brackets |
| Bulleted list | `- item` or `• item` | Dash or bullet character |
| Numbered list | `1. item` | Number followed by period |

### Common Mistakes to Avoid

- Do NOT use `**bold**` (double asterisks) — Slack uses `*bold*` (single)
- Do NOT use `## headers` — Slack has no header syntax. Use `*bold text*` on its own line
- Do NOT use `[text](url)` for links — Slack uses `<url|text>`
- Do NOT use `---` for horizontal rules — Slack doesn't render these

## Message Structure Guidelines

- **Lead with the point.** Most important info in the first line (mobile notifications only show the first line).
- **Keep it short.** 1-3 short paragraphs. For longer content, use a Canvas.
- **Use line breaks generously.** Separate distinct thoughts with blank lines.
- **Use bullet points.** Anything with 3+ items should be a list.
- **Bold key information.** Use `*bold*` for names, dates, deadlines, and action items.

## Thread vs Channel Etiquette

- **Reply in threads** when responding to a specific message.
- **Use `reply_broadcast`** only when the reply contains info everyone needs.
- **Post in the channel** when starting a new topic, making an announcement, or asking a question.
- **Don't start a new thread** to continue an existing conversation — find and reply to the original.

## Tone and Audience

- Match the tone to the channel — `#general` is usually more formal than `#random`.
- Use emoji reactions for simple acknowledgments rather than reply messages.
- When writing announcements: context, key info, call to action.

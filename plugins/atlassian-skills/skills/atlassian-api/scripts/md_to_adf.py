#!/usr/bin/env python3
"""
Markdown to Atlassian Document Format (ADF) Converter

Converts Markdown text to ADF JSON format for Jira Cloud v3 API.
Handles: headings, paragraphs, bold, italic, code, links, lists, horizontal rules.

ADF Spec: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/
"""

import re


def md_to_adf(markdown_text):
    """
    Convert Markdown text to ADF document structure.

    Args:
        markdown_text: Markdown formatted string

    Returns:
        dict: ADF document structure ready for Jira API
    """
    lines = markdown_text.split('\n')
    content = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Code block (``` ... ```)
        if line.strip().startswith('```'):
            language = line.strip()[3:].strip() or None
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # Skip closing ```
            code = '\n'.join(code_lines)
            content.append(make_code_block(code, language))
            continue

        # Headings (# H1, ## H2, etc.)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            content.append(make_heading(text, level))
            i += 1
            continue

        # Horizontal rule (---, ***, ___)
        if re.match(r'^[-*_]{3,}\s*$', line):
            content.append({'type': 'rule'})
            i += 1
            continue

        # Unordered list (- item, * item)
        if re.match(r'^\s*[-*+]\s+', line):
            list_items = []
            while i < len(lines) and re.match(r'^\s*[-*+]\s+', lines[i]):
                item_text = re.sub(r'^\s*[-*+]\s+', '', lines[i])
                list_items.append(item_text)
                i += 1
            content.append(make_bullet_list(list_items))
            continue

        # Ordered list (1. item)
        if re.match(r'^\s*\d+\.\s+', line):
            list_items = []
            while i < len(lines) and re.match(r'^\s*\d+\.\s+', lines[i]):
                item_text = re.sub(r'^\s*\d+\.\s+', '', lines[i])
                list_items.append(item_text)
                i += 1
            content.append(make_ordered_list(list_items))
            continue

        # Regular paragraph (may span multiple lines)
        paragraph_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not is_block_start(lines[i]):
            paragraph_lines.append(lines[i])
            i += 1

        text = ' '.join(paragraph_lines)
        content.append(make_paragraph(text))

    return {
        'type': 'doc',
        'version': 1,
        'content': content
    }


def is_block_start(line):
    """Check if line starts a new block element."""
    return any([
        line.strip().startswith('#'),
        line.strip().startswith('```'),
        re.match(r'^\s*[-*+]\s+', line),
        re.match(r'^\s*\d+\.\s+', line),
        re.match(r'^[-*_]{3,}\s*$', line)
    ])


def parse_inline(text):
    """
    Parse inline Markdown formatting into ADF text nodes.

    Handles: **bold**, *italic*, `code`, [links](url)

    Returns:
        list: List of ADF content nodes
    """
    content = []

    # Pattern to match all inline elements
    # Order matters: longer patterns first
    pattern = r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))'

    parts = re.split(pattern, text)

    for part in parts:
        if not part:
            continue

        # Bold: **text**
        if part.startswith('**') and part.endswith('**'):
            inner = part[2:-2]
            content.append({
                'type': 'text',
                'text': inner,
                'marks': [{'type': 'strong'}]
            })
        # Italic: *text*
        elif part.startswith('*') and part.endswith('*') and len(part) > 2:
            inner = part[1:-1]
            content.append({
                'type': 'text',
                'text': inner,
                'marks': [{'type': 'em'}]
            })
        # Inline code: `code`
        elif part.startswith('`') and part.endswith('`'):
            inner = part[1:-1]
            content.append({
                'type': 'text',
                'text': inner,
                'marks': [{'type': 'code'}]
            })
        # Link: [text](url)
        elif part.startswith('[') and ')' in part:
            match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', part)
            if match:
                link_text = match.group(1)
                link_url = match.group(2)
                content.append({
                    'type': 'text',
                    'text': link_text,
                    'marks': [{'type': 'link', 'attrs': {'href': link_url}}]
                })
            else:
                content.append({'type': 'text', 'text': part})
        # Plain text
        else:
            content.append({'type': 'text', 'text': part})

    return content if content else [{'type': 'text', 'text': ''}]


def make_paragraph(text):
    """Create ADF paragraph node."""
    return {
        'type': 'paragraph',
        'content': parse_inline(text)
    }


def make_heading(text, level):
    """Create ADF heading node (level 1-6)."""
    return {
        'type': 'heading',
        'attrs': {'level': min(max(level, 1), 6)},
        'content': parse_inline(text)
    }


def make_code_block(code, language=None):
    """Create ADF code block node."""
    node = {
        'type': 'codeBlock',
        'content': [{'type': 'text', 'text': code}]
    }
    if language:
        node['attrs'] = {'language': language}
    return node


def make_bullet_list(items):
    """Create ADF bullet list node."""
    return {
        'type': 'bulletList',
        'content': [
            {
                'type': 'listItem',
                'content': [make_paragraph(item)]
            }
            for item in items
        ]
    }


def make_ordered_list(items):
    """Create ADF ordered list node."""
    return {
        'type': 'orderedList',
        'content': [
            {
                'type': 'listItem',
                'content': [make_paragraph(item)]
            }
            for item in items
        ]
    }


if __name__ == '__main__':
    # Test the converter
    import json

    test_md = """# Heading 1

This is a **bold** and *italic* test with `inline code`.

## Heading 2

- Item 1
- Item 2
- Item 3

1. First
2. Second

---

Check [this link](https://example.com) for more.

```python
def hello():
    print("Hello")
```
"""

    result = md_to_adf(test_md)
    print(json.dumps(result, indent=2))

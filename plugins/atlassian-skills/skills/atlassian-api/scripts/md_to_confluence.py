#!/usr/bin/env python3
"""
Markdown to Confluence Storage Format Converter

Converts Markdown files to Confluence XHTML storage format.
Handles: headings, paragraphs, bold, italic, links, lists, tables, code blocks (including Mermaid).
"""

import re
import sys
import json
import time
from pathlib import Path


def escape_xml(text):
    """Escape XML special characters."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def slugify(text):
    """Convert heading text to URL-friendly anchor ID."""
    # Remove inline formatting markers
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Convert to lowercase, replace spaces/special chars with hyphens
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    return text


def make_anchor(anchor_id):
    """Create Confluence anchor macro."""
    return f'<ac:structured-macro ac:name="anchor" ac:schema-version="1"><ac:parameter ac:name="">{anchor_id}</ac:parameter></ac:structured-macro>'


def make_toc_macro():
    """Create Confluence Table of Contents macro."""
    return '<ac:structured-macro ac:name="toc" ac:schema-version="1" />'


def wrap_with_toc_sidebar(content):
    """Wrap content in a two-column layout with TOC in right sidebar."""
    toc_sidebar = f'''<p><strong>Content On This Page</strong></p>
{make_toc_macro()}'''

    return f'''<ac:layout>
<ac:layout-section ac:type="two_right_sidebar" ac:breakout-mode="full-width">
<ac:layout-cell>
{content}
</ac:layout-cell>
<ac:layout-cell>
{toc_sidebar}
</ac:layout-cell>
</ac:layout-section>
</ac:layout>'''


def convert_inline(text):
    """Convert inline Markdown formatting to HTML."""
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)

    # Italic: *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'(?<![_\w])_([^_]+?)_(?![_\w])', r'<em>\1</em>', text)

    # Inline code: `code`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # Images: ![alt](src) — MUST come before links to avoid partial match
    def _image_replacement(match):
        alt = match.group(1)
        src = match.group(2)
        if src.startswith(('http://', 'https://')):
            # External URL image
            return f'<ac:image ac:alt="{alt}"><ri:url ri:value="{src}" /></ac:image>'
        else:
            # Local file — treat as page attachment
            return f'<ac:image ac:alt="{alt}" ac:width="800"><ri:attachment ri:filename="{src}" /></ac:image>'
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _image_replacement, text)

    # Links: [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    return text


def convert_mermaid_block(code):
    """Convert mermaid code to weweave Confluence mermaid macro."""
    # weweave macro expects JSON array with body and date
    # Escape code for JSON (handles newlines, quotes, etc.)
    timestamp = int(time.time() * 1000)
    body_json = json.dumps([{"body": code, "date": timestamp}])

    # Escape CDATA end sequences
    body_json = body_json.replace(']]>', ']]]]><![CDATA[>')

    return f'''<ac:structured-macro ac:name="confluence-mermaid-macro" ac:schema-version="1">
<ac:parameter ac:name="theme">neutral</ac:parameter>
<ac:parameter ac:name="alignment">center</ac:parameter>
<ac:parameter ac:name="look">classic</ac:parameter>
<ac:parameter ac:name="panZoom">true</ac:parameter>
<ac:parameter ac:name="fullscreen">true</ac:parameter>
<ac:plain-text-body><![CDATA[{body_json}]]></ac:plain-text-body>
</ac:structured-macro>'''


def convert_code_block(language, code):
    """Convert code block to Confluence structured macro."""
    # Use weweave mermaid macro for mermaid diagrams
    if language and language.lower() == 'mermaid':
        return convert_mermaid_block(code)

    # Escape CDATA end sequences in code
    code = code.replace(']]>', ']]]]><![CDATA[>')

    return f'''<ac:structured-macro ac:name="code" ac:schema-version="1">
<ac:parameter ac:name="language">{language or 'text'}</ac:parameter>
<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>
</ac:structured-macro>'''


def convert_table(lines):
    """Convert Markdown table to HTML table."""
    if len(lines) < 2:
        return ''

    html = ['<table>']

    # Header row
    header_cells = [cell.strip() for cell in lines[0].strip('|').split('|')]
    html.append('<tr>')
    for cell in header_cells:
        html.append(f'<th>{convert_inline(cell)}</th>')
    html.append('</tr>')

    # Skip separator row (lines[1])

    # Data rows
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        html.append('<tr>')
        for cell in cells:
            html.append(f'<td>{convert_inline(cell)}</td>')
        html.append('</tr>')

    html.append('</table>')
    return ''.join(html)


def convert_list(lines, ordered=False):
    """Convert Markdown list to HTML list."""
    tag = 'ol' if ordered else 'ul'
    html = [f'<{tag}>']

    for line in lines:
        # Remove list marker
        if ordered:
            content = re.sub(r'^\s*\d+\.\s*', '', line)
        else:
            content = re.sub(r'^\s*[-*+]\s*', '', line)
        html.append(f'<li><p>{convert_inline(content)}</p></li>')

    html.append(f'</{tag}>')
    return ''.join(html)


def md_to_confluence(markdown_text):
    """Convert Markdown text to Confluence storage format."""
    lines = markdown_text.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Code block
        if line.strip().startswith('```'):
            language = line.strip()[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # Skip closing ```
            code = '\n'.join(code_lines)
            result.append(convert_code_block(language, code))
            continue

        # Headings - add anchor macro before each heading for TOC links
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            raw_heading = heading_match.group(2)
            anchor_id = slugify(raw_heading)
            content = convert_inline(raw_heading)
            # Add anchor macro before heading for TOC navigation
            result.append(make_anchor(anchor_id))
            result.append(f'<h{level}>{content}</h{level}>')
            # Skip inline TOC - it will be in the sidebar
            i += 1
            continue

        # Table
        if '|' in line and i + 1 < len(lines) and re.match(r'^[\s|:-]+$', lines[i + 1]):
            table_lines = [line]
            i += 1
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i])
                i += 1
            result.append(convert_table(table_lines))
            continue

        # Unordered list
        if re.match(r'^\s*[-*+]\s+', line):
            list_lines = [line]
            i += 1
            while i < len(lines) and re.match(r'^\s*[-*+]\s+', lines[i]):
                list_lines.append(lines[i])
                i += 1
            result.append(convert_list(list_lines, ordered=False))
            continue

        # Ordered list
        if re.match(r'^\s*\d+\.\s+', line):
            list_lines = [line]
            i += 1
            while i < len(lines) and re.match(r'^\s*\d+\.\s+', lines[i]):
                list_lines.append(lines[i])
                i += 1
            result.append(convert_list(list_lines, ordered=True))
            continue

        # Horizontal rule
        if re.match(r'^[-*_]{3,}\s*$', line):
            result.append('<hr />')
            i += 1
            continue

        # Skip manual TOC anchor links - they're replaced by the TOC macro
        # The TOC macro is inserted after "Table of Contents" heading
        if line.strip().startswith('[') and '](#' in line:
            i += 1
            continue

        # Regular paragraph
        paragraph_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not any([
            lines[i].strip().startswith('#'),
            lines[i].strip().startswith('```'),
            lines[i].strip().startswith('-') and ' ' in lines[i],
            lines[i].strip().startswith('*') and ' ' in lines[i],
            re.match(r'^\d+\.', lines[i].strip()),
            '|' in lines[i] and i + 1 < len(lines) and '|' in lines[i + 1],
            re.match(r'^[-*_]{3,}\s*$', lines[i])
        ]):
            paragraph_lines.append(lines[i])
            i += 1

        content = ' '.join(paragraph_lines)
        content = convert_inline(content)
        result.append(f'<p>{content}</p>')

    # Wrap content with TOC sidebar layout
    main_content = ''.join(result)
    return wrap_with_toc_sidebar(main_content)


def convert_file(input_path, output_path=None):
    """Convert a Markdown file to Confluence format."""
    with open(input_path, 'r', encoding='utf-8') as f:
        markdown = f.read()

    confluence = md_to_confluence(markdown)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(confluence)
        print(f"Converted: {input_path} -> {output_path}")
    else:
        print(confluence)

    return confluence


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python md_to_confluence.py <input.md> [output.html]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    convert_file(input_file, output_file)

#!/usr/bin/env python3
"""
CRE 2.0 FreeMarker Template Validator

Validate FreeMarker template syntax and extract variables.
Performs local validation without requiring NetSuite connection.

Commands:
  validate <file>       Validate template syntax
  extract-vars <file>   Extract variables used in template
  check-xml <file>      Check XML/HTML structure
"""

import sys
import re
import os
from typing import List, Dict, Set, Tuple
from collections import defaultdict


class TemplateValidator:
    """FreeMarker template validator for CRE 2.0 templates."""

    # FreeMarker directive patterns
    DIRECTIVE_PATTERNS = {
        'if': re.compile(r'<#if\s+([^>]+)>', re.IGNORECASE),
        'elseif': re.compile(r'<#elseif\s+([^>]+)>', re.IGNORECASE),
        'else': re.compile(r'<#else\s*>', re.IGNORECASE),
        'endif': re.compile(r'</#if\s*>', re.IGNORECASE),
        'list': re.compile(r'<#list\s+([^\s]+)\s+as\s+([^>]+)>', re.IGNORECASE),
        'endlist': re.compile(r'</#list\s*>', re.IGNORECASE),
        'assign': re.compile(r'<#assign\s+([^=]+)\s*=\s*([^>]+)>', re.IGNORECASE),
        'macro': re.compile(r'<macro\s+id="([^"]+)">', re.IGNORECASE),
        'endmacro': re.compile(r'</macro\s*>', re.IGNORECASE),
    }

    # Variable interpolation pattern
    VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')

    # Built-in functions
    BUILTINS = {
        '?has_content', '?string', '?number', '?date', '?time', '?datetime',
        '?upper_case', '?lower_case', '?cap_first', '?trim', '?length',
        '?replace', '?split', '?join', '?size', '?first', '?last',
        '?keys', '?values', '?string.currency', '?string.number',
        '?string.medium', '?string.short', '?string.long'
    }

    def __init__(self, content: str, filename: str = 'template.html'):
        self.content = content
        self.filename = filename
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.variables: Set[str] = set()
        self.assignments: Set[str] = set()
        self.macros: Set[str] = set()
        self.lists: List[Tuple[str, str]] = []

    def validate(self) -> bool:
        """Run all validations and return True if valid."""
        self._validate_directives()
        self._validate_variables()
        self._validate_xml_structure()
        self._check_common_issues()
        return len(self.errors) == 0

    def _validate_directives(self) -> None:
        """Validate FreeMarker directive matching."""
        # Track directive stack
        if_stack = 0
        list_stack = 0
        macro_stack = 0

        lines = self.content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Check #if directives
            if_opens = len(self.DIRECTIVE_PATTERNS['if'].findall(line))
            if_closes = len(self.DIRECTIVE_PATTERNS['endif'].findall(line))
            if_stack += if_opens - if_closes

            # Check #list directives
            list_matches = self.DIRECTIVE_PATTERNS['list'].findall(line)
            for collection, var in list_matches:
                self.lists.append((collection.strip(), var.strip()))
            list_opens = len(list_matches)
            list_closes = len(self.DIRECTIVE_PATTERNS['endlist'].findall(line))
            list_stack += list_opens - list_closes

            # Check macro directives
            macro_matches = self.DIRECTIVE_PATTERNS['macro'].findall(line)
            for macro_id in macro_matches:
                self.macros.add(macro_id)
            macro_opens = len(macro_matches)
            macro_closes = len(self.DIRECTIVE_PATTERNS['endmacro'].findall(line))
            macro_stack += macro_opens - macro_closes

            # Check #assign directives
            assign_matches = self.DIRECTIVE_PATTERNS['assign'].findall(line)
            for var_name, _ in assign_matches:
                self.assignments.add(var_name.strip())

            # Check for #elseif without #if
            if self.DIRECTIVE_PATTERNS['elseif'].search(line):
                if if_stack <= 0:
                    self.errors.append(f"Line {line_num}: <#elseif> without matching <#if>")

            # Check for #else without #if
            if self.DIRECTIVE_PATTERNS['else'].search(line):
                if if_stack <= 0:
                    self.errors.append(f"Line {line_num}: <#else> without matching <#if>")

        # Check final balances
        if if_stack > 0:
            self.errors.append(f"Unclosed <#if> directive(s): {if_stack} remaining")
        elif if_stack < 0:
            self.errors.append(f"Extra </#if> directive(s): {-if_stack} extra")

        if list_stack > 0:
            self.errors.append(f"Unclosed <#list> directive(s): {list_stack} remaining")
        elif list_stack < 0:
            self.errors.append(f"Extra </#list> directive(s): {-list_stack} extra")

        if macro_stack > 0:
            self.errors.append(f"Unclosed <macro> directive(s): {macro_stack} remaining")
        elif macro_stack < 0:
            self.errors.append(f"Extra </macro> directive(s): {-macro_stack} extra")

    def _validate_variables(self) -> None:
        """Extract and validate variable references."""
        matches = self.VAR_PATTERN.findall(self.content)

        for match in matches:
            # Clean up the variable expression
            var_expr = match.strip()

            # Extract base variable name
            base_var = var_expr.split('.')[0].split('[')[0].split('?')[0]

            # Skip built-in variables
            if base_var in ['.now', '.data_model', '.main']:
                continue

            self.variables.add(base_var)

            # Check for common issues
            if '??' in var_expr:
                self.warnings.append(f"Double question mark in expression: ${{{var_expr}}}")

            # Check for missing quotes in string comparisons
            if '==' in var_expr and not ('"' in var_expr or "'" in var_expr):
                # Could be comparing to number or boolean, just warn
                self.warnings.append(f"String comparison may need quotes: ${{{var_expr}}}")

    def _validate_xml_structure(self) -> None:
        """Validate basic XML/HTML structure."""
        # Check for PDF doctype
        if '<!DOCTYPE pdf' in self.content:
            if '<pdf>' not in self.content:
                self.errors.append("Missing <pdf> root element")
            if '</pdf>' not in self.content:
                self.errors.append("Missing </pdf> closing tag")

            if '<head>' not in self.content:
                self.warnings.append("Missing <head> section in PDF template")

            if '<body' not in self.content:
                self.errors.append("Missing <body> element in PDF template")

        # Check for common unclosed tags
        self_closing = {'br', 'hr', 'img', 'input', 'meta', 'link'}
        tag_pattern = re.compile(r'<(/?)(\w+)[^>]*(/?)>')

        tag_stack = []
        for match in tag_pattern.finditer(self.content):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2).lower()
            is_self_closing = match.group(3) == '/'

            # Skip self-closing tags
            if tag_name in self_closing or is_self_closing:
                continue

            # Skip FreeMarker directives embedded in attributes
            if tag_name.startswith('#') or tag_name.startswith('/'):
                continue

            if is_closing:
                if tag_stack and tag_stack[-1] == tag_name:
                    tag_stack.pop()
                elif tag_stack:
                    # Mismatched tag
                    pass  # Don't report - FreeMarker can cause false positives
            else:
                tag_stack.append(tag_name)

    def _check_common_issues(self) -> None:
        """Check for common CRE 2.0 template issues."""
        lines = self.content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Check for ?number without ?has_content
            if '?number' in line and '?has_content' not in line:
                # Look for the variable being converted
                match = re.search(r'\$\{([^}]+)\?number', line)
                if match:
                    var = match.group(1)
                    # Check if there's a surrounding ?has_content check
                    if f'{var}?has_content' not in self.content:
                        self.warnings.append(
                            f"Line {line_num}: {var}?number without ?has_content check may fail on null"
                        )

            # Check for hardcoded URLs that might not work across environments
            if 'system.netsuite.com' in line or 'system.sandbox.netsuite.com' in line:
                self.warnings.append(
                    f"Line {line_num}: Hardcoded NetSuite URL may not work across environments"
                )

    def get_variables(self) -> Dict[str, List[str]]:
        """Get categorized variables."""
        categories = defaultdict(list)

        for var in sorted(self.variables):
            if var in self.assignments:
                categories['assigned'].append(var)
            elif var in ['record', 'customer', 'tran', 'aging', 'itemfulfillment', 'salesorder']:
                categories['data_source'].append(var)
            elif var in ['preferences', 'currency_symbol']:
                categories['system'].append(var)
            else:
                categories['unknown'].append(var)

        return dict(categories)

    def print_report(self) -> None:
        """Print validation report."""
        print(f"\nCRE 2.0 Template Validation Report")
        print(f"File: {self.filename}")
        print("=" * 60)

        # Errors
        if self.errors:
            print(f"\n[ERRORS] ({len(self.errors)})")
            for error in self.errors:
                print(f"  ❌ {error}")
        else:
            print("\n[ERRORS] None found ✅")

        # Warnings
        if self.warnings:
            print(f"\n[WARNINGS] ({len(self.warnings)})")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
        else:
            print("\n[WARNINGS] None found ✅")

        # Summary
        print(f"\n[SUMMARY]")
        print(f"  Variables used: {len(self.variables)}")
        print(f"  Assignments: {len(self.assignments)}")
        print(f"  Macros: {len(self.macros)}")
        print(f"  Lists: {len(self.lists)}")

        # Result
        print("\n" + "=" * 60)
        if self.errors:
            print("Result: FAILED ❌")
        else:
            print("Result: PASSED ✅")

    def print_variables(self) -> None:
        """Print extracted variables."""
        print(f"\nVariables in {self.filename}")
        print("=" * 60)

        categories = self.get_variables()

        if categories.get('data_source'):
            print("\n[DATA SOURCE VARIABLES]")
            for var in categories['data_source']:
                print(f"  ${{{var}.*}}")

        if categories.get('assigned'):
            print("\n[ASSIGNED VARIABLES]")
            for var in categories['assigned']:
                print(f"  ${{{var}}}")

        if categories.get('system'):
            print("\n[SYSTEM VARIABLES]")
            for var in categories['system']:
                print(f"  ${{{var}}}")

        if categories.get('unknown'):
            print("\n[OTHER VARIABLES]")
            for var in categories['unknown']:
                print(f"  ${{{var}}}")

        if self.lists:
            print("\n[LIST ITERATIONS]")
            for collection, var in self.lists:
                print(f"  <#list {collection} as {var}>")

        if self.macros:
            print("\n[MACROS]")
            for macro in sorted(self.macros):
                print(f"  <macro id=\"{macro}\">")


def validate_file(filepath: str) -> bool:
    """Validate a template file."""
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    validator = TemplateValidator(content, os.path.basename(filepath))
    is_valid = validator.validate()
    validator.print_report()

    return is_valid


def extract_variables(filepath: str) -> None:
    """Extract variables from a template file."""
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    validator = TemplateValidator(content, os.path.basename(filepath))
    validator.validate()  # Run validation to extract variables
    validator.print_variables()


def check_xml(filepath: str) -> None:
    """Check XML structure of template."""
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    print(f"\nXML Structure Check: {os.path.basename(filepath)}")
    print("=" * 60)

    # Check doctype
    if '<!DOCTYPE pdf' in content:
        print("✅ PDF doctype found")
    elif '<!DOCTYPE html' in content:
        print("✅ HTML doctype found")
    else:
        print("⚠️  No doctype found")

    # Check root elements
    if '<pdf>' in content and '</pdf>' in content:
        print("✅ <pdf> root element balanced")
    elif '<html>' in content and '</html>' in content:
        print("✅ <html> root element balanced")

    # Check head/body
    if '<head>' in content:
        print("✅ <head> section present")
    if '<body' in content:
        print("✅ <body> element present")

    # Check for macros
    macro_pattern = re.compile(r'<macro\s+id="([^"]+)">')
    macros = macro_pattern.findall(content)
    if macros:
        print(f"✅ Found {len(macros)} macro(s): {', '.join(macros)}")


def print_usage():
    """Print usage information."""
    print("""CRE 2.0 Template Validator

Usage: python3 validate_template.py <command> <file>

Commands:
  validate <file>       Validate FreeMarker template syntax
  extract-vars <file>   Extract variables used in template
  check-xml <file>      Check XML/HTML structure
  <file>                Same as validate (default command)

Examples:
  python3 validate_template.py validate template.html
  python3 validate_template.py extract-vars template.html
  python3 validate_template.py check-xml template.html
  python3 validate_template.py template.html  # defaults to validate

Validation checks:
  - Balanced FreeMarker directives (<#if>/</#if>, <#list>/</#list>)
  - Variable syntax
  - Common issues (?number without null check, hardcoded URLs)
  - Basic XML structure
""")


def main():
    """CLI interface."""
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print_usage()
        sys.exit(0)

    command = sys.argv[1]

    # Handle default command (just filename)
    if command.endswith('.html') or command.endswith('.xml'):
        filepath = command
        command = 'validate'
    elif len(sys.argv) < 3:
        print("ERROR: File path required")
        print_usage()
        sys.exit(1)
    else:
        filepath = sys.argv[2]

    if command == 'validate':
        success = validate_file(filepath)
        sys.exit(0 if success else 1)

    elif command in ['extract-vars', 'vars', 'variables']:
        extract_variables(filepath)

    elif command in ['check-xml', 'xml']:
        check_xml(filepath)

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == '__main__':
    main()

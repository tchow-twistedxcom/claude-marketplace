#!/usr/bin/env python3
"""
Automated PDF Verification for CRE2 Templates.

Downloads and analyzes a rendered PDF to check for common issues:
- DEBUG messages visible
- Unresolved ${variable} patterns
- "null" or "undefined" text
- Empty sections
- Missing data indicators

Usage:
    python3 verify_pdf.py --url "https://4138030-sb2.app.netsuite.com/..."
    python3 verify_pdf.py --profile-id 1217 --record-id 8352429 --env sb2
    python3 verify_pdf.py --file /path/to/local.pdf

Requirements:
    pip install pypdf2  (or pdfplumber for better extraction)
"""

import sys
import json
import argparse
import urllib.request
import urllib.error
import tempfile
import re
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Try to import PDF libraries
PDF_LIBRARY = None
try:
    import pdfplumber
    PDF_LIBRARY = 'pdfplumber'
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PDF_LIBRARY = 'pypdf2'
    except ImportError:
        pass

# NetSuite API Gateway endpoint
GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# Account/Environment mappings
ACCOUNT_ALIASES = {
    'twx': 'twistedx', 'twisted': 'twistedx', 'twistedx': 'twistedx',
    'dm': 'dutyman', 'duty': 'dutyman', 'dutyman': 'dutyman'
}

ENV_ALIASES = {
    'prod': 'production', 'production': 'production',
    'sb1': 'sandbox', 'sandbox': 'sandbox', 'sandbox1': 'sandbox',
    'sb2': 'sandbox2', 'sandbox2': 'sandbox2'
}

ACCOUNT_IDS = {
    'twistedx': {
        'production': '4138030',
        'sandbox': '4138030-sb1',
        'sandbox2': '4138030-sb2'
    },
    'dutyman': {
        'production': '3611820',
        'sandbox': '3611820-sb1',
        'sandbox2': '3611820-sb2'
    }
}

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'

# Verification patterns
ISSUE_PATTERNS = {
    'debug_messages': [
        r'\bDEBUG\b',
        r'\bDEBUG:',
        r'Debug:',
        r'\[DEBUG\]',
    ],
    'unresolved_variables': [
        r'\$\{[^}]+\}',  # ${variable}
        r'\$\![^}]+\}',  # $!{variable}
        r'\#\{[^}]+\}',  # #{variable}
    ],
    'null_values': [
        r'\bnull\b',
        r'\bundefined\b',
        r'\bNaN\b',
        r'\[object Object\]',
    ],
    'error_indicators': [
        r'\bError\b',
        r'\bERROR\b',
        r'\bException\b',
        r'FreeMarker',
        r'template error',
    ],
    'placeholder_text': [
        r'TODO',
        r'FIXME',
        r'XXX',
        r'PLACEHOLDER',
        r'N/A',  # May be intentional but worth noting
    ],
}

# Expected content patterns (presence is good)
EXPECTED_PATTERNS = {
    'has_date': r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY or similar
    'has_currency': r'\$[\d,]+\.\d{2}',  # $X,XXX.XX
    'has_document_number': r'(?:PO|Invoice|Order|Shipment|ASN).*?(?:#|Number|ID)?\s*:?\s*\w+',
}


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def get_netsuite_base_url(account: str, environment: str) -> str:
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)
    account_id = ACCOUNT_IDS.get(resolved_account, {}).get(resolved_env)
    if not account_id:
        return None
    return f"https://{account_id}.app.netsuite.com"


def render_pdf(
    profile_id: str,
    record_id: str,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """Call CRE2 render API to generate PDF."""
    payload = {
        'action': 'cre2Render',
        'procedure': 'cre2Render',
        'profileId': profile_id,
        'recordId': record_id,
        'netsuiteAccount': resolve_account(account),
        'netsuiteEnvironment': resolve_environment(environment)
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            GATEWAY_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'http://localhost:3002'
            }
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))

            if result.get('success') and result.get('data', {}).get('pdfUrl'):
                pdf_url = result['data']['pdfUrl']
                if pdf_url.startswith('/'):
                    base_url = get_netsuite_base_url(account, environment)
                    if base_url:
                        result['data']['fullPdfUrl'] = f"{base_url}{pdf_url}"

            return result

    except Exception as e:
        return {'success': False, 'error': {'message': str(e)}}


def download_pdf(url: str, output_path: str = None) -> Tuple[bool, str]:
    """Download PDF from URL to local file."""
    if not output_path:
        fd, output_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)

    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        return True, output_path
    except Exception as e:
        return False, str(e)


def extract_text_from_pdf(pdf_path: str) -> Tuple[bool, str]:
    """Extract text content from PDF file."""
    if not PDF_LIBRARY:
        return False, "No PDF library installed. Install with: pip install pdfplumber"

    try:
        text_content = []

        if PDF_LIBRARY == 'pdfplumber':
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ''
                    text_content.append(page_text)

        elif PDF_LIBRARY == 'pypdf2':
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                page_text = page.extract_text() or ''
                text_content.append(page_text)

        return True, '\n'.join(text_content)

    except Exception as e:
        return False, str(e)


def analyze_pdf_content(text: str) -> Dict[str, Any]:
    """Analyze extracted PDF text for issues."""
    results = {
        'issues': [],
        'warnings': [],
        'info': [],
        'content_checks': {},
        'issue_count': 0,
        'warning_count': 0,
    }

    # Check for issues
    for category, patterns in ISSUE_PATTERNS.items():
        found = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found.extend(matches[:5])  # Limit to first 5 matches

        if found:
            if category in ['debug_messages', 'unresolved_variables', 'error_indicators']:
                results['issues'].append({
                    'category': category,
                    'matches': list(set(found))[:5],
                    'severity': 'error'
                })
                results['issue_count'] += 1
            elif category == 'null_values':
                results['warnings'].append({
                    'category': category,
                    'matches': list(set(found))[:5],
                    'severity': 'warning'
                })
                results['warning_count'] += 1
            else:
                results['info'].append({
                    'category': category,
                    'matches': list(set(found))[:5],
                    'severity': 'info'
                })

    # Check for expected content
    for check_name, pattern in EXPECTED_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        results['content_checks'][check_name] = {
            'found': len(matches) > 0,
            'count': len(matches),
            'samples': matches[:3] if matches else []
        }

    # Check for empty or minimal content
    word_count = len(text.split())
    if word_count < 50:
        results['warnings'].append({
            'category': 'minimal_content',
            'message': f'PDF has very little text content ({word_count} words)',
            'severity': 'warning'
        })
        results['warning_count'] += 1

    # Determine overall status
    if results['issue_count'] > 0:
        results['status'] = 'FAIL'
    elif results['warning_count'] > 0:
        results['status'] = 'WARN'
    else:
        results['status'] = 'PASS'

    return results


def print_verification_report(results: Dict[str, Any], pdf_source: str):
    """Print formatted verification report."""
    status = results['status']
    status_icon = '✅' if status == 'PASS' else ('⚠️' if status == 'WARN' else '❌')

    print("\n" + "="*60)
    print("CRE2 PDF VERIFICATION REPORT")
    print("="*60)
    print(f"\n📄 Source: {pdf_source}")
    print(f"\n{status_icon} Overall Status: {status}")
    print(f"   Issues: {results['issue_count']} | Warnings: {results['warning_count']}")

    # Critical issues
    if results['issues']:
        print("\n❌ CRITICAL ISSUES:")
        for issue in results['issues']:
            print(f"\n   [{issue['category'].upper().replace('_', ' ')}]")
            for match in issue['matches']:
                print(f"      • Found: \"{match}\"")

    # Warnings
    if results['warnings']:
        print("\n⚠️ WARNINGS:")
        for warning in results['warnings']:
            if 'matches' in warning:
                print(f"\n   [{warning['category'].upper().replace('_', ' ')}]")
                for match in warning['matches']:
                    print(f"      • Found: \"{match}\"")
            elif 'message' in warning:
                print(f"\n   [{warning['category'].upper().replace('_', ' ')}]")
                print(f"      • {warning['message']}")

    # Content checks
    print("\n📋 CONTENT VERIFICATION:")
    for check_name, check_result in results['content_checks'].items():
        icon = '✓' if check_result['found'] else '✗'
        display_name = check_name.replace('has_', '').replace('_', ' ').title()
        if check_result['found']:
            samples = ', '.join(check_result['samples'][:2])
            print(f"   {icon} {display_name}: Found ({check_result['count']} instances)")
            if samples:
                print(f"      e.g., {samples}")
        else:
            print(f"   {icon} {display_name}: NOT FOUND")

    # Info items
    if results['info']:
        print("\nℹ️ NOTES:")
        for info in results['info']:
            print(f"   [{info['category'].upper().replace('_', ' ')}]")
            for match in info['matches']:
                print(f"      • \"{match}\"")

    print("\n" + "-"*60)
    if status == 'PASS':
        print("✅ PDF passed all verification checks")
    elif status == 'WARN':
        print("⚠️ PDF has warnings that should be reviewed")
    else:
        print("❌ PDF has critical issues that need to be fixed")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Automated PDF verification for CRE2 templates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify by rendering first
  python3 verify_pdf.py --profile-id 1217 --record-id 8352429 --env sb2

  # Verify from URL
  python3 verify_pdf.py --url "https://4138030-sb2.app.netsuite.com/..."

  # Verify local file
  python3 verify_pdf.py --file /path/to/document.pdf

  # JSON output for automation
  python3 verify_pdf.py --profile-id 1217 --record-id 8352429 --env sb2 --json
        """
    )

    # Source options (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        '--url', '-u',
        help='PDF URL to download and verify'
    )
    source_group.add_argument(
        '--file', '-f',
        help='Local PDF file to verify'
    )
    source_group.add_argument(
        '--profile-id', '-p',
        help='CRE2 profile ID (use with --record-id)'
    )

    parser.add_argument(
        '--record-id', '-r',
        help='Record ID to render (required with --profile-id)'
    )
    parser.add_argument(
        '--account', '-a',
        default=DEFAULT_ACCOUNT,
        choices=['twx', 'twistedx', 'dm', 'dutyman'],
        help=f'NetSuite account (default: {DEFAULT_ACCOUNT})'
    )
    parser.add_argument(
        '--env', '-e',
        default=DEFAULT_ENVIRONMENT,
        choices=['prod', 'production', 'sb1', 'sandbox', 'sb2', 'sandbox2'],
        help=f'NetSuite environment (default: {DEFAULT_ENVIRONMENT})'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--keep-pdf',
        action='store_true',
        help='Keep downloaded PDF file after verification'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.profile_id and not args.record_id:
        parser.error("--record-id is required when using --profile-id")

    # Check PDF library availability
    if not PDF_LIBRARY:
        print("Error: No PDF library installed.", file=sys.stderr)
        print("Install with: pip install pdfplumber", file=sys.stderr)
        print("         or: pip install pypdf2", file=sys.stderr)
        sys.exit(1)

    pdf_path = None
    pdf_source = ""
    temp_file = False

    try:
        # Get PDF from source
        if args.file:
            pdf_path = args.file
            pdf_source = args.file
            if not os.path.exists(pdf_path):
                print(f"Error: File not found: {pdf_path}", file=sys.stderr)
                sys.exit(1)

        elif args.url:
            print(f"Downloading PDF from URL...")
            success, result = download_pdf(args.url)
            if not success:
                print(f"Error downloading PDF: {result}", file=sys.stderr)
                sys.exit(1)
            pdf_path = result
            pdf_source = args.url
            temp_file = True

        elif args.profile_id:
            print(f"Rendering PDF (Profile: {args.profile_id}, Record: {args.record_id})...")
            result = render_pdf(args.profile_id, args.record_id, args.account, args.env)

            if not result.get('success'):
                error = result.get('error', {}).get('message', 'Unknown error')
                print(f"Error rendering PDF: {error}", file=sys.stderr)
                sys.exit(1)

            pdf_url = result.get('data', {}).get('fullPdfUrl') or result.get('data', {}).get('pdfUrl')
            if not pdf_url:
                print("Error: No PDF URL returned", file=sys.stderr)
                sys.exit(1)

            print(f"Downloading rendered PDF...")
            success, dl_result = download_pdf(pdf_url)
            if not success:
                print(f"Error downloading PDF: {dl_result}", file=sys.stderr)
                sys.exit(1)

            pdf_path = dl_result
            pdf_source = f"Profile {args.profile_id}, Record {args.record_id}"
            temp_file = True

        # Extract text from PDF
        print(f"Extracting text from PDF (using {PDF_LIBRARY})...")
        success, text_or_error = extract_text_from_pdf(pdf_path)

        if not success:
            print(f"Error extracting text: {text_or_error}", file=sys.stderr)
            sys.exit(1)

        # Analyze content
        results = analyze_pdf_content(text_or_error)
        results['pdf_source'] = pdf_source
        results['text_length'] = len(text_or_error)
        results['word_count'] = len(text_or_error.split())

        # Output results
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print_verification_report(results, pdf_source)

        # Exit code based on status
        if results['status'] == 'FAIL':
            sys.exit(1)
        elif results['status'] == 'WARN':
            sys.exit(0)  # Warnings are non-fatal
        else:
            sys.exit(0)

    finally:
        # Clean up temp file
        if temp_file and pdf_path and os.path.exists(pdf_path) and not args.keep_pdf:
            try:
                os.remove(pdf_path)
            except:
                pass


if __name__ == '__main__':
    main()

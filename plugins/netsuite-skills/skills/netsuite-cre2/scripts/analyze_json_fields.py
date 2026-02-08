#!/usr/bin/env python3
"""
Analyze EDI JSON structure vs Data Extractor expectations.

Compares the actual JSON field structure in an EDI record against
what the data extractor function expects to find.

Usage:
    python3 analyze_json_fields.py --record-id 9405472 --doctype 824 --env sb2
    python3 analyze_json_fields.py --record-id 7696563 --doctype 850 --env sb2 --show-json
    python3 analyze_json_fields.py --record-id 9405472 --show-structure --env sb2

Returns:
    Analysis showing:
    - Actual JSON field paths
    - Expected fields from data extractor
    - Mismatches and suggestions
"""

import sys
import json
import argparse
import urllib.request
import urllib.error
import re
from typing import Dict, Any, List, Set
from pathlib import Path

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

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'

# Data extractor file path (relative to B2bDashboard)
DATA_EXTRACTOR_PATH = Path.home() / 'B2bDashboard' / 'sdf' / 'FileCabinet' / 'SuiteScripts' / 'Twisted X' / 'CRE2' / 'twx_CRE2_EDI_DataExtractor.js'

# Expected field patterns by document type
# These are extracted from the data extractor functions
EXPECTED_FIELDS = {
    '810': [
        'EDI Invoice ID', 'Invoice Number', 'Invoice Date', 'Invoice Amount',
        'Purchase Order Number', 'Bill of Lading Number',
        'N101 - Entity Identifier Code', 'N102 - Name',
        'IT101 - Assigned Identification', 'IT102 - Quantity Invoiced',
        'IT104 - Unit Price', 'IT105 - Unit of Measure',
        'TDS01 - Total Monetary Value',
    ],
    '850': [
        'EDI Purchase Order ID', 'Purchase Order Number', 'Purchase Order Date',
        'Date/Time Reference', 'PO Creation Date', 'Requested Ship Date',
        'Date(BEG05)', 'BEG01 - Transaction Set Purpose Code',
        'N101 - Entity Identifier Code', 'N102 - Name', 'N103 - Identification Code Qualifier',
        'PO101 - Assigned Identification', 'PO102 - Quantity Ordered',
        'PO104 - Unit Price', 'PO105 - Basis of Unit Price Code',
        'Product/Item Description', 'Buyer Item Number', 'Vendor Item Number',
        'ITD01 - Terms Type Code', 'ITD02 - Terms Basis Date Code',
        'ITD05 - Terms Discount Percent', 'ITD07 - Terms Net Days',
    ],
    '855': [
        'BAK01 - Transaction Set Purpose Code', 'BAK02 - Acknowledgment Type',
        'BAK03 - Purchase Order Number', 'BAK04 - Date', 'BAK06 - Request Reference Number',
        'ACK01 - Line Item Status Code', 'ACK02 - Quantity',
        'N101 - Entity Identifier Code', 'N102 - Name',
    ],
    '856': [
        'BSN01 - Transaction Set Purpose Code', 'BSN02 - Shipment Identification',
        'BSN03 - Date', 'BSN04 - Time',
        'TD501 - Carrier Transportation Method/Type Code', 'TD502 - Routing',
        'TD503 - Shipment Weight', 'TD109 - Packaging Form Code',
        'REF02 - Reference Identification',
        'HL01 - Hierarchical ID Number', 'HL02 - Hierarchical Parent ID',
        'SN101 - Assigned Identification', 'SN102 - Number of Units Shipped',
    ],
    '820': [
        'BPR01 - Transaction Handling Code', 'BPR02 - Monetary Amount',
        'BPR03 - Credit/Debit Flag Code', 'BPR04 - Payment Method Code',
        'BPR16 - Date', 'TRN02 - Reference Identification',
        'N101 - Entity Identifier Code', 'N102 - Name',
        'RMR01 - Reference Identification Qualifier', 'RMR02 - Reference Identification',
        'RMR04 - Monetary Amount',
    ],
    '824': [
        'BGN01 - Transaction Set Purpose Code', 'BGN02 - Reference Identification',
        'BGN03 - Date', 'BGN04 - Time',
        'OTI01 - Application Acknowledgment Code', 'OTI02 - Reference Identification',
        'OTI03 - Date', 'OTI06 - Transaction Set Identifier Code',
        'TED01 - Application Error Condition Code', 'TED02 - Free Form Message',
        'N1 Loop', 'N101 - Entity Identifier Code', 'N102 - Name',
    ],
    '860': [
        'BCH01 - Transaction Set Purpose Code', 'BCH02 - Purchase Order Type Code',
        'BCH03 - Purchase Order Number', 'BCH05 - Date',
        'POC01 - Assigned Identification', 'POC02 - Change/Response Type Code',
        'POC03 - Quantity', 'POC04 - Quantity', 'POC05 - Unit of Measure',
        'POC06 - Unit Price',
    ],
}


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def fetch_record_json(
    record_id: str,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """Fetch EDI JSON from a specific record."""
    query = f"""
        SELECT
            h.id,
            h.custrecord_twx_edi_history_json AS edi_json,
            h.custrecord_twx_edi_type AS doc_type_id
        FROM customrecord_twx_edi_history h
        WHERE h.id = {record_id}
    """

    payload = {
        'action': 'execute',
        'procedure': 'queryRun',
        'query': query,
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

        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))

            if result.get('success'):
                rows = result.get('data', {}).get('rows', [])
                if rows:
                    row = rows[0]
                    edi_json_str = row.get('edi_json', '{}')
                    try:
                        edi_json = json.loads(edi_json_str) if edi_json_str else {}
                    except json.JSONDecodeError:
                        edi_json = {}
                    return {
                        'success': True,
                        'record_id': record_id,
                        'doc_type_id': row.get('doc_type_id'),
                        'edi_json': edi_json,
                        'raw_json': edi_json_str
                    }
                else:
                    return {'success': False, 'error': {'message': f'Record {record_id} not found'}}
            return result

    except Exception as e:
        return {'success': False, 'error': {'message': str(e)}}


def extract_field_paths(obj: Any, prefix: str = '', paths: Set[str] = None) -> Set[str]:
    """Recursively extract all field paths from a JSON object."""
    if paths is None:
        paths = set()

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{prefix}.{key}" if prefix else key
            paths.add(current_path)
            extract_field_paths(value, current_path, paths)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            # For arrays, use [] notation
            array_path = f"{prefix}[]" if prefix else "[]"
            paths.add(array_path)
            extract_field_paths(item, array_path, paths)

    return paths


def get_top_level_fields(obj: Dict) -> List[str]:
    """Get just the top-level field names from JSON."""
    if isinstance(obj, dict):
        return sorted(obj.keys())
    return []


def analyze_structure(edi_json: Dict) -> Dict[str, Any]:
    """Analyze the structure of the EDI JSON."""
    all_paths = extract_field_paths(edi_json)
    top_level = get_top_level_fields(edi_json)

    # Categorize fields
    segment_fields = []  # Fields that look like EDI segment references (e.g., BGN01, N102)
    data_fields = []     # Fields that look like data values
    array_fields = []    # Fields that are arrays
    nested_fields = []   # Fields with nested objects

    for key in top_level:
        value = edi_json[key]
        if isinstance(value, list):
            array_fields.append(f"{key}[] ({len(value)} items)")
        elif isinstance(value, dict):
            nested_fields.append(key)
        elif re.match(r'^[A-Z]{2,3}\d{2}', key):
            segment_fields.append(key)
        else:
            data_fields.append(key)

    return {
        'total_paths': len(all_paths),
        'top_level_count': len(top_level),
        'segment_fields': sorted(segment_fields),
        'data_fields': sorted(data_fields),
        'array_fields': sorted(array_fields),
        'nested_fields': sorted(nested_fields),
        'all_paths': sorted(all_paths)
    }


def compare_fields(
    actual_fields: Set[str],
    expected_fields: List[str],
    doctype: str
) -> Dict[str, Any]:
    """Compare actual JSON fields to expected fields."""
    actual_set = set(actual_fields)
    expected_set = set(expected_fields)

    # Fields in actual that match expected
    matched = actual_set & expected_set

    # Fields expected but not found (potential issues)
    missing = expected_set - actual_set

    # Fields in actual not in expected (may need extractor updates)
    extra = actual_set - expected_set

    # Try to find close matches for missing fields
    suggestions = {}
    for missing_field in missing:
        # Extract the key part (e.g., "BGN01" from "BGN01 - Transaction Set Purpose Code")
        match = re.match(r'^([A-Z]{2,3}\d{2})', missing_field)
        if match:
            prefix = match.group(1)
            # Look for actual fields that might be similar
            for actual in extra:
                if prefix in actual or actual.startswith(prefix):
                    suggestions[missing_field] = actual

    return {
        'doctype': doctype,
        'matched_count': len(matched),
        'missing_count': len(missing),
        'extra_count': len(extra),
        'matched_fields': sorted(matched),
        'missing_fields': sorted(missing),
        'extra_fields': sorted(extra),
        'suggestions': suggestions
    }


def print_analysis_report(analysis: Dict[str, Any], comparison: Dict[str, Any] = None):
    """Print a formatted analysis report."""
    print("\n" + "="*60)
    print("EDI JSON STRUCTURE ANALYSIS")
    print("="*60)

    print(f"\n📊 Structure Overview:")
    print(f"   Total unique paths: {analysis['total_paths']}")
    print(f"   Top-level fields: {analysis['top_level_count']}")

    if analysis['segment_fields']:
        print(f"\n📋 Segment Reference Fields ({len(analysis['segment_fields'])}):")
        for field in analysis['segment_fields'][:10]:
            print(f"   • {field}")
        if len(analysis['segment_fields']) > 10:
            print(f"   ... and {len(analysis['segment_fields']) - 10} more")

    if analysis['array_fields']:
        print(f"\n📦 Array Fields ({len(analysis['array_fields'])}):")
        for field in analysis['array_fields']:
            print(f"   • {field}")

    if analysis['nested_fields']:
        print(f"\n🔗 Nested Object Fields ({len(analysis['nested_fields'])}):")
        for field in analysis['nested_fields'][:10]:
            print(f"   • {field}")
        if len(analysis['nested_fields']) > 10:
            print(f"   ... and {len(analysis['nested_fields']) - 10} more")

    if analysis['data_fields']:
        print(f"\n📝 Data Fields ({len(analysis['data_fields'])}):")
        for field in analysis['data_fields'][:15]:
            print(f"   • {field}")
        if len(analysis['data_fields']) > 15:
            print(f"   ... and {len(analysis['data_fields']) - 15} more")

    if comparison:
        print("\n" + "="*60)
        print(f"DATA EXTRACTOR COMPARISON (DocType: {comparison['doctype']})")
        print("="*60)

        if comparison['matched_count'] > 0:
            print(f"\n✅ Matched Fields ({comparison['matched_count']}):")
            for field in comparison['matched_fields'][:5]:
                print(f"   • {field}")
            if comparison['matched_count'] > 5:
                print(f"   ... and {comparison['matched_count'] - 5} more")

        if comparison['missing_count'] > 0:
            print(f"\n⚠️ Expected but NOT FOUND ({comparison['missing_count']}):")
            for field in comparison['missing_fields']:
                suggestion = comparison['suggestions'].get(field)
                if suggestion:
                    print(f"   • {field}")
                    print(f"     → Possible match: \"{suggestion}\"")
                else:
                    print(f"   • {field}")

        if comparison['extra_count'] > 0:
            print(f"\n📌 Found but NOT in Extractor ({comparison['extra_count']}):")
            for field in sorted(comparison['extra_fields'])[:15]:
                print(f"   • {field}")
            if comparison['extra_count'] > 15:
                print(f"   ... and {comparison['extra_count'] - 15} more")

        # Summary assessment
        print("\n" + "-"*60)
        if comparison['missing_count'] == 0:
            print("✅ ASSESSMENT: All expected fields found in JSON")
        elif comparison['missing_count'] < 5:
            print(f"⚠️ ASSESSMENT: Minor issues - {comparison['missing_count']} expected fields not found")
        else:
            print(f"❌ ASSESSMENT: Major issues - {comparison['missing_count']} expected fields not found")
            print("   The data extractor may need updates for this partner's JSON format")

        if comparison['suggestions']:
            print("\n💡 SUGGESTIONS:")
            print("   The data extractor expects different field names than what's in the JSON.")
            print("   Consider updating the extract function to handle both patterns:")
            for expected, actual in comparison['suggestions'].items():
                print(f"   • ediData['{expected}'] || ediData['{actual}']")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze EDI JSON structure vs Data Extractor expectations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze 824 record and compare to extractor
  python3 analyze_json_fields.py --record-id 9405472 --doctype 824 --env sb2

  # Just show the JSON structure without comparison
  python3 analyze_json_fields.py --record-id 9405472 --show-structure --env sb2

  # Show raw JSON for debugging
  python3 analyze_json_fields.py --record-id 9405472 --show-json --env sb2

  # List all top-level fields
  python3 analyze_json_fields.py --record-id 9405472 --list-fields --env sb2
        """
    )

    parser.add_argument(
        '--record-id', '-r',
        required=True,
        help='EDI History record ID to analyze'
    )
    parser.add_argument(
        '--doctype', '-d',
        choices=['810', '850', '855', '856', '820', '824', '860'],
        help='Document type for comparison (optional if just analyzing structure)'
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
        '--show-json',
        action='store_true',
        help='Show the raw JSON (truncated)'
    )
    parser.add_argument(
        '--show-structure',
        action='store_true',
        help='Show structure analysis only (no comparison)'
    )
    parser.add_argument(
        '--list-fields',
        action='store_true',
        help='List all top-level field names'
    )
    parser.add_argument(
        '--json-output',
        action='store_true',
        help='Output results as JSON instead of formatted text'
    )

    args = parser.parse_args()

    # Fetch the record
    result = fetch_record_json(args.record_id, args.account, args.env)

    if not result.get('success'):
        error_msg = result.get('error', {}).get('message', 'Unknown error')
        print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)

    edi_json = result.get('edi_json', {})

    if not edi_json:
        print("Error: Record has no JSON data", file=sys.stderr)
        sys.exit(1)

    # Show raw JSON if requested
    if args.show_json:
        print("\n📄 RAW JSON (first 5000 chars):")
        print("-"*60)
        raw = json.dumps(edi_json, indent=2)
        print(raw[:5000])
        if len(raw) > 5000:
            print(f"\n... truncated ({len(raw)} total chars)")
        print()

    # List fields only
    if args.list_fields:
        fields = get_top_level_fields(edi_json)
        print("\n📋 TOP-LEVEL FIELDS:")
        for field in fields:
            value = edi_json[field]
            if isinstance(value, list):
                print(f"  • {field} (array, {len(value)} items)")
            elif isinstance(value, dict):
                print(f"  • {field} (object)")
            else:
                preview = str(value)[:50]
                if len(str(value)) > 50:
                    preview += "..."
                print(f"  • {field}: {preview}")
        sys.exit(0)

    # Analyze structure
    analysis = analyze_structure(edi_json)

    # Compare to expected if doctype provided
    comparison = None
    if args.doctype and not args.show_structure:
        expected = EXPECTED_FIELDS.get(args.doctype, [])
        actual_fields = get_top_level_fields(edi_json)
        comparison = compare_fields(set(actual_fields), expected, args.doctype)

    # Output
    if args.json_output:
        output = {
            'record_id': args.record_id,
            'doc_type_id': result.get('doc_type_id'),
            'analysis': analysis
        }
        if comparison:
            output['comparison'] = comparison
        print(json.dumps(output, indent=2))
    else:
        print_analysis_report(analysis, comparison)

    # Exit code based on comparison results
    if comparison and comparison['missing_count'] > 5:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()

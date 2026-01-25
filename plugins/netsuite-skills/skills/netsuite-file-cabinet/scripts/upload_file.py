#!/usr/bin/env python3
"""
NetSuite File Upload

Upload files to NetSuite File Cabinet via the NetSuite API Gateway.
- Uses fileCreate procedure for new files (--folder-id)
- Uses fileUpdate procedure for existing files (--file-id)

Usage:
  python3 upload_file.py --file ./script.js --folder-id 137935 --env prod
  python3 upload_file.py --file ./script.js --file-id 52794157 --env sb2
  python3 upload_file.py --file ./script.js --name "custom.js" --folder-id 137935 --env sb2
"""

import sys
import os
import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

# NetSuite API Gateway endpoint
GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# Account aliases
ACCOUNT_ALIASES = {
    'twx': 'twistedx', 'twisted': 'twistedx', 'twistedx': 'twistedx',
    'dm': 'dutyman', 'duty': 'dutyman', 'dutyman': 'dutyman'
}

# Environment aliases
ENV_ALIASES = {
    'prod': 'production', 'production': 'production',
    'sb1': 'sandbox', 'sandbox': 'sandbox', 'sandbox1': 'sandbox',
    'sb2': 'sandbox2', 'sandbox2': 'sandbox2'
}

# File type mapping by extension
FILE_TYPES = {
    '.js': 'JAVASCRIPT',
    '.json': 'JSON',
    '.xml': 'XMLDOC',
    '.html': 'HTMLDOC',
    '.htm': 'HTMLDOC',
    '.css': 'STYLESHEET',
    '.txt': 'PLAINTEXT',
    '.csv': 'CSV',
    '.pdf': 'PDF',
    '.png': 'PNGIMAGE',
    '.jpg': 'JPGIMAGE',
    '.jpeg': 'JPGIMAGE',
    '.gif': 'GIFIMAGE',
    '.zip': 'ZIP',
}

# Binary file types that need base64 encoding
BINARY_TYPES = {'PDF', 'PNGIMAGE', 'JPGIMAGE', 'GIFIMAGE', 'ZIP'}

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def get_file_type(filename: str) -> str:
    """Determine NetSuite file type from extension."""
    ext = os.path.splitext(filename)[1].lower()
    return FILE_TYPES.get(ext, 'PLAINTEXT')


def upload_file(
    file_path: str,
    folder_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """
    Upload a file to NetSuite File Cabinet.

    Args:
        file_path: Local path to file
        folder_id: NetSuite folder internal ID
        name: Override filename (optional)
        description: File description (optional)
        account: NetSuite account
        environment: NetSuite environment

    Returns:
        Dictionary with file info or error
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Validate account
    if resolved_account not in ['twistedx', 'dutyman']:
        return {'error': f"Invalid account: {account}"}

    # Validate environment
    if resolved_env not in ['production', 'sandbox', 'sandbox2']:
        return {'error': f"Invalid environment: {environment}"}

    # Read file
    if not os.path.exists(file_path):
        return {'error': f"File not found: {file_path}"}

    filename = name or os.path.basename(file_path)
    file_type = get_file_type(filename)

    # Read and encode content
    if file_type in BINARY_TYPES:
        with open(file_path, 'rb') as f:
            contents = base64.b64encode(f.read()).decode('utf-8')
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            contents = f.read()

    # Build payload
    payload = {
        'action': 'execute',
        'procedure': 'fileCreate',
        'name': filename,
        'fileType': file_type,
        'contents': contents,
        'description': description or f'Uploaded via netsuite-file-cabinet skill',
        'encoding': 'UTF-8',
        'folderID': folder_id,
        'isOnline': False,
        'isInactive': False,
        'netsuiteAccount': resolved_account,
        'netsuiteEnvironment': resolved_env
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            GATEWAY_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'http://localhost:3000'
            }
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))

            if result.get('success'):
                file_info = result.get('data', {}).get('file', {}).get('info', {})
                return {
                    'success': True,
                    'file_id': file_info.get('id'),
                    'name': file_info.get('name'),
                    'folder': file_info.get('folder'),
                    'account': resolved_account,
                    'environment': resolved_env
                }
            else:
                return {
                    'error': result.get('error', {}).get('message', 'Unknown error'),
                    'account': resolved_account,
                    'environment': resolved_env
                }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get('error', {}).get('message', error_body)
        except:
            error_msg = error_body
        return {'error': f'HTTP {e.code}: {error_msg}'}

    except urllib.error.URLError as e:
        return {'error': f'Gateway connection error: {str(e.reason)}'}

    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


def get_file_info(
    file_id: int,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """
    Get file metadata from NetSuite by file ID using SuiteQL.

    Args:
        file_id: NetSuite file internal ID
        account: NetSuite account
        environment: NetSuite environment

    Returns:
        Dictionary with file info (name, folder) or error
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    payload = {
        'action': 'queryRun',
        'procedure': 'queryRun',
        'query': f'SELECT id, name, folder FROM file WHERE id = {file_id}',
        'params': [],
        'returnAllRows': False,
        'netsuiteAccount': resolved_account,
        'netsuiteEnvironment': resolved_env
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            GATEWAY_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'http://localhost:3000'
            }
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))

            if result.get('success'):
                records = result.get('data', {}).get('records', [])
                if records and len(records) > 0:
                    record = records[0]
                    return {
                        'success': True,
                        'id': record.get('id'),
                        'name': record.get('name'),
                        'folder': record.get('folder')
                    }
                else:
                    return {'error': f'File not found: {file_id}'}
            else:
                return {'error': result.get('error', {}).get('message', 'Query failed')}

    except Exception as e:
        return {'error': f'Failed to get file info: {str(e)}'}


def update_file(
    file_path: str,
    file_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """
    Update an existing file in NetSuite File Cabinet by its ID.

    This works by:
    1. Looking up the file's current folder via SuiteQL
    2. Using fileCreate to overwrite the file (using existing name unless --name provided)

    Args:
        file_path: Local path to file with new contents
        file_id: NetSuite file internal ID to update
        name: New filename (optional, uses existing filename if not provided)
        description: New description (optional)
        account: NetSuite account
        environment: NetSuite environment

    Returns:
        Dictionary with file info or error
    """
    # First, get the existing file's info (folder and name)
    file_info = get_file_info(file_id, account, environment)
    if not file_info.get('success'):
        return file_info

    folder_id = file_info.get('folder')
    existing_name = file_info.get('name')

    if not folder_id:
        return {'error': f'Could not determine folder for file {file_id}'}

    # Use existing name if no override provided
    final_name = name or existing_name

    # Now upload using the folder ID (which will overwrite by name)
    return upload_file(file_path, folder_id, final_name, description, account, environment)


def print_usage():
    print("""NetSuite File Upload

Usage: python3 upload_file.py --file <path> --folder-id <id> [options]
       python3 upload_file.py --file <path> --file-id <id> [options]

Required (one of):
  --folder-id <id>       NetSuite folder internal ID (creates/overwrites by name)
  --file-id <id>         NetSuite file internal ID (updates existing file by ID)

Required:
  --file <path>          Local file to upload

Options:
  --name <name>          Override filename in NetSuite
  --description <desc>   File description
  --account <account>    Account (default: twistedx)
  --env <environment>    Environment (default: sandbox2)

Examples:
  # Upload new file to folder
  python3 upload_file.py --file ./myScript.js --folder-id 137935 --env prod

  # Update existing file by ID (useful when you know the file ID)
  python3 upload_file.py --file ./myScript.js --file-id 52794157 --env sb2

  # Upload with custom name
  python3 upload_file.py --file ./local.js --name "remote.js" --folder-id 137935 --env sb2

Supported File Types:
  .js (JAVASCRIPT), .json (JSON), .xml (XMLDOC), .html (HTMLDOC),
  .css (STYLESHEET), .txt (PLAINTEXT), .csv (CSV), .pdf (PDF),
  .png/.jpg/.gif (images), .zip (ZIP)

Note: --folder-id overwrites by filename, --file-id updates by internal ID.
""")


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        sys.exit(0)

    file_path = None
    folder_id = None
    file_id = None
    name = None
    description = None
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--file' and i + 1 < len(sys.argv):
            file_path = sys.argv[i + 1]
            i += 2
        elif arg == '--folder-id' and i + 1 < len(sys.argv):
            folder_id = int(sys.argv[i + 1])
            i += 2
        elif arg == '--file-id' and i + 1 < len(sys.argv):
            file_id = int(sys.argv[i + 1])
            i += 2
        elif arg == '--name' and i + 1 < len(sys.argv):
            name = sys.argv[i + 1]
            i += 2
        elif arg == '--description' and i + 1 < len(sys.argv):
            description = sys.argv[i + 1]
            i += 2
        elif arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
            i += 2
        elif arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    # Validate required arguments
    if not file_path:
        print("ERROR: --file is required")
        print_usage()
        sys.exit(1)

    if not folder_id and not file_id:
        print("ERROR: Either --folder-id or --file-id is required")
        print_usage()
        sys.exit(1)

    if folder_id and file_id:
        print("ERROR: Cannot specify both --folder-id and --file-id")
        print_usage()
        sys.exit(1)

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Use appropriate function based on argument
    if file_id:
        print(f"Updating file {file_id} in {resolved_account}/{resolved_env}...")
        result = update_file(file_path, file_id, name, description, account, environment)
        action = "updated"
    else:
        print(f"Uploading to {resolved_account}/{resolved_env}...")
        result = upload_file(file_path, folder_id, name, description, account, environment)
        action = "uploaded"

    if result.get('success'):
        print(f"SUCCESS: File {action}")
        print(f"  File ID: {result.get('file_id')}")
        print(f"  Name: {result.get('name')}")
        print(f"  Folder: {result.get('folder')}")
    else:
        print(f"ERROR: {result.get('error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()

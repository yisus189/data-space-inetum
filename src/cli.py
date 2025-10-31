#!/usr/bin/env python3
"""
Data Space CLI - Console interface for Data Space operations
Provides clear step-by-step output for all operations
"""
import sys
import os
import json
import argparse
import requests
from typing import Optional
from datetime import datetime

# Default API configuration
API_URL = os.getenv("DATASPACE_API_URL", "http://localhost:8000")
TOKEN = os.getenv("DATASPACE_TOKEN", "")


class Colors:
    """ANSI color codes for console output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_step(text: str):
    """Print a step"""
    print(f"{Colors.OKBLUE}▶{Colors.ENDC} {text}")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {text}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗{Colors.ENDC} {text}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {text}")


def print_json(data: dict):
    """Print JSON data in a readable format"""
    print(json.dumps(data, indent=2))


def get_headers() -> dict:
    """Get request headers with authentication"""
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def make_request(method: str, endpoint: str, data: Optional[dict] = None) -> dict:
    """Make HTTP request to API"""
    url = f"{API_URL}{endpoint}"
    headers = get_headers()
    
    print_step(f"Making {method} request to {endpoint}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        result = response.json()
        print_success(f"Request successful (status: {response.status_code})")
        return result
        
    except requests.RequestException as e:
        print_error(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print_error(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print_error(f"Response: {e.response.text}")
        sys.exit(1)


def cmd_publish(args):
    """Publish a dataset"""
    print_header("PUBLISH DATASET")
    
    print_step(f"Publishing: {args.title}")
    if args.description:
        print(f"  Description: {args.description}")
    
    data = {
        "title": args.title,
        "description": args.description or "",
        "metadata": {}
    }
    
    if args.metadata:
        try:
            data["metadata"] = json.loads(args.metadata)
            print(f"  Metadata: {args.metadata}")
        except json.JSONDecodeError:
            print_error("Invalid JSON in metadata")
            sys.exit(1)
    
    result = make_request("POST", "/publications", data)
    
    print_success("Publication created successfully!")
    print(f"\n{Colors.BOLD}Publication Details:{Colors.ENDC}")
    print(f"  ID: {result['id']}")
    print(f"  Title: {result['title']}")
    print(f"  Description: {result.get('description', 'N/A')}")
    print(f"  Created: {result['created_at']}")


def cmd_request(args):
    """Create a data request"""
    print_header("CREATE DATA REQUEST")
    
    print_step(f"Creating request: {args.subject}")
    if args.publication_id:
        print(f"  For publication: {args.publication_id}")
    
    data = {
        "subject": args.subject,
        "publication_id": args.publication_id
    }
    
    result = make_request("POST", "/requests", data)
    
    print_success("Request created successfully!")
    print(f"\n{Colors.BOLD}Request Details:{Colors.ENDC}")
    print(f"  ID: {result['id']}")
    print(f"  Subject: {result['subject']}")
    print(f"  State: {result['state']}")
    print(f"  Created: {result['created_at']}")


def cmd_contract(args):
    """Create a contract"""
    print_header("CREATE CONTRACT")
    
    print_step(f"Creating contract for request: {args.request_id}")
    
    data = {
        "request_id": args.request_id,
        "terms": {}
    }
    
    if args.terms:
        try:
            data["terms"] = json.loads(args.terms)
            print(f"  Terms: {args.terms}")
        except json.JSONDecodeError:
            print_error("Invalid JSON in terms")
            sys.exit(1)
    
    result = make_request("POST", "/contracts", data)
    
    print_success("Contract created and implicitly signed!")
    print(f"\n{Colors.BOLD}Contract Details:{Colors.ENDC}")
    print(f"  ID: {result['id']}")
    print(f"  Request ID: {result['request_id']}")
    print(f"  State: {result['state']}")
    print(f"  Signed: {result['signed_at']}")


def cmd_transfer(args):
    """Create a data transfer"""
    print_header("CREATE DATA TRANSFER")
    
    print_step(f"Creating transfer for contract: {args.contract_id}")
    if args.destination:
        print(f"  Destination: {args.destination}")
    
    data = {
        "contract_id": args.contract_id,
        "destination": args.destination
    }
    
    result = make_request("POST", "/transfers", data)
    
    print_success("Transfer created successfully!")
    print(f"\n{Colors.BOLD}Transfer Details:{Colors.ENDC}")
    print(f"  ID: {result['id']}")
    print(f"  Contract ID: {result['contract_id']}")
    print(f"  State: {result['state']}")
    
    if result.get('presigned_url'):
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}Presigned URL for data download:{Colors.ENDC}")
        print(f"  {result['presigned_url']}")
        print(f"\n{Colors.WARNING}Note: This URL is temporary and will expire.{Colors.ENDC}")


def cmd_sync_catalog(args):
    """Sync catalog from OpenMetadata"""
    print_header("SYNC CATALOG FROM OPENMETADATA")
    
    print_step("Initiating catalog sync...")
    print("  This will import datasets from OpenMetadata into the Data Space")
    
    result = make_request("POST", "/sync/catalog", {})
    
    print_success("Catalog sync completed!")
    print(f"\n{Colors.BOLD}Sync Results:{Colors.ENDC}")
    print(f"  Items imported: {result['items_imported']}")
    print(f"  New publications created: {result['items_created']}")
    print(f"  Message: {result['message']}")


def cmd_list_catalog(args):
    """List catalog items"""
    print_header("CATALOG LISTING")
    
    print_step("Retrieving catalog items...")
    
    result = make_request("GET", "/catalog", None)
    
    total = result['total']
    items = result['items']
    
    print_success(f"Found {total} catalog items")
    
    if total == 0:
        print_warning("No catalog items found. Run 'sync-catalog' to import from OpenMetadata.")
        return
    
    print(f"\n{Colors.BOLD}Catalog Items:{Colors.ENDC}")
    for i, item in enumerate(items, 1):
        print(f"\n{Colors.OKCYAN}[{i}] {item['title']}{Colors.ENDC}")
        print(f"    ID: {item['id']}")
        print(f"    Description: {item.get('description', 'N/A')[:100]}")
        if item.get('metadata', {}).get('tags'):
            print(f"    Tags: {', '.join(item['metadata']['tags'])}")


def cmd_download_catalog(args):
    """Download a specific catalog item"""
    print_header("DOWNLOAD CATALOG ITEM")
    
    print_step(f"Downloading catalog item: {args.catalog_id}")
    
    result = make_request("GET", f"/catalog/{args.catalog_id}/download", None)
    
    filename = args.output or f"catalog-{args.catalog_id}.json"
    
    print_step(f"Saving to file: {filename}")
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    print_success(f"Catalog item downloaded successfully!")
    print(f"  File: {filename}")
    print(f"  Title: {result['title']}")


def cmd_view_audit(args):
    """View audit logs"""
    print_header("AUDIT LOG")
    
    print_step("Retrieving audit logs...")
    params = f"?limit={args.limit}"
    if args.event_type:
        params += f"&event_type={args.event_type}"
    
    result = make_request("GET", f"/audit{params}", None)
    
    total = result['total']
    logs = result['logs']
    
    print_success(f"Found {total} audit log entries")
    
    if total == 0:
        print_warning("No audit logs found.")
        return
    
    print(f"\n{Colors.BOLD}Audit Logs (most recent first):{Colors.ENDC}")
    for i, log in enumerate(logs, 1):
        timestamp = datetime.fromisoformat(log['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{Colors.OKCYAN}[{i}] {log['event_type']}{Colors.ENDC}")
        print(f"    Time: {timestamp}")
        if log.get('user_id'):
            print(f"    User: {log['user_id']}")
        if log.get('entity_type') and log.get('entity_id'):
            print(f"    Entity: {log['entity_type']} ({log['entity_id']})")
        if log.get('payload'):
            print(f"    Details: {json.dumps(log['payload'], indent=2)}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Data Space CLI - Console interface for Data Space operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Publish a dataset
  %(prog)s publish --title "Customer Data" --description "Customer records"
  
  # Create a data request
  %(prog)s request --subject "Need customer data" --publication-id <pub-id>
  
  # Create a contract
  %(prog)s contract --request-id <req-id>
  
  # Create a transfer
  %(prog)s transfer --contract-id <contract-id>
  
  # Sync catalog from OpenMetadata
  %(prog)s sync-catalog
  
  # List catalog items
  %(prog)s list-catalog
  
  # Download catalog item
  %(prog)s download-catalog --catalog-id <id>
  
  # View audit logs
  %(prog)s view-audit --limit 50

Environment Variables:
  DATASPACE_API_URL    API URL (default: http://localhost:8000)
  DATASPACE_TOKEN      Authentication token (JWT)
        """
    )
    
    parser.add_argument('--api-url', default=API_URL, help='API URL')
    parser.add_argument('--token', default=TOKEN, help='Authentication token')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Publish command
    pub_parser = subparsers.add_parser('publish', help='Publish a dataset')
    pub_parser.add_argument('--title', required=True, help='Publication title')
    pub_parser.add_argument('--description', help='Publication description')
    pub_parser.add_argument('--metadata', help='Metadata as JSON string')
    
    # Request command
    req_parser = subparsers.add_parser('request', help='Create a data request')
    req_parser.add_argument('--subject', required=True, help='Request subject')
    req_parser.add_argument('--publication-id', help='Publication ID to request')
    
    # Contract command
    contract_parser = subparsers.add_parser('contract', help='Create a contract')
    contract_parser.add_argument('--request-id', required=True, help='Request ID')
    contract_parser.add_argument('--terms', help='Contract terms as JSON string')
    
    # Transfer command
    transfer_parser = subparsers.add_parser('transfer', help='Create a data transfer')
    transfer_parser.add_argument('--contract-id', required=True, help='Contract ID')
    transfer_parser.add_argument('--destination', help='Transfer destination')
    
    # Sync catalog command
    subparsers.add_parser('sync-catalog', help='Sync catalog from OpenMetadata')
    
    # List catalog command
    subparsers.add_parser('list-catalog', help='List catalog items')
    
    # Download catalog command
    download_parser = subparsers.add_parser('download-catalog', help='Download catalog item')
    download_parser.add_argument('--catalog-id', required=True, help='Catalog item ID')
    download_parser.add_argument('--output', help='Output filename')
    
    # View audit command
    audit_parser = subparsers.add_parser('view-audit', help='View audit logs')
    audit_parser.add_argument('--limit', type=int, default=50, help='Number of logs to show')
    audit_parser.add_argument('--event-type', help='Filter by event type')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Override API URL and token if provided
    if args.api_url:
        globals()['API_URL'] = args.api_url
    if args.token:
        globals()['TOKEN'] = args.token
    
    # Execute command
    commands = {
        'publish': cmd_publish,
        'request': cmd_request,
        'contract': cmd_contract,
        'transfer': cmd_transfer,
        'sync-catalog': cmd_sync_catalog,
        'list-catalog': cmd_list_catalog,
        'download-catalog': cmd_download_catalog,
        'view-audit': cmd_view_audit,
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        try:
            cmd_func(args)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Operation cancelled by user{Colors.ENDC}")
            sys.exit(130)
    else:
        print_error(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

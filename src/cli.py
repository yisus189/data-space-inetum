#!/usr/bin/env python3
"""
Data Space CLI - Command-line interface for interacting with the Data Space API

This CLI provides commands for:
- Publishing datasets
- Requesting access to datasets
- Creating contracts
- Initiating transfers
- Syncing catalog from OpenMetadata
- Listing catalog items
- Downloading catalog metadata
- Viewing audit logs
"""

import click
import requests
import json
import sys
from typing import Optional
from datetime import datetime
import os


class DataSpaceClient:
    """Client for Data Space API"""
    
    def __init__(self, api_url: str, token: Optional[str] = None):
        self.api_url = api_url.rstrip('/')
        self.token = token
        self.session = requests.Session()
        
        if token:
            self.session.headers.update({
                'Authorization': f'Bearer {token}'
            })
    
    def _request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request to API"""
        url = f"{self.api_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                error_detail = error_data.get('detail', str(e))
            except:
                error_detail = str(e)
            
            click.echo(f"❌ Error: {error_detail}", err=True)
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            click.echo(f"❌ Connection error: {e}", err=True)
            sys.exit(1)
    
    def get(self, endpoint: str, **kwargs):
        return self._request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs):
        return self._request('POST', endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs):
        return self._request('PUT', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs):
        return self._request('DELETE', endpoint, **kwargs)


def get_client(ctx):
    """Get Data Space client from context"""
    return ctx.obj['client']


@click.group()
@click.option('--api-url', envvar='API_URL', default='http://localhost:8000', help='Data Space API URL')
@click.option('--token', envvar='API_TOKEN', help='Authentication token')
@click.pass_context
def cli(ctx, api_url, token):
    """Data Space CLI - Interact with the Data Space API"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = DataSpaceClient(api_url, token)
    ctx.obj['api_url'] = api_url


@cli.command()
@click.option('--title', required=True, help='Publication title')
@click.option('--description', help='Publication description')
@click.option('--data-location', help='Data location')
@click.option('--tags', help='Comma-separated tags')
@click.pass_context
def publish(ctx, title, description, data_location, tags):
    """Publish a new dataset"""
    client = get_client(ctx)
    
    click.echo("📝 Creating publication...")
    click.echo(f"   Title: {title}")
    
    data = {
        'title': title,
        'description': description or '',
        'data_location': data_location,
        'tags': [t.strip() for t in tags.split(',')] if tags else [],
    }
    
    result = client.post('/publications', json=data)
    
    click.echo("✅ Publication created successfully!")
    click.echo(f"   ID: {result['id']}")
    click.echo(f"   Status: {result['status']}")
    click.echo(f"   Created: {result['created_at']}")


@cli.command()
@click.option('--publication-id', required=True, help='Publication ID to request')
@click.option('--subject', required=True, help='Request subject')
@click.option('--purpose', help='Purpose of the request')
@click.option('--intended-use', help='Intended use of the data')
@click.option('--duration', help='Duration in days')
@click.pass_context
def request(ctx, publication_id, subject, purpose, intended_use, duration):
    """Request access to a dataset"""
    client = get_client(ctx)
    
    click.echo("📝 Creating access request...")
    click.echo(f"   Publication: {publication_id}")
    click.echo(f"   Subject: {subject}")
    
    data = {
        'publication_id': publication_id,
        'subject': subject,
        'purpose': purpose,
        'intended_use': intended_use,
        'duration_days': duration,
    }
    
    result = client.post('/requests', json=data)
    
    click.echo("✅ Request created successfully!")
    click.echo(f"   ID: {result['id']}")
    click.echo(f"   Status: {result['status']}")
    click.echo(f"   Created: {result['created_at']}")


@cli.command('contract-create')
@click.option('--request-id', required=True, help='Request ID to create contract from')
@click.option('--start-date', help='Contract start date (YYYY-MM-DD)')
@click.option('--end-date', help='Contract end date (YYYY-MM-DD)')
@click.pass_context
def contract_create(ctx, request_id, start_date, end_date):
    """Create a contract from an approved request"""
    client = get_client(ctx)
    
    click.echo("📝 Creating contract...")
    click.echo(f"   Request: {request_id}")
    
    data = {
        'request_id': request_id,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    result = client.post('/contracts', json=data)
    
    click.echo("✅ Contract created successfully!")
    click.echo(f"   ID: {result['id']}")
    click.echo(f"   Status: {result['status']}")
    click.echo(f"   Signature Method: {result['signature_method']}")
    click.echo(f"   Signature Hash: {result['signature_hash']}")
    click.echo(f"   Created: {result['created_at']}")


@cli.command()
@click.option('--contract-id', required=True, help='Contract ID to initiate transfer')
@click.option('--destination', help='Transfer destination')
@click.option('--format', help='File format')
@click.pass_context
def transfer(ctx, contract_id, destination, format):
    """Initiate a data transfer"""
    client = get_client(ctx)
    
    click.echo("📝 Initiating transfer...")
    click.echo(f"   Contract: {contract_id}")
    
    data = {
        'contract_id': contract_id,
        'destination': destination,
        'file_format': format,
    }
    
    result = client.post('/transfers', json=data)
    
    click.echo("✅ Transfer initiated successfully!")
    click.echo(f"   ID: {result['id']}")
    click.echo(f"   Status: {result['status']}")
    click.echo(f"   Method: {result['transfer_method']}")
    
    if result.get('presigned_url'):
        click.echo(f"   Download URL: {result['presigned_url']}")
        click.echo(f"   Expires: {result['presigned_url_expires_at']}")


@cli.command('sync-catalog')
@click.pass_context
def sync_catalog(ctx):
    """Sync catalog from OpenMetadata"""
    client = get_client(ctx)
    
    click.echo("🔄 Syncing catalog from OpenMetadata...")
    
    result = client.post('/catalog/sync')
    
    click.echo("✅ Catalog synced successfully!")
    click.echo(f"   Items imported: {result['imported']}")
    click.echo(f"   Message: {result['message']}")


@cli.command('list-catalog')
@click.option('--limit', default=10, help='Number of items to show')
@click.pass_context
def list_catalog(ctx, limit):
    """List catalog items"""
    client = get_client(ctx)
    
    click.echo("📚 Fetching catalog items...")
    
    result = client.get(f'/catalog?limit={limit}')
    
    if not result:
        click.echo("No catalog items found.")
        return
    
    click.echo(f"\n{'ID':<38} {'Title':<40} {'Tags':<30}")
    click.echo("-" * 110)
    
    for item in result:
        tags = ', '.join(item.get('tags', [])[:3])
        click.echo(f"{item['id']:<38} {item['title'][:40]:<40} {tags[:30]:<30}")
    
    click.echo(f"\nTotal items: {len(result)}")


@cli.command('download-catalog')
@click.option('--catalog-id', required=True, help='Catalog item ID to download')
@click.option('--output', help='Output file path')
@click.pass_context
def download_catalog(ctx, catalog_id, output):
    """Download catalog item metadata"""
    client = get_client(ctx)
    
    click.echo(f"📥 Downloading catalog metadata...")
    click.echo(f"   ID: {catalog_id}")
    
    # Use session to get raw response
    url = f"{ctx.obj['api_url']}/catalog/{catalog_id}/download"
    response = client.session.get(url)
    response.raise_for_status()
    
    # Determine output file
    if not output:
        output = f"catalog_{catalog_id}.json"
    
    # Write to file
    with open(output, 'w') as f:
        f.write(response.text)
    
    click.echo(f"✅ Metadata downloaded to: {output}")
    
    # Pretty print summary
    try:
        data = response.json()
        click.echo(f"\n   Title: {data.get('title')}")
        click.echo(f"   Description: {data.get('description', 'N/A')}")
        click.echo(f"   Tags: {', '.join(data.get('tags', []))}")
    except:
        pass


@cli.command('view-audit')
@click.option('--limit', default=20, help='Number of logs to show')
@click.option('--event-type', help='Filter by event type')
@click.option('--category', help='Filter by category')
@click.option('--actor', help='Filter by actor username')
@click.pass_context
def view_audit(ctx, limit, event_type, category, actor):
    """View audit logs"""
    client = get_client(ctx)
    
    click.echo("📋 Fetching audit logs...")
    
    params = {'limit': limit}
    if event_type:
        params['event_type'] = event_type
    if category:
        params['event_category'] = category
    if actor:
        params['actor_username'] = actor
    
    result = client.get('/audit', params=params)
    
    if not result:
        click.echo("No audit logs found.")
        return
    
    click.echo(f"\n{'Timestamp':<20} {'Event Type':<30} {'Actor':<20} {'Status':<10}")
    click.echo("-" * 85)
    
    for log in result:
        timestamp = log['created_at'][:19]  # Truncate microseconds
        event_type = log['event_type'][:30]
        actor = (log.get('actor_username') or 'system')[:20]
        status = (log.get('status') or 'N/A')[:10]
        
        click.echo(f"{timestamp:<20} {event_type:<30} {actor:<20} {status:<10}")
    
    click.echo(f"\nTotal logs: {len(result)}")


@cli.command('list-publications')
@click.option('--limit', default=10, help='Number of items to show')
@click.pass_context
def list_publications(ctx, limit):
    """List publications"""
    client = get_client(ctx)
    
    click.echo("📚 Fetching publications...")
    
    result = client.get(f'/publications?limit={limit}')
    
    if not result:
        click.echo("No publications found.")
        return
    
    click.echo(f"\n{'ID':<38} {'Title':<40} {'Status':<15}")
    click.echo("-" * 95)
    
    for item in result:
        click.echo(f"{item['id']:<38} {item['title'][:40]:<40} {item['status']:<15}")
    
    click.echo(f"\nTotal: {len(result)}")


@cli.command('list-requests')
@click.option('--limit', default=10, help='Number of items to show')
@click.pass_context
def list_requests(ctx, limit):
    """List requests"""
    client = get_client(ctx)
    
    click.echo("📚 Fetching requests...")
    
    result = client.get(f'/requests?limit={limit}')
    
    if not result:
        click.echo("No requests found.")
        return
    
    click.echo(f"\n{'ID':<38} {'Subject':<40} {'Status':<15}")
    click.echo("-" * 95)
    
    for item in result:
        click.echo(f"{item['id']:<38} {item['subject'][:40]:<40} {item['status']:<15}")
    
    click.echo(f"\nTotal: {len(result)}")


@cli.command('list-contracts')
@click.option('--limit', default=10, help='Number of items to show')
@click.pass_context
def list_contracts(ctx, limit):
    """List contracts"""
    client = get_client(ctx)
    
    click.echo("📚 Fetching contracts...")
    
    result = client.get(f'/contracts?limit={limit}')
    
    if not result:
        click.echo("No contracts found.")
        return
    
    click.echo(f"\n{'ID':<38} {'Status':<15} {'Created':<20}")
    click.echo("-" * 75)
    
    for item in result:
        created = item['created_at'][:19]
        click.echo(f"{item['id']:<38} {item['status']:<15} {created:<20}")
    
    click.echo(f"\nTotal: {len(result)}")


@cli.command('list-transfers')
@click.option('--limit', default=10, help='Number of items to show')
@click.pass_context
def list_transfers(ctx, limit):
    """List transfers"""
    client = get_client(ctx)
    
    click.echo("📚 Fetching transfers...")
    
    result = client.get(f'/transfers?limit={limit}')
    
    if not result:
        click.echo("No transfers found.")
        return
    
    click.echo(f"\n{'ID':<38} {'Status':<15} {'Method':<20}")
    click.echo("-" * 75)
    
    for item in result:
        method = item.get('transfer_method', 'N/A')
        click.echo(f"{item['id']:<38} {item['status']:<15} {method:<20}")
    
    click.echo(f"\nTotal: {len(result)}")


if __name__ == '__main__':
    cli()

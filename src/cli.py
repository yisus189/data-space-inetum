"""CLI tool for Data Space operations."""

import os
import sys
import json
import click
import requests
from typing import Optional
from datetime import datetime

API_URL = os.getenv("API_URL", "http://localhost:8000")


class DataSpaceClient:
    """Client for Data Space API."""
    
    def __init__(self, api_url: str, token: Optional[str] = None):
        self.api_url = api_url
        self.token = token
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def login(self, username: str, password: str) -> dict:
        """Authenticate and get token."""
        response = requests.post(
            f"{self.api_url}/auth/token",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()
    
    def create_publication(self, title: str, description: str = None, 
                          metadata: dict = None, s3_path: str = None) -> dict:
        """Create a publication."""
        data = {
            "title": title,
            "description": description,
            "metadata": metadata or {},
            "s3_path": s3_path
        }
        response = requests.post(
            f"{self.api_url}/publications",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def list_publications(self) -> list:
        """List publications."""
        response = requests.get(
            f"{self.api_url}/publications",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def create_request(self, subject: str, publication_id: int, message: str = None) -> dict:
        """Create a data access request."""
        data = {
            "subject": subject,
            "publication_id": publication_id,
            "message": message
        }
        response = requests.post(
            f"{self.api_url}/requests",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def list_requests(self, as_requester: bool = False, as_provider: bool = False) -> list:
        """List requests."""
        params = {}
        if as_requester:
            params["as_requester"] = "true"
        if as_provider:
            params["as_provider"] = "true"
        
        response = requests.get(
            f"{self.api_url}/requests",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def create_contract(self, request_id: int, terms: dict = None) -> dict:
        """Create a contract."""
        data = {
            "request_id": request_id,
            "terms": terms or {}
        }
        response = requests.post(
            f"{self.api_url}/contracts",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def create_transfer(self, contract_id: int, destination: str = None) -> dict:
        """Initiate a transfer."""
        data = {
            "contract_id": contract_id,
            "destination": destination
        }
        response = requests.post(
            f"{self.api_url}/transfers",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def sync_catalog(self) -> dict:
        """Sync catalog from OpenMetadata."""
        response = requests.post(
            f"{self.api_url}/catalog/sync",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def list_catalog(self) -> list:
        """List catalog items."""
        response = requests.get(
            f"{self.api_url}/catalog",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def download_catalog_metadata(self, publication_id: int, output_file: str):
        """Download catalog metadata."""
        response = requests.get(
            f"{self.api_url}/catalog/{publication_id}/download",
            headers=self.headers
        )
        response.raise_for_status()
        
        with open(output_file, 'w') as f:
            f.write(response.text)
    
    def list_audit_logs(self, limit: int = 100) -> list:
        """List audit logs."""
        response = requests.get(
            f"{self.api_url}/audit",
            headers=self.headers,
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()


@click.group()
@click.option('--api-url', default=API_URL, help='API URL')
@click.option('--token', help='Access token (or use login command)')
@click.pass_context
def cli(ctx, api_url, token):
    """Data Space CLI - Manage publications, requests, contracts, and transfers."""
    ctx.ensure_object(dict)
    ctx.obj['client'] = DataSpaceClient(api_url, token)
    ctx.obj['api_url'] = api_url


@cli.command()
@click.option('--username', prompt=True, help='Username')
@click.option('--password', prompt=True, hide_input=True, help='Password')
@click.pass_context
def login(ctx, username, password):
    """Login and get access token."""
    client = ctx.obj['client']
    
    click.echo("🔐 Authenticating...")
    try:
        result = client.login(username, password)
        click.echo(f"✅ Login successful!")
        click.echo(f"📋 Access Token: {result['access_token']}")
        click.echo(f"⏰ Expires in: {result['expires_in']} seconds")
        click.echo("\nUse this token with other commands:")
        click.echo(f"  --token {result['access_token']}")
    except requests.HTTPError as e:
        click.echo(f"❌ Login failed: {e.response.text}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--title', prompt=True, help='Publication title')
@click.option('--description', help='Publication description')
@click.option('--s3-path', help='S3 path to data')
@click.pass_context
def publish(ctx, title, description, s3_path):
    """Create a new publication."""
    client = ctx.obj['client']
    
    click.echo("📤 Creating publication...")
    try:
        result = client.create_publication(title, description, s3_path=s3_path)
        click.echo(f"✅ Publication created!")
        click.echo(f"📋 ID: {result['id']}")
        click.echo(f"📝 Title: {result['title']}")
        click.echo(f"👤 Owner ID: {result['owner_id']}")
        click.echo(f"📊 Status: {result['status']}")
    except requests.HTTPError as e:
        click.echo(f"❌ Failed to create publication: {e.response.text}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--publication-id', type=int, prompt=True, help='Publication ID')
@click.option('--subject', prompt=True, help='Request subject')
@click.option('--message', help='Request message')
@click.pass_context
def request(ctx, publication_id, subject, message):
    """Create a data access request."""
    client = ctx.obj['client']
    
    click.echo("📨 Creating request...")
    try:
        result = client.create_request(subject, publication_id, message)
        click.echo(f"✅ Request created!")
        click.echo(f"📋 ID: {result['id']}")
        click.echo(f"📝 Subject: {result['subject']}")
        click.echo(f"📊 Status: {result['status']}")
        click.echo(f"🎯 Publication ID: {result['publication_id']}")
    except requests.HTTPError as e:
        click.echo(f"❌ Failed to create request: {e.response.text}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--request-id', type=int, prompt=True, help='Request ID')
@click.pass_context
def contract_create(ctx, request_id):
    """Create a contract from an approved request."""
    client = ctx.obj['client']
    
    click.echo("📄 Creating contract...")
    try:
        result = client.create_contract(request_id)
        click.echo(f"✅ Contract created!")
        click.echo(f"📋 ID: {result['id']}")
        click.echo(f"📊 Status: {result['status']}")
        click.echo(f"🔒 Signed at: {result['signed_at']}")
        click.echo(f"🎯 Request ID: {result['request_id']}")
    except requests.HTTPError as e:
        click.echo(f"❌ Failed to create contract: {e.response.text}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--contract-id', type=int, prompt=True, help='Contract ID')
@click.option('--destination', help='Transfer destination')
@click.pass_context
def transfer(ctx, contract_id, destination):
    """Initiate a data transfer."""
    client = ctx.obj['client']
    
    click.echo("🚀 Initiating transfer...")
    try:
        result = client.create_transfer(contract_id, destination)
        click.echo(f"✅ Transfer initiated!")
        click.echo(f"📋 ID: {result['id']}")
        click.echo(f"📊 Status: {result['status']}")
        click.echo(f"🎯 Contract ID: {result['contract_id']}")
        
        if result.get('presigned_url'):
            click.echo(f"🔗 Download URL: {result['presigned_url']}")
            click.echo("   (Valid for 1 hour)")
    except requests.HTTPError as e:
        click.echo(f"❌ Failed to initiate transfer: {e.response.text}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def sync_catalog(ctx):
    """Sync catalog from OpenMetadata."""
    client = ctx.obj['client']
    
    click.echo("🔄 Syncing catalog from OpenMetadata...")
    try:
        result = client.sync_catalog()
        click.echo(f"✅ Catalog synced!")
        click.echo(f"📊 Imported: {result['imported_count']} items")
        click.echo(f"🔍 Source: {result['source']}")
        
        if result['source'] == 'mock':
            click.echo("⚠️  Using mock data (OpenMetadata unavailable)")
        
        if result.get('publication_ids'):
            click.echo(f"📋 Publication IDs: {', '.join(map(str, result['publication_ids']))}")
    except requests.HTTPError as e:
        click.echo(f"❌ Failed to sync catalog: {e.response.text}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def list_catalog(ctx):
    """List catalog items."""
    client = ctx.obj['client']
    
    click.echo("📚 Listing catalog...")
    try:
        items = client.list_catalog()
        
        if not items:
            click.echo("No catalog items found")
            return
        
        click.echo(f"\nFound {len(items)} catalog items:\n")
        for item in items:
            click.echo(f"📋 ID: {item['id']}")
            click.echo(f"   Title: {item['title']}")
            click.echo(f"   Description: {item.get('description', 'N/A')}")
            click.echo(f"   Status: {item['status']}")
            click.echo(f"   Owner ID: {item['owner_id']}")
            click.echo()
    except requests.HTTPError as e:
        click.echo(f"❌ Failed to list catalog: {e.response.text}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--publication-id', type=int, prompt=True, help='Publication ID')
@click.option('--output', default='catalog_metadata.json', help='Output file')
@click.pass_context
def download_catalog(ctx, publication_id, output):
    """Download catalog metadata."""
    client = ctx.obj['client']
    
    click.echo(f"📥 Downloading catalog metadata...")
    try:
        client.download_catalog_metadata(publication_id, output)
        click.echo(f"✅ Metadata downloaded to: {output}")
    except requests.HTTPError as e:
        click.echo(f"❌ Failed to download metadata: {e.response.text}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--limit', default=20, help='Number of logs to display')
@click.pass_context
def view_audit(ctx, limit):
    """View audit logs."""
    client = ctx.obj['client']
    
    click.echo("📜 Fetching audit logs...")
    try:
        logs = client.list_audit_logs(limit)
        
        if not logs:
            click.echo("No audit logs found")
            return
        
        click.echo(f"\nShowing {len(logs)} recent audit logs:\n")
        for log in logs:
            timestamp = log['created_at']
            click.echo(f"🕐 {timestamp}")
            click.echo(f"   Event: {log['event_type']}")
            if log.get('entity_type'):
                click.echo(f"   Entity: {log['entity_type']} (ID: {log.get('entity_id', 'N/A')})")
            if log.get('user_id'):
                click.echo(f"   User ID: {log['user_id']}")
            click.echo()
    except requests.HTTPError as e:
        click.echo(f"❌ Failed to fetch audit logs: {e.response.text}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli(obj={})

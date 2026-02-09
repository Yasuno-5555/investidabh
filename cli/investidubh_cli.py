import os
import json
import sys
from pathlib import Path

# --- 1. Dependency Check ---
try:
    import click
    import requests
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown
except ImportError as e:
    print(f"Error: Missing dependency '{e.name}'.")
    print("Please run: pip install -r cli/requirements.txt")
    sys.exit(1)

# Initialize Console
console = Console()
TOKEN_FILE = Path.home() / ".investidubh_token"

# --- 2. Helper Functions ---
def get_token():
    if not TOKEN_FILE.exists():
        return None
    return TOKEN_FILE.read_text().strip()

def save_token(token):
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)

def api_request(ctx, method, endpoint, data=None, params=None):
    """
    Robust API Request Wrapper
    - ctx: Click context (for API_URL)
    - Handle Connection Errors
    - Handle JSON Parse Errors
    - Handle 4xx/5xx Gracefully
    """
    api_url = ctx.obj.get('API_URL')
    token = get_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    url = f"{api_url}/api{endpoint}"
    
    try:
        response = requests.request(method, url, json=data, params=params, headers=headers)
        
        # Unauthorized Catch
        if response.status_code == 401:
            console.print("[bold red]Error:[/bold red] Unauthorized. Please run [bold]auth login[/bold].")
            sys.exit(1)
            
        return response

    except requests.exceptions.ConnectionError:
        console.print(f"[bold red]Connection Error:[/bold red] Could not connect to {api_url}")
        console.print("Suggestions:")
        console.print("  1. Check if the gateway is running (docker-compose ps).")
        console.print("  2. If running remotely, use --api-url.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        sys.exit(1)

def handle_api_error(response):
    """Parse API Error Response"""
    try:
        data = response.json()
        msg = data.get('error') or data.get('message') or response.text
        console.print(f"[bold red]API Error ({response.status_code}):[/bold red] {msg}")
    except json.JSONDecodeError:
        console.print(f"[bold red]API Error ({response.status_code}):[/bold red] (Response was not JSON)")
        console.print(f"Raw Body: {response.text[:200]}...")

# --- 3. CLI Config ---
@click.group()
@click.option('--api-url', default=os.getenv("API_URL", "http://localhost:4000"), help="Base URL of the Investidubh API")
@click.pass_context
def cli(ctx, api_url):
    """Investidubh CLI - OSINT Automation Tool"""
    # Ensure ctx.obj exists
    ctx.ensure_object(dict)
    ctx.obj['API_URL'] = api_url.rstrip('/')

# --- 4. Commands ---
@cli.group()
def auth():
    """Manage authentication"""
    pass

@auth.command(name="login")
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True)
@click.pass_context
def login(ctx, username, password):
    """Log in to the platform"""
    api_url = ctx.obj.get('API_URL')
    
    try:
        # Direct request here to handle 401 specifically for login
        res = requests.post(f"{api_url}/api/auth/login", json={"username": username, "password": password})
        if res.status_code == 200:
            token = res.json().get("token")
            save_token(token)
            console.print("[green]Successfully logged in![/green]")
        else:
            handle_api_error(res)
    except requests.exceptions.ConnectionError:
        console.print(f"[bold red]Connection Error:[/bold red] Could not connect to {api_url}")

@cli.command()
@click.argument("url")
@click.pass_context
def scan(ctx, url):
    """Start a new investigation"""
    console.print(f"[*] Starting investigation for {url}...")
    res = api_request(ctx, "POST", "/investigations", data={"targetUrl": url})
    
    if res.status_code == 200:
        data = res.json()
        console.print(f"[green]Investigation queued![/green] ID: [bold]{data.get('id')}[/bold]")
    else:
        handle_api_error(res)

@cli.command(name="list")
@click.pass_context
def list_investigations(ctx):
    """List recent investigations"""
    res = api_request(ctx, "GET", "/investigations")
    
    if res.status_code == 200:
        try:
            investigations = res.json()
            table = Table(title="Recent Investigations")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Target URL", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("Created At", justify="right")

            for inv in investigations:
                status_style = "green" if inv['status'] == 'COMPLETED' else "yellow"
                table.add_row(
                    inv['id'], 
                    inv['target_url'], 
                    f"[{status_style}]{inv['status']}[/{status_style}]", 
                    inv['created_at']
                )
            console.print(table)
        except json.JSONDecodeError:
            handle_api_error(res)
    else:
        handle_api_error(res)

@cli.command()
@click.argument("id")
@click.pass_context
def show(ctx, id):
    """Show investigation details"""
    res = api_request(ctx, "GET", f"/investigations/{id}")
    
    if res.status_code == 200:
        try:
            data = res.json()
            
            # Header
            console.print(Panel(f"[bold]{data['target_url']}[/bold]\nStatus: {data['status']}", title=f"Investigation {id}"))

            # Intelligence
            if data.get('intelligence'):
                table = Table(title="Extracted Intelligence")
                table.add_column("Type", style="cyan")
                table.add_column("Value", style="white")
                table.add_column("Source", style="blue")
                
                for item in data['intelligence']:
                    table.add_row(item['entity_type'], item['value'], item.get('source_type', 'unknown'))
                console.print(table)

            # Artifacts
            if data.get('artifacts'):
                 console.print(f"\n[bold]Artifacts:[/bold] {len(data['artifacts'])} found.")
                 for art in data['artifacts']:
                     console.print(f"- {art['artifact_type']}: {art['storage_path']}")
        except json.JSONDecodeError:
            handle_api_error(res)

    elif res.status_code == 404:
        console.print("[red]Investigation not found.[/red]")
    else:
        handle_api_error(res)

@cli.command()
@click.argument("query")
@click.pass_context
def search(ctx, query):
    """Search investigations and artifacts"""
    res = api_request(ctx, "GET", "/search", params={"q": query})
    if res.status_code == 200:
        try:
            hits = res.json()
            if not hits:
                console.print("No results found.")
                return

            table = Table(title=f"Search Results: '{query}'")
            table.add_column("URL", style="magenta")
            table.add_column("Snippet", style="white")
            
            for hit in hits:
                # Handle Meilisearch highlights or raw snippet
                snippet = hit.get('_formatted', {}).get('text') or hit.get('snippet') or hit.get('text', '')[:100] + "..."
                # Strip newlines for cleaner table
                snippet = snippet.replace("\n", " ")[:100]
                table.add_row(hit.get('url', 'N/A'), snippet)
                
            console.print(table)
        except json.JSONDecodeError:
            handle_api_error(res)
    else:
        handle_api_error(res)

if __name__ == '__main__':
    cli()

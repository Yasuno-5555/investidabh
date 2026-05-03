import os
import json
import sys
from pathlib import Path

# --- 1. Dependency Check ---
try:
    import click
    import requests
    import time
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.status import Status
    import sseclient
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

@auth.command(name="register")
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.pass_context
def register(ctx, username, password):
    """Register a new account"""
    api_url = ctx.obj.get('API_URL')
    try:
        res = requests.post(f"{api_url}/api/auth/register", json={"username": username, "password": password})
        if res.status_code in [200, 201]:
            console.print("[green]Successfully registered![/green] You can now login.")
        else:
            handle_api_error(res)
    except requests.exceptions.ConnectionError:
        console.print(f"[bold red]Connection Error:[/bold red] Could not connect to {api_url}")

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
@click.argument("url", required=False)
@click.option("--wait", is_flag=True, help="Wait for the investigation to complete with a progress spinner")
@click.pass_context
def scan(ctx, url, wait):
    """Start a new investigation"""
    if not url:
        url = click.prompt("Please enter the target URL to scan")
        
    console.print(f"[*] Starting investigation for {url}...")
    res = api_request(ctx, "POST", "/investigations", data={"targetUrl": url})
    
    if res.status_code == 200:
        data = res.json()
        inv_id = data.get('id')
        console.print(f"[green]Investigation queued![/green] ID: [bold]{inv_id}[/bold]")
        
        if wait and inv_id:
            with Status(f"[bold blue]Scanning {url}...[/bold blue]", spinner="dots") as status:
                while True:
                    status_res = api_request(ctx, "GET", f"/investigations/{inv_id}")
                    if status_res.status_code == 200:
                        status_data = status_res.json()
                        inv_status = status_data.get('status')
                        if inv_status == 'COMPLETED':
                            console.print("[green]✔ Scan completed successfully![/green]")
                            break
                        elif inv_status == 'FAILED':
                            console.print("[red]✖ Scan failed.[/red]")
                            break
                    time.sleep(3)
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
@click.argument("id", required=False)
@click.pass_context
def show(ctx, id):
    """Show investigation details"""
    if not id:
        id = click.prompt("Please enter the investigation ID to show")
        
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

@cli.group()
@click.pass_context
def search(ctx):
    """Search for indicators, entities, or investigations."""
    pass

@search.command(name="investigations")
@click.argument("query")
@click.pass_context
def search_investigations(ctx, query):
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

@search.command(name="indicator")
@click.argument("query")
@click.pass_context
def search_indicator(ctx, query):
    """Search for a specific indicator (IP, domain, hash, etc.)"""
    res = api_request(ctx, "GET", f"/search/indicators", params={"q": query})
    if res.status_code == 200:
        try:
            results = res.json()
            if not results:
                console.print("No results found.")
                return

            table = Table(title=f"Indicator Search Results: '{query}'")
            table.add_column("Type", style="cyan")
            table.add_column("Value", style="magenta")
            table.add_column("First Seen", style="green")
            table.add_column("Last Seen", style="green")
            
            for item in results:
                table.add_row(
                    item.get('type', 'N/A'),
                    item.get('value', 'N/A'),
                    item.get('first_seen', 'N/A'),
                    item.get('last_seen', 'N/A')
                )
            console.print(table)
        except json.JSONDecodeError:
            handle_api_error(res)
    else:
        handle_api_error(res)

@search.command(name="entity")
@click.argument("query")
@click.pass_context
def search_entity(ctx, query):
    """Search for a specific entity (e.g., email, name, company)"""
    res = api_request(ctx, "GET", f"/api/search/entities", params={"q": query})
    if res.status_code == 200:
        try:
            results = res.json()
            if not results:
                console.print("No results found.")
                return

            table = Table(title=f"Entity Search Results: '{query}'")
            table.add_column("Type", style="cyan")
            table.add_column("Value", style="magenta")
            table.add_column("Related Investigation", style="blue")
            
            for item in results:
                table.add_row(
                    item.get('type', 'N/A'),
                    item.get('value', 'N/A'),
                    item.get('investigation_id', 'N/A')
                )
            console.print(table)
        except json.JSONDecodeError:
            handle_api_error(res)
    else:
        handle_api_error(res)

@cli.group()
@click.pass_context
def entity(ctx):
    """Manage entities."""
    pass

@entity.command(name="update")
@click.argument("type")
@click.argument("value")
@click.option("--metadata", required=True, help='JSON string of metadata to update. E.g., \'{"description": "New description"}\'')
@click.pass_context
def update_entity(ctx, type, value, metadata):
    """Update an entity's metadata."""
    try:
        metadata_json = json.loads(metadata)
    except json.JSONDecodeError:
        console.print("[bold red]Error:[/bold red] Invalid JSON format for metadata.")
        return

    endpoint = f"/entities/{type}/{value}"
    res = api_request(ctx, "PATCH", endpoint, data=metadata_json)

    if res.status_code == 200:
        console.print(f"[green]Successfully updated entity {type}: {value}[/green]")
    else:
        handle_api_error(res)


@cli.command()
@click.pass_context
def graph(ctx):
    """Get all entities and insights (Global Graph)"""
    res = api_request(ctx, "GET", "/graph")
    if res.status_code == 200:
        data = res.json()
        console.print(f"Graph Data: {len(data.get('nodes', []))} nodes, {len(data.get('edges', []))} edges")
        if click.confirm("Do you want to save the graph data to graph.json?"):
            with open("graph.json", "w") as f:
                json.dump(data, f, indent=2)
            console.print("[green]Saved to graph.json[/green]")
    else:
        handle_api_error(res)

@cli.command()
@click.argument("id")
@click.pass_context
def timeline(ctx, id):
    """Get temporal event data for an investigation"""
    res = api_request(ctx, "GET", f"/investigations/{id}/timeline")
    if res.status_code == 200:
        data = res.json()
        if not data:
            console.print("No timeline events found.")
            return
            
        table = Table(title=f"Timeline for Investigation {id}")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Event", style="white")
        
        for event in data:
            table.add_row(event.get('timestamp', ''), event.get('description', ''))
        console.print(table)
    else:
        handle_api_error(res)

@cli.command()
@click.argument("id")
@click.pass_context
def report(ctx, id):
    """Generate and download PDF report"""
    console.print(f"[*] Requesting report for investigation {id}...")
    # NOTE: PDF responses are binary, handle appropriately
    api_url = ctx.obj.get('API_URL')
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    try:
        res = requests.get(f"{api_url}/api/investigations/{id}/report", headers=headers)
        if res.status_code == 200:
            filename = f"report_{id}.pdf"
            with open(filename, "wb") as f:
                f.write(res.content)
            console.print(f"[green]✔ Report saved as {filename}[/green]")
        else:
            handle_api_error(res)
    except requests.exceptions.ConnectionError:
        console.print(f"[bold red]Connection Error:[/bold red] Could not connect to {api_url}")

@cli.command()
@click.argument("id")
@click.pass_context
def audit(ctx, id):
    """Get Chain of Custody logs"""
    res = api_request(ctx, "GET", f"/investigations/{id}/audit")
    if res.status_code == 200:
        data = res.json()
        if not data:
            console.print("No audit logs found.")
            return
            
        table = Table(title=f"Chain of Custody Logs - Investigation {id}")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Action", style="magenta")
        table.add_column("Actor", style="white")
        
        for log in data:
            table.add_row(log.get('timestamp', ''), log.get('action', ''), log.get('actor', ''))
        console.print(table)
    else:
        handle_api_error(res)

@cli.command()
@click.pass_context
def verify(ctx):
    """Run system-wide integrity check"""
    console.print("[*] Running system-wide integrity check...")
    res = api_request(ctx, "POST", "/admin/verify-integrity")
    if res.status_code == 200:
        data = res.json()
        status = data.get('status')
        if status == 'passed':
            console.print("[green]✔ Integrity check passed![/green]")
        else:
            console.print(f"[bold red]✖ Integrity check failed![/bold red] Details: {data.get('details')}")
    else:
        handle_api_error(res)

@cli.group()
def alerts():
    """Manage and view real-time alerts."""
    pass

@alerts.command(name="stream")
@click.pass_context
def stream_alerts(ctx):
    """Stream real-time alerts from the platform."""
    api_url = ctx.obj.get('API_URL')
    token = get_token()
    if not token:
        console.print("[bold red]Error:[/bold red] You must be logged in to stream alerts. Please run 'auth login'.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{api_url}/api/alerts/stream"

    console.print(f"[*] Connecting to alert stream at {url}...")
    
    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status() 
        client = sseclient.SSEClient(response)

        console.print("[green]✔ Connected.[/green] Waiting for alerts...")
        for event in client.events():
            try:
                alert_data = json.loads(event.data)
                panel_content = (
                    f"[bold]Type:[/bold] {alert_data.get('type', 'N/A')}\n"
                    f"[bold]Message:[/bold] {alert_data.get('message', 'N/A')}\n"
                    f"[bold]Timestamp:[/bold] {alert_data.get('timestamp', 'N/A')}"
                )
                console.print(Panel(panel_content, title="[bold magenta]New Alert[/bold magenta]", expand=False))
            except json.JSONDecodeError:
                console.print(f"[yellow]Received non-JSON event data: {event.data}[/yellow]")

    except requests.exceptions.HTTPError as e:
        console.print(f"[bold red]HTTP Error:[/bold red] Could not connect to stream. Status code: {e.response.status_code}")
    except requests.exceptions.ConnectionError:
        console.print(f"[bold red]Connection Error:[/bold red] Could not connect to {api_url}")
    except KeyboardInterrupt:
        console.print("\n[yellow]Stream disconnected by user.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")

if __name__ == '__main__':
    cli()

# Investidubh CLI Manual

The Investidubh CLI provides a powerful, headless interface for managing investigations, creating automation scripts, and integrating Investidubh into your existing workflows.

## Installation

The CLI requires Python 3.8+ and minimal dependencies.

**Automated Setup (Recommended):**
From the project root, run the setup script. This will set up the environment variables, Docker containers, create the CLI virtual environment, and create a convenient `./investidubh` executable wrapper.
```bash
chmod +x setup.sh
./setup.sh
```

**Manual Setup:**
```bash
python3 -m venv cli/venv
source cli/venv/bin/activate
pip install -r cli/requirements.txt
```

## Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--api-url` | Base URL of the API Gateway | `http://localhost:4000` or `API_URL` env var |

**Example:**
```bash
./investidubh --api-url http://192.168.1.10:4000 list
```
*(Note: Examples below use the `./investidubh` wrapper. If you installed manually, use `python cli/investidubh_cli.py` instead.)*

## Authentication

Before running commands, you must authenticate. The CLI saves your JWT token to `~/.investidubh_token`.

### `auth register` - Create Account
```bash
./investidubh auth register
# Prompts for Username and Password, and registers a new account.
```

### `auth login` - Log In
```bash
./investidubh auth login
# Prompts for Username and Password, and saves the auth token locally.
```

## Commands

### `scan` - Start Investigation
Queues a new URL for investigation. If the URL is omitted, the CLI will prompt for it.

```bash
# Start a scan
./investidubh scan https://example.com

# Start a scan and wait for completion with a progress spinner
./investidubh scan https://example.com --wait
```

### `list` - List Investigations
Shows the most recent investigations with their status.

```bash
./investidubh list
```

### `show` - View Details
Displays detailed intelligence and artifacts for a specific investigation. If the ID is omitted, the CLI will prompt for it.

```bash
./investidubh show <investigation_id>
```

### `timeline` - Temporal Analysis
Displays the events associated with an investigation ordered by time.

```bash
./investidubh timeline <investigation_id>
```

### `graph` - Export Global Graph Data
Fetches all entities and their relationships from the system and allows saving them to `graph.json`.

```bash
./investidubh graph
```

### `search` - Global Search
Searches across all artifacts and intelligence using the Meilisearch engine.

```bash
./investidubh search "malware"
```

### `report` - Download PDF Report
Generates a PDF report for a given investigation and saves it to the current directory.

```bash
./investidubh report <investigation_id>
```

### `audit` - Chain of Custody Logs
Retrieves the unalterable audit logs showing what actions were performed, by whom, and when, for a specific investigation.

```bash
./investidubh audit <investigation_id>
```

### `verify` - System Integrity Check
Runs a system-wide hash check to ensure that stored artifacts and records have not been tampered with.

```bash
./investidubh verify
```

## Scripting & Automation

Since the CLI outputs structured text and exit codes, you can easily chain it with other tools.

**Example: Scan a list of domains**
```bash
while read domain; do
  ./investidubh scan "https://$domain"
done < domains.txt
```

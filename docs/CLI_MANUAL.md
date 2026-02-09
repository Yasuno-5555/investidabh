# Investidubh CLI Manual

The Investidubh CLI provides a powerful, headless interface for managing investigations, creating automation scripts, and integrating Investidubh into your existing workflows.

# Investidubh CLI Manual

The Investidubh CLI provides a powerful, headless interface for managing investigations, creating automation scripts, and integrating Investidubh into your existing workflows.

## Installation

The CLI requires Python 3.8+ and minimal dependencies.

```bash
# From project root
pip install -r cli/requirements.txt
```

## Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--api-url` | Base URL of the API Gateway | `http://localhost:4000` or `API_URL` env var |

**Example:**
```bash
python3 cli/investidubh_cli.py --api-url http://192.168.1.10:4000 list
```

## Authentication

Before running commands, you must authenticate. The CLI saves your JWT token to `~/.investidubh_token`.

```bash
# Interactive login
python3 cli/investidubh_cli.py auth login

# Output
# Username: admin
# Password: 
# Successfully logged in!
```

> **Note**: You can also use non-interactive login by passing `--username` and `--password` flags, but be careful with history.

## Commands

### `scan` - Start Investigation
Queues a new URL for investigation.

```bash
python3 cli/investidubh_cli.py scan https://example.com

# Output
# [*] Starting investigation for https://example.com...
# Investigation queued! ID: c5cae1be-1d0c-47dd-b20a-6779ee867ace
```

### `list` - List Investigations
Shows the most recent investigations with their status.

```bash
python3 cli/investidubh_cli.py list
```

| ID | Target URL | Status | Created At |
|----|------------|--------|------------|
| ...| ...        | ...    | ...        |

### `show` - View Details
Displays detailed intelligence and artifacts for a specific investigation.

```bash
python3 cli/investidubh_cli.py show <investigation_id>
```

**Output includes:**
- Status and Target
- Extracted Intelligence (Type, Value, Source)
- Artifact Paths (Screenshots, HTML)

### `search` - Global Search
Searches across all artifacts and intelligence using the Meilisearch engine.

```bash
python3 cli/investidubh_cli.py search "malware"
```

## scripting & Automation

Since the CLI outputs structured text and exit codes, you can easily chain it with other tools.

**Example: Scan a list of domains**
```bash
while read domain; do
  python3 cli/investidubh_cli.py scan "https://$domain"
done < domains.txt
```

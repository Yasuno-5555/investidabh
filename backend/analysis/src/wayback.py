import requests
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

CDX_API_URL = "http://web.archive.org/cdx/search/cdx"
WAYBACK_BASE_URL = "http://web.archive.org/web"

def fetch_snapshots(target_url, limit_per_year=1, max_years=5):
    """
    Fetch snapshots from CDX API.
    Strategy: Sample 1 snapshot per year to minimize load and redundancy.
    """
    snapshots = []
    
    # Filter for 200 OK and HTML only to avoid junk
    params = {
        'url': target_url,
        'output': 'json',
        'fl': 'timestamp,original,mimetype,statuscode,digest',
        'filter': ['statuscode:200', 'mimetype:text/html'],
        'collapse': 'digest' # Skip duplicate content
    }

    try:
        response = requests.get(CDX_API_URL, params=params, timeout=10)
        data = response.json()
        
        # data[0] is header: ['timestamp', 'original', 'mimetype', 'statuscode', 'digest']
        if not data or len(data) <= 1:
            return []

        rows = data[1:]
        # Sort by timestamp desc
        rows.sort(key=lambda x: x[0], reverse=True)

        seen_years = set()
        
        for row in rows:
            ts = row[0] # YYYYMMDDHHMMSS
            year = ts[:4]
            
            if year not in seen_years:
                snapshots.append({
                    'timestamp': ts,
                    'original': row[1],
                    'url': f"{WAYBACK_BASE_URL}/{ts}id_/{row[1]}"
                })
                seen_years.add(year)
            
            if len(seen_years) >= max_years:
                break
                
        logger.info(f"Wayback: Found {len(snapshots)} snapshots for {target_url}")
        return snapshots

    except Exception as e:
        logger.error(f"Wayback CDX Error: {e}")
        return []

def get_historical_content(snapshot_url):
    """
    Fetch the raw HTML content of a snapshot.
    Includes rate limiting sleep.
    """
    try:
        time.sleep(1.5) # Polite delay
        resp = requests.get(snapshot_url, timeout=15)
        if resp.status_code == 200:
            return resp.text
        return None
    except Exception as e:
        logger.error(f"Wayback Content Fetch Error: {e}")
        return None

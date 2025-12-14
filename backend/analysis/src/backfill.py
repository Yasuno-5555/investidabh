import os
import psycopg
import meilisearch
from minio import Minio
from bs4 import BeautifulSoup
import asyncio

# Config
# Note: Using synchronous psycopg for this script or async? The snippet used 'psycopg.connect' which is sync.
# The project uses 'psycopg[binary]' which supports both.
DB_DSN = os.getenv("DATABASE_URL", "postgresql://investidubh:secret@postgres:5432/investidubh_core")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "password")
MEILI_HOST = os.getenv("MEILI_HOST", "http://meilisearch:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")

# Clients
# MinIO client needs host:port. The env var often includes it or handles it.
# Docker service name 'minio' resolves to IP.
# If MINIO_ENDPOINT is 'minio:9000', we pass that.
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

try:
    meili_client = meilisearch.Client(MEILI_HOST, MEILI_KEY)
except Exception as e:
    print(f"[!] Meilisearch Connection Error: {e}")
    exit(1)

def strip_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for script in soup(["script", "style", "meta", "noscript"]):
        script.decompose()
    return soup.get_text(separator=' ', strip=True)[:100000]

def run_backfill():
    print("[*] Starting Backfill Process...")
    
    # Ensure index exists
    try:
        index = meili_client.index('contents')
        index.update_settings({
            'searchableAttributes': ['text', 'title', 'url'],
            'filterableAttributes': ['investigation_id'],
            'displayedAttributes': ['investigation_id', 'title', 'url', 'snippet']
        })
    except Exception as e:
        print(f"[!] Failed to update settings (might be offline): {e}")

    # 1. Connect to DB
    try:
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                # HTMLアーティファクトを持つ完了済みの調査を取得
                cur.execute("""
                    SELECT i.id, i.target_url, a.storage_path 
                    FROM investigations i
                    JOIN artifacts a ON i.id = a.investigation_id
                    WHERE a.artifact_type = 'html' AND i.status = 'COMPLETED'
                """)
                rows = cur.fetchall()
                
                print(f"[*] Found {len(rows)} investigations to process.")
                
                for row in rows:
                    inv_id, url, path = row
                    print(f" -> Processing {url} ({inv_id})")
                    
                    try:
                        # 2. Fetch HTML from MinIO
                        # MinIO bucket name 'raw-data' is hardcoded in other places, assuming same here.
                        response = minio_client.get_object("raw-data", path)
                        html_content = response.read().decode('utf-8')
                        response.close()
                        response.release_conn()
                        
                        # 3. Strip & Index
                        text_content = strip_html(html_content)
                        doc = {
                            'id': str(inv_id),
                            'investigation_id': str(inv_id),
                            'url': url,
                            'title': url,
                            'text': text_content
                        }
                        meili_client.index('contents').add_documents([doc])
                        print("    [OK] Indexed.")
                        
                    except Exception as e:
                        print(f"    [ERR] Failed: {e}")

        print("[*] Backfill Completed.")
    except Exception as e:
        print(f"[!] DB Connection Error: {e}")

if __name__ == "__main__":
    run_backfill()

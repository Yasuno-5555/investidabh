import asyncio
import json
import os
import redis.asyncio as redis
import logging
import sys
from extractor import extract_and_save
from indexer import index_content
from nlp_analyzer import analyze_and_save
from scorer import run_scoring
from enrichers import WhoisEnricher, DNSEnricher
from alerts import AlertManager
from ttp_map import TTPMapper
from migrate_db import migrate

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Phase 31 Components
whois_enricher = WhoisEnricher()
dns_enricher = DNSEnricher()
alert_manager = AlertManager()
ttp_mapper = TTPMapper()
# Load basic watchlist for demo - ideally this comes from DB/Config
alert_manager.load_watchlist(['bad.com', 'evil-corp.org', 'test@example.com']) 

from bs4 import BeautifulSoup
from minio import Minio
import psycopg

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DB_DSN = os.getenv("DATABASE_URL", "postgres://investidubh:secret@localhost:5432/investidubh_core")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "password")
BUCKET_NAME = "raw-data"

# Initialize MinIO
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

async def process_enrichment_and_alerts(investigation_id, r_conn):
    """
    Phase 31: Run Enrichment, TTP Mapping, and Alerts.
    Updates intelligence items with new metadata.
    """
    logger.info(f"[*] Starting Enrichment & Alerts for {investigation_id}")
    try:
        # Pass redis connection to alert manager if not already set
        if not alert_manager.redis:
            alert_manager.redis = r_conn

        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as cur:
                # 1. Fetch all entities for this investigation
                await cur.execute(
                    "SELECT id, type, value, metadata FROM intelligence WHERE investigation_id = %s",
                    (investigation_id,)
                )
                rows = await cur.fetchall()
                
                for row in rows:
                    ent_id, ent_type, ent_value, ent_metadata = row
                    if not ent_metadata: ent_metadata = {}
                    
                    changed = False
                    
                    # 2. Run Enrichment
                    enrichments = {}
                    if whois_enricher.can_handle(ent_type):
                        res = whois_enricher.enrich(ent_type, ent_value)
                        if res: enrichments.update(res)
                    
                    if dns_enricher.can_handle(ent_type):
                        res = dns_enricher.enrich(ent_type, ent_value)
                        if res: enrichments.update(res)
                        
                    if enrichments:
                        ent_metadata.update(enrichments)
                        changed = True
                        logger.info(f"[+] Enriched {ent_value} ({ent_type})")

                    # 3. TTP Mapping
                    tags = ttp_mapper.map_text(str(ent_value))
                    # Also map from metadata if useful text exists (e.g. title)
                    if 'whois' in ent_metadata and 'org' in ent_metadata['whois']:
                         tags.extend(ttp_mapper.map_text(str(ent_metadata['whois']['org'])))
                    
                    current_tags = ent_metadata.get('ttps', [])
                    new_tags = list(set(current_tags + tags))
                    if len(new_tags) > len(current_tags):
                        ent_metadata['ttps'] = new_tags
                        changed = True
                        logger.info(f"[+] TTPs found for {ent_value}: {tags}")

                    # 4. Update DB if changed
                    if changed:
                         await cur.execute(
                             "UPDATE intelligence SET metadata = %s WHERE id = %s",
                             (json.dumps(ent_metadata), ent_id)
                         )

                    # 5. Alerts
                    # Check watchlist and TTPs
                    alert_manager.check_and_alert(
                        entity_type=ent_type,
                        entity_value=ent_value,
                        investigation_id=investigation_id,
                        metadata=ent_metadata
                    )
                    if new_tags:
                        alert_manager.check_and_alert(
                            entity_type=ent_type,
                            entity_value=ent_value,
                            investigation_id=investigation_id,
                            metadata={'ttps': new_tags, 'msg': 'TTP Detected'}
                        )

            await aconn.commit()
            
    except Exception as e:
        logger.error(f"[!] Enrichment/Alerting failed: {e}")

async def worker():
    # Run DB Migration on Startup
    # await migrate()

    logger.info(f"[*] Analysis Worker started. Connecting to {REDIS_URL}...")
    try:
        r = redis.from_url(REDIS_URL)
        pubsub = r.pubsub()
        await pubsub.subscribe("events:investigation_completed")
        logger.info("[-] Subscribed to events:investigation_completed")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return

    async for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                logger.info(f"[+] Received event for investigation: {data.get('id')}")
                
                investigation_id = data.get('id')
                target_url = data.get('targetUrl')

                # 1. Run Entity Extraction (Emails, Phones - existing)
                await extract_and_save(investigation_id, target_url=target_url)

                # 2. Fetch HTML content for Advanced Analysis
                html_path = None
                try:
                    async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
                        async with aconn.cursor() as cur:
                             await cur.execute("SELECT storage_path FROM artifacts WHERE investigation_id = %s AND artifact_type = 'html'", (investigation_id,))
                             row = await cur.fetchone()
                             if row:
                                 html_path = row[0]
                except Exception as e:
                    logger.error(f"DB Error fetching HTML path: {e}")

                # 3. Analyze Text (NLP - Named Entity Recognition & Sentiment)
                if html_path:
                    try:
                        # Fetch content from MinIO
                        resp = minio_client.get_object(BUCKET_NAME, html_path)
                        html_content = resp.read().decode('utf-8')
                        resp.close()
                        resp.release_conn()
                        
                        # Extract text from HTML
                        soup = BeautifulSoup(html_content, 'html.parser')
                        text = soup.get_text()
                        
                        # Analyze
                        await analyze_and_save(investigation_id, text)
                        
                    except Exception as e:
                        logger.error(f"NLP Analysis failed: {e}")

                    # 3.5 Indexing (Meilisearch) - Optimized
                    try:
                         # Now index_content is async and non-blocking
                         await index_content(investigation_id, target_url, html_content)
                    except Exception as e:
                         # Indexing failure shouldn't fail the pipeline
                         logger.warning(f"Indexing failed: {e}")
                
                # 3.6 Enrichment & Alerts (Phase 31)
                await process_enrichment_and_alerts(investigation_id, r)

                # 4. Scoring
                await run_scoring(investigation_id)
                
                logger.info(f"[-] Analysis completed for {investigation_id}")

            except Exception as e:
                logger.error(f"Error processing message: {e}")

if __name__ == "__main__":
    asyncio.run(worker())

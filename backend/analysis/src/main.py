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
from migrate_db import migrate
from bs4 import BeautifulSoup
from extractor import minio_client, BUCKET_NAME, DB_DSN
import psycopg


# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("analysis")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def worker():
    # Run DB Migration on Startup
    await migrate()

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
                task_data = json.loads(task[1])
                asyncio.run(process_task(task_data))
            except Exception as e:
                logger.error(f"Error processing task: {e}")

if __name__ == "__main__":
    worker()

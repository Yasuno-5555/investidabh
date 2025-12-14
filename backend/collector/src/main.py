import asyncio
import json
import os
import redis.asyncio as redis
import logging
import sys
from collector import collect_url

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("collector")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def worker():
    logger.info(f"[*] Collector Worker started. Connecting to {REDIS_URL}...")
    try:
        r = redis.from_url(REDIS_URL)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return

    while True:
        try:
            item = await r.blpop("tasks:collector", timeout=0)
            
            if item:
                _, task_json = item
                try:
                    task = json.loads(task_json)
                    
                    logger.info(f"[+] Received task: {task.get('id', 'unknown')}")
                    logger.info(f"    Target: {task.get('targetUrl', 'unknown')}")
                    
                    # 実収集処理の実行
                    success = await collect_url(task['id'], task['targetUrl'])
                    
                    if success:
                        logger.info(f"[-] Task {task.get('id', 'unknown')} completed.")
                        # Parse trigger
                        await r.publish('events:investigation_completed', json.dumps({
                            'id': task['id'],
                            'targetUrl': task['targetUrl']
                        }))
                    else:
                        logger.error(f"[!] Task {task.get('id', 'unknown')} failed.")
                        
                except json.JSONDecodeError:
                    logger.error(f"[!] Received invalid JSON: {task_json}")

        except Exception as e:
            logger.error(f"[!] Worker Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped.")

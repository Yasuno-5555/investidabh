import asyncio
import json
import os
import redis.asyncio as redis
import logging
import sys
from collector import collect_url

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("collector-worker")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MAX_RETRIES_PER_TASK = int(os.getenv("MAX_RETRIES_PER_TASK", "3"))

async def connect_redis():
    while True:
        try:
            r = redis.from_url(REDIS_URL, socket_keepalive=True)
            await r.ping()  # Connection check
            logger.info("Successfully connected to Redis")
            return r
        except Exception as e:
            logger.error(f"Redis connection failed: {e}. Retrying in 10s...")
            await asyncio.sleep(10)

# Initialize Collectors
rss_collector = RSSCollector()
sns_collector = SNSCollector()
git_collector = GitCollector()
infra_collector = InfraCollector()

async def worker():
    logger.info("[*] Collector Worker starting...")
    
    while True:
        r = None
        try:
            r = await connect_redis()
            
            while True:
                try:
                    item = await r.blpop("tasks:collector", timeout=30)
                    if not item:
                        continue
                        
                    _, task_json = item
                    task = json.loads(task_json)
                    
                    task_id = task.get('id')
                    url = task.get('targetUrl')
                    if not task_id or not url:
                        logger.error(f"Invalid task format: {task_json}")
                        continue
                        
                    logger.info(f"Processing task {task_id} -> {url}")
                    
                    success = False
                    
                    # Dispatch based on URL Scheme
                    if url.startswith("rss://") or url.endswith(".rss") or url.endswith(".xml") or "feed" in url:
                        # Simple heuristic for RSS if scheme not present, but better to use scheme
                        target = url.replace("rss://", "https://") if url.startswith("rss://") else url
                        data = await rss_collector.collect(target)
                        success = await save_data_artifact(task_id, data, "rss")
                        
                    elif url.startswith("mastodon://"):
                        query = url.replace("mastodon://", "")
                        data = await sns_collector.collect(query, platform="mastodon")
                        success = await save_data_artifact(task_id, data, "sns")
                        
                    elif url.startswith("twitter://"):
                         query = url.replace("twitter://", "")
                         data = await sns_collector.collect(query, platform="twitter")
                         success = await save_data_artifact(task_id, data, "sns")

                    elif url.startswith("github://"):
                        query = url.replace("github://", "")
                        data = await git_collector.collect(query)
                        success = await save_data_artifact(task_id, data, "git")
                        
                    elif url.startswith("infra://") or url.startswith("crtsh://"):
                         query = url.replace("infra://", "").replace("crtsh://", "")
                         data = await infra_collector.collect(query)
                         success = await save_data_artifact(task_id, data, "infra")

                    else:
                        # Default Web Collector
                        success = await collect_url(task_id, url)
                    
                    if success:
                        logger.info(f"Task {task_id} completed successfully")
                        await r.publish('events:investigation_completed', json.dumps({
                            'id': task_id,
                            'targetUrl': url,
                            'status': 'completed',
                            'timestamp': asyncio.get_event_loop().time()
                        }))
                    else:
                        logger.warning(f"Task {task_id} failed")
                        # Publish failure event so other systems know
                        await r.publish('events:investigation_failed', json.dumps({
                            'id': task_id,
                            'targetUrl': url,
                            'status': 'failed',
                            'timestamp': asyncio.get_event_loop().time()
                        }))
                        
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {task_json}")
                except redis.ConnectionError as ce:
                    logger.error(f"Redis connection lost: {ce}")
                    break  # Break inner loop to reconnect
                except Exception as e:
                    logger.error(f"Unexpected error in task processing: {e}")
                    
        except Exception as e:
            logger.error(f"Critical error: {e}")
        finally:
            if r:
                try:
                    await r.close()
                except:
                    pass
            await asyncio.sleep(5)  # Wait a bit before reconnecting

if __name__ == "__main__":
    try:
        asyncio.run(worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")

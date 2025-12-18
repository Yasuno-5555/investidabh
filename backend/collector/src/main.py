import asyncio
import json
import os
import redis.asyncio as redis
import logging
import sys
from collector import collect_url, save_data_artifact

# Import Collectors
from collectors.rss_collector import RSSCollector
from collectors.sns_collector import SNSCollector
from collectors.git_collector import GitCollector
from collectors.infra_collector import InfraCollector

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

async def worker(
    rss_collector: RSSCollector = None,
    sns_collector: SNSCollector = None,
    git_collector: GitCollector = None,
    infra_collector: InfraCollector = None
):
    logger.info("[*] Collector Worker starting...")
    
    # Initialize Collectors if not provided (DI support)
    try:
        if not rss_collector: rss_collector = RSSCollector()
        if not sns_collector: sns_collector = SNSCollector()
        if not git_collector: git_collector = GitCollector()
        if not infra_collector: infra_collector = InfraCollector()
        logger.info("Collectors initialized")
    except Exception as e:
        logger.error(f"Failed to initialize collectors: {e}")
        return

    while True:
        r = None
        try:
            r = await connect_redis()
            
            while True:
                try:
                    # Priority: New tasks ("tasks:collector") first, then retries ("tasks:retry")
                    # Note: Redis BLPOP processes keys in order.
                    # If we want a delay for retries, this simple model doesn't strictly enforce it,
                    # but processing new tasks first acts as a natural delay for retries under load.
                    # For strict backoff, we'd need a delayed queue (ZSET). 
                    # For now, following user request to use tasks:retry queue.
                    item = await r.blpop(["tasks:collector", "tasks:retry"], timeout=30)
                    if not item:
                        continue
                        
                    queue_name, task_json = item
                    # queue_name is bytes, need to decode if checking source
                    queue_name_str = queue_name.decode('utf-8') if isinstance(queue_name, bytes) else queue_name

                    task = json.loads(task_json)
                    
                    task_id = task.get('id')
                    url = task.get('targetUrl')
                    retry_count = task.get('retry_count', 0)
                    
                    if not task_id or not url:
                        logger.error(f"Invalid task format: {task_json}")
                        continue
                        
                    logger.info(f"Processing task {task_id} -> {url} (Retry: {retry_count}) from {queue_name_str}")
                    
                    success = False
                    
                    try:
                        # Dispatch based on URL Scheme
                        if url.startswith("rss://") or url.endswith(".rss") or url.endswith(".xml") or "feed" in url:
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
                            
                    except Exception as e:
                        logger.error(f"Task execution failed: {e}")
                        success = False
                    
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
                        
                        # Retry Logic
                        if retry_count < MAX_RETRIES_PER_TASK:
                            retry_count += 1
                            task['retry_count'] = retry_count
                            logger.info(f"Re-queueing task {task_id} to tasks:retry (Attempt {retry_count}/{MAX_RETRIES_PER_TASK})")
                            # Simple "mock" exponential backoff: sleep here? 
                            # Sleeping here blocks the worker. 
                            # Ideally we push to a ZSET with score=future_timestamp.
                            # But consistent with user request for LIST queue:
                            await r.rpush('tasks:retry', json.dumps(task))
                        else:
                            logger.error(f"Task {task_id} exceeded max retries. Giving up.")
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
                    logger.error(f"Unexpected error in task processing loop: {e}")
                    
        except Exception as e:
            logger.error(f"Critical error in worker: {e}")
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


import asyncio
import os
import json
import logging
import hashlib
import datetime
import io
import socket
import ipaddress
from urllib.parse import urlparse
import psycopg
from psycopg_pool import AsyncConnectionPool
from playwright.async_api import async_playwright
from minio import Minio
from tor_control import renew_tor_identity

logger = logging.getLogger("collector")

# Environment Variables
DB_DSN = os.environ["DATABASE_URL"]
MINIO_ENDPOINT = os.environ["MINIO_ENDPOINT"]
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER") or os.getenv("MINIO_ACCESS_KEY") or "admin"
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD") or os.getenv("MINIO_SECRET_KEY") or "password"
BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "investigations")
TOR_ROTATION_ENABLED = os.getenv("TOR_ROTATION_ENABLED", "true").lower() == "true"

# MinIO Client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Global DB Pool
db_pool: AsyncConnectionPool = None

async def init_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = AsyncConnectionPool(DB_DSN, open=False)
        await db_pool.open()
        logger.info("DB Pool initialized")

async def close_db_pool():
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None
        logger.info("DB Pool closed")

# Ensure bucket exists
if not minio_client.bucket_exists(BUCKET_NAME):
    try:
        minio_client.make_bucket(BUCKET_NAME)
    except Exception as e:
        logger.error(f"Failed to create bucket: {e}")

def validate_url(url: str):
    """
    Prevents SSRF by blocking internal/private IP ranges and dangerous hostnames.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ['http', 'https']:
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: No hostname found")

    # 1. Block known dangerous internal hostnames
    blacklist = ['localhost', 'tor', 'minio', 'postgres', 'redis', 'meilisearch', 'analysis', 'gateway']
    if hostname.lower() in blacklist:
        raise ValueError(f"Access to internal hostname blocked: {hostname}")

    # 2. Resolve IP and check if it is private
    try:
        ip_addr = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_addr)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            raise ValueError(f"Access to private IP blocked: {ip_addr}")
        
        # Cloud Metadata IP (AWS, GCP, etc.)
        if str(ip) == "169.254.169.254":
             raise ValueError("Access to cloud metadata IP blocked")
             
    except socket.gaierror:
        # If we can't resolve, it might be an onion or just invalid. 
        # For onion sites, we let it pass as it will be handled by Tor proxy.
        if not hostname.endswith('.onion'):
            logger.warning(f"Could not resolve hostname {hostname}, proceeding with caution")
    except Exception as e:
        raise ValueError(f"URL validation error: {e}")

async def collect_url(task_id: str, url: str, browser=None) -> bool:
    logger.info(f"Starting collection for task {task_id}: {url}")
    
    if db_pool is None:
        logger.error("DB Pool not initialized!")
        return False
        
    # SSRF Validation
    try:
        validate_url(url)
    except ValueError as e:
        logger.error(f"URL validation failed for {url}: {e}")
        return False

    # Tor Rotation & Proxy Enforcement
    proxy_settings = None
    if TOR_ROTATION_ENABLED:
        logger.info("Renewing Tor identity...")
        tor_control_host = os.getenv("TOR_CONTROL_HOST", "tor")
        tor_control_port = int(os.getenv("TOR_CONTROL_PORT", "9051"))
        await renew_tor_identity(control_host=tor_control_host, control_port=tor_control_port)
        
        tor_proxy = os.getenv("TOR_PROXY_URL") or "socks5://tor:9050"
        # FAIL-CLOSED
        if not tor_proxy:
             logger.error("TOR_ROTATION_ENABLED but TOR_PROXY_URL is missing. ABORTING.")
             return False
        proxy_settings = {"server": tor_proxy}
    
    # helper to run the collection logic given a browser instance
    async def run_collection(browser_instance):
        context = await browser_instance.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            proxy=proxy_settings # Apply proxy at context level if supported, or browser level. 
                                 # Playwright only supports proxy at launch().
                                 # If reusing browser, we CANNOT change proxy per context easily without a separate browser instance 
                                 # OR using a proxy that handles rotation (like Privoxy/Tor).
                                 # For this specific case, if TOR_ROTATION is enabled, we need to ensure the browser uses it.
                                 # If we launched the browser with the proxy, we are good.
        )
        try:
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                logger.warning(f"Navigate timeout or error for {url}: {e}")
            
            content = await page.content()
            try:
                screenshot = await page.screenshot(full_page=True)
            except Exception as e:
                logger.warning(f"Screenshot failed: {e}")
                screenshot = b""

            timestamp = datetime.datetime.now().isoformat()
            base_path = f"{task_id}/{timestamp}"

            html_bytes = content.encode('utf-8')
            screenshot_bytes = screenshot
            
            html_hash = hashlib.sha256(html_bytes).hexdigest()
            screenshot_hash = hashlib.sha256(screenshot_bytes).hexdigest()

            # MinIO Preservation
            await asyncio.to_thread(
                minio_client.put_object,
                BUCKET_NAME, f"{base_path}/index.html",
                io.BytesIO(html_bytes), len(html_bytes),
                content_type="text/html"
            )
            
            if screenshot_bytes:
                    await asyncio.to_thread(
                    minio_client.put_object,
                    BUCKET_NAME, f"{base_path}/screenshot.png",
                    io.BytesIO(screenshot_bytes), len(screenshot_bytes),
                    content_type="image/png"
                )

            # Batch DB Update
            html_path = f"{base_path}/index.html"
            screenshot_path = f"{base_path}/screenshot.png"

            async with db_pool.connection() as aconn:
                async with aconn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO artifacts (investigation_id, artifact_type, storage_path, hash_sha256) VALUES (%s, %s, %s, %s)",
                        (task_id, 'html', html_path, html_hash)
                    )
                    if screenshot_bytes:
                        await cur.execute(
                            "INSERT INTO artifacts (investigation_id, artifact_type, storage_path, hash_sha256) VALUES (%s, %s, %s, %s)",
                            (task_id, 'screenshot', screenshot_path, screenshot_hash)
                        )
            
            logger.info(f"Successfully saved artifacts for {task_id}")
            return True

        finally:
            await context.close()

    # Use provided browser or launch a temporary one (fallback)
    if browser:
        return await run_collection(browser)
    else:
        async with async_playwright() as p:
             # NOTE: If we are here, we are launching a one-off browser.
             # This respects the proxy settings calculated above.
             browser = await p.chromium.launch(headless=True, proxy=proxy_settings)
             try:
                 return await run_collection(browser)
             finally:
                 await browser.close()

async def save_data_artifact(task_id: str, data: dict, source_type: str) -> bool:
    """
    Saves structured data (JSON) to MinIO and DB.
    """
    try:
        if db_pool is None:
             logger.error("DB Pool not initialized!")
             return False

        timestamp = datetime.datetime.now().isoformat()
        base_path = f"{task_id}/{timestamp}"
        file_name = f"{source_type}_data.json"
        object_path = f"{base_path}/{file_name}"
        
        json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        
        # Calculate Hash
        json_hash = hashlib.sha256(json_bytes).hexdigest()
        
        # MinIO
        await asyncio.to_thread(
            minio_client.put_object,
            BUCKET_NAME, object_path,
            io.BytesIO(json_bytes), len(json_bytes),
            content_type="application/json"
        )
        
        # DB
        async with db_pool.connection() as aconn:
            async with aconn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO artifacts (investigation_id, artifact_type, storage_path, hash_sha256) VALUES (%s, %s, %s, %s)",
                    (task_id, 'raw_data', object_path, json_hash)
                )
                
        logger.info(f"Saved structured data for {task_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save data artifact: {e}")
        return False


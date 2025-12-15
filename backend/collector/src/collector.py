import os
import io
import datetime
import psycopg
import asyncio
import json
from playwright.async_api import async_playwright
from minio import Minio
from tor_control import renew_tor_identity


# MinIO設定
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "password")
BUCKET_NAME = "raw-data"

# DB設定
DB_DSN = os.getenv("DATABASE_URL", "postgresql://investidubh:secret@postgres:5432/investidubh_core")


# MinIOクライアント初期化
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

if not minio_client.bucket_exists(BUCKET_NAME):
    minio_client.make_bucket(BUCKET_NAME)

async def collect_url(task_id: str, url: str):
    print(f"[*] Starting collection for {url}")
    
    proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"
    proxy_server = f"socks5://{os.getenv('PROXY_HOST', 'tor')}:{os.getenv('PROXY_PORT', '9050')}"
    tor_control_host = os.getenv("TOR_CONTROL_HOST", "tor")
    tor_control_port = int(os.getenv("TOR_CONTROL_PORT", "9051"))
    
    max_retries = 3
    
    for attempt in range(max_retries):
        browser = None
        try:
            async with async_playwright() as p:
                launch_args = {"headless": True}
                if proxy_enabled:
                    launch_args["proxy"] = {"server": proxy_server}
                    print(f"[*] [Attempt {attempt+1}/{max_retries}] Using Proxy: {proxy_server}")
                else:
                    print(f"[*] [Attempt {attempt+1}/{max_retries}] Direct connection (No Proxy)")

                browser = await p.chromium.launch(**launch_args)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                page = await context.new_page()

                # Timeout extended to 120s for Tor
                await page.goto(url, timeout=120000, wait_until="networkidle")

                content = await page.content()
                screenshot = await page.screenshot(full_page=True)

                timestamp = datetime.datetime.now().isoformat()
                base_path = f"{task_id}/{timestamp}"

                html_bytes = content.encode('utf-8')
                screenshot_bytes = screenshot

                # MinIO Preservation
                minio_client.put_object(
                    BUCKET_NAME, f"{base_path}/index.html",
                    io.BytesIO(html_bytes), len(html_bytes),
                    content_type="text/html"
                )
                minio_client.put_object(
                    BUCKET_NAME, f"{base_path}/screenshot.png",
                    io.BytesIO(screenshot_bytes), len(screenshot_bytes),
                    content_type="image/png"
                )

                # Batch DB Update after successful MinIO saves
                html_path = f"{base_path}/index.html"
                screenshot_path = f"{base_path}/screenshot.png"

                async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
                    async with aconn.cursor() as cur:
                        await cur.execute(
                            "INSERT INTO artifacts (investigation_id, artifact_type, storage_path) VALUES (%s, %s, %s)",
                            (task_id, 'html', html_path)
                        )
                        await cur.execute(
                            "INSERT INTO artifacts (investigation_id, artifact_type, storage_path) VALUES (%s, %s, %s)",
                            (task_id, 'screenshot', screenshot_path)
                        )
                        await cur.execute(
                            "UPDATE investigations SET status = 'COMPLETED' WHERE id = %s",
                            (task_id,)
                        )
                        await aconn.commit()

                print(f"[+] Successfully saved artifacts for {task_id}")
                return True

        except Exception as e:
            print(f"[!] Error on attempt {attempt+1}: {e}")
            if attempt < max_retries - 1 and proxy_enabled:
                print("[!] Rotating Tor identity...")
                try:
                    await renew_tor_identity(tor_control_host, tor_control_port)
                except Exception as renew_e:
                    print(f"[!] Tor renew failed: {renew_e}")
        finally:
            if browser:
                await browser.close()
    return False

async def save_data_artifact(task_id: str, data: dict, source_type: str):
    """
    Saves structured data (JSON) to MinIO and DB.
    """
    timestamp = datetime.datetime.now().isoformat()
    base_path = f"{task_id}/{timestamp}"
    file_name = f"{source_type}_data.json"
    object_path = f"{base_path}/{file_name}"
    
    json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    # MinIO
    minio_client.put_object(
        BUCKET_NAME, object_path,
        io.BytesIO(json_bytes), len(json_bytes),
        content_type="application/json"
    )
    
    # DB
    async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
        async with aconn.cursor() as cur:
            await cur.execute(
                "INSERT INTO artifacts (investigation_id, artifact_type, storage_path) VALUES (%s, %s, %s)",
                (task_id, 'raw_data', object_path)
            )
            # Mark investigation as completed
            await cur.execute(
                "UPDATE investigations SET status = 'COMPLETED' WHERE id = %s",
                (task_id,)
            )
            await aconn.commit()
            
    print(f"[+] Saved structured data for {task_id}")
    return True


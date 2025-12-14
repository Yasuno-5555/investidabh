import os
import io
import datetime
import psycopg
import asyncio
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

async def save_artifact_meta(investigation_id, artifact_type, storage_path):
    """Postgresに成果物情報を保存"""
    try:
        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO artifacts (investigation_id, artifact_type, storage_path)
                    VALUES (%s, %s, %s)
                    """,
                    (investigation_id, artifact_type, storage_path)
                )
                # ステータスをCOMPLETEDに更新
                await cur.execute(
                    "UPDATE investigations SET status = 'COMPLETED' WHERE id = %s",
                    (investigation_id,)
                )
                await aconn.commit()
    except Exception as e:
        print(f"[!] DB Error: {e}")

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
                launch_args = {
                    "headless": True
                }
                
                if proxy_enabled:
                    launch_args["proxy"] = {"server": proxy_server}
                    print(f"[*] [Attempt {attempt+1}/{max_retries}] Using Proxy: {proxy_server}")
                else:
                    print(f"[*] [Attempt {attempt+1}/{max_retries}] Direct connection (No Proxy)")

                browser = await p.chromium.launch(**launch_args)
                
                # Use a standard user agent to avoid detection
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                page = await context.new_page()

                try:
                    # Extended timeout for Tor (90s)
                    await page.goto(url, timeout=90000, wait_until="networkidle")
                    
                    # 1. HTML保存
                    content = await page.content()
                    screenshot = await page.screenshot(full_page=True)
                    
                    # --- MinIOへの保存 ---
                    timestamp = datetime.datetime.now().isoformat()
                    base_path = f"{task_id}/{timestamp}"

                    html_bytes = content.encode('utf-8')
                    minio_client.put_object(
                        BUCKET_NAME,
                        f"{base_path}/index.html",
                        io.BytesIO(html_bytes),
                        len(html_bytes),
                        content_type="text/html"
                    )

                    # 2. スクリーンショット保存
                    minio_client.put_object(
                        BUCKET_NAME,
                        f"{base_path}/screenshot.png",
                        io.BytesIO(screenshot),
                        len(screenshot),
                        content_type="image/png"
                    )
                    
                    # --- Postgres保存 ---
                    html_path = f"{base_path}/index.html"
                    screenshot_path = f"{base_path}/screenshot.png"

                    await save_artifact_meta(task_id, 'html', html_path)
                    await save_artifact_meta(task_id, 'screenshot', screenshot_path)
                    
                    print(f"[+] Successfully saved artifacts for {task_id}")
                    return True # Success, exit loop
                
                finally:
                   await browser.close()

        except Exception as e:
            print(f"[!] Error processing {url} (Attempt {attempt+1}): {e}")
            if attempt < max_retries - 1 and proxy_enabled:
                print("[!] Initiating IP rotation before retry...")
                await renew_tor_identity(tor_control_host, tor_control_port)
            elif attempt == max_retries - 1:
                return False
                
    return False

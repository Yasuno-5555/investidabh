import hashlib

# ... (Previous imports)

# ... (MinIO Client init)

async def collect_url(task_id: str, url: str):
    # ... (Start log)
    
    # ... (Proxy setup)
    
    # ... (Retry Loop)
        # ... (Browser launch)
                # ... (Goto URL)

                # ... (Get content)
                content = await page.content()
                screenshot = await page.screenshot(full_page=True)

                timestamp = datetime.datetime.now().isoformat()
                base_path = f"{task_id}/{timestamp}"

                html_bytes = content.encode('utf-8')
                screenshot_bytes = screenshot
                
                # Phase 35: Calculate Hashes
                html_hash = hashlib.sha256(html_bytes).hexdigest()
                screenshot_hash = hashlib.sha256(screenshot_bytes).hexdigest()

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
                        # Phase 35: Save Hashes
                        await cur.execute(
                            "INSERT INTO artifacts (investigation_id, artifact_type, storage_path, hash_sha256) VALUES (%s, %s, %s, %s)",
                            (task_id, 'html', html_path, html_hash)
                        )
                        await cur.execute(
                            "INSERT INTO artifacts (investigation_id, artifact_type, storage_path, hash_sha256) VALUES (%s, %s, %s, %s)",
                            (task_id, 'screenshot', screenshot_path, screenshot_hash)
                        )
                        await cur.execute(
                            "UPDATE investigations SET status = 'COMPLETED' WHERE id = %s",
                            (task_id,)
                        )
                        await aconn.commit()

                print(f"[+] Successfully saved artifacts for {task_id}")
                return True

        # ... (Exception handling)

async def save_data_artifact(task_id: str, data: dict, source_type: str):
    """
    Saves structured data (JSON) to MinIO and DB.
    """
    timestamp = datetime.datetime.now().isoformat()
    base_path = f"{task_id}/{timestamp}"
    file_name = f"{source_type}_data.json"
    object_path = f"{base_path}/{file_name}"
    
    json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    # Phase 35: Calculate Hash
    json_hash = hashlib.sha256(json_bytes).hexdigest()
    
    # MinIO
    minio_client.put_object(
        BUCKET_NAME, object_path,
        io.BytesIO(json_bytes), len(json_bytes),
        content_type="application/json"
    )
    
    # DB
    async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
        async with aconn.cursor() as cur:
            # Phase 35: Save Hash
            await cur.execute(
                "INSERT INTO artifacts (investigation_id, artifact_type, storage_path, hash_sha256) VALUES (%s, %s, %s, %s)",
                (task_id, 'raw_data', object_path, json_hash)
            )
            # Mark investigation as completed
            await cur.execute(
                "UPDATE investigations SET status = 'COMPLETED' WHERE id = %s",
                (task_id,)
            )
            await aconn.commit()
            
    print(f"[+] Saved structured data for {task_id}")
    return True


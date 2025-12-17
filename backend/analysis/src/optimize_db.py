import os
import asyncio
import psycopg

DB_DSN = os.getenv("DATABASE_URL", "postgres://investidubh:secret@localhost:5432/investidubh_core")

async def optimize_db():
    print("[*] Starting Database Optimization...")
    try:
        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as cur:
                # 1. Intelligence Indexes
                await cur.execute("CREATE INDEX IF NOT EXISTS idx_intelligence_value ON intelligence(value);")
                await cur.execute("CREATE INDEX IF NOT EXISTS idx_intelligence_type ON intelligence(type);")
                await cur.execute("CREATE INDEX IF NOT EXISTS idx_intelligence_norm_value ON intelligence(normalized_value);")
                
                # 2. Artifacts Hashes
                await cur.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_hash ON artifacts(hash_sha256);")
                
                # 3. Investigation User
                await cur.execute("CREATE INDEX IF NOT EXISTS idx_investigation_user ON investigations(user_id);")

                await aconn.commit()
                print("[+] Indexes verified/created successfully.")
                
                # Note: VACUUM usually runs automatically in Postgres, but manual analyze helps new tables.
                # await cur.execute("ANALYZE;") 
                # print("[+] ANALYZE completed.")

    except Exception as e:
        print(f"[!] Optimization failed: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(optimize_db())

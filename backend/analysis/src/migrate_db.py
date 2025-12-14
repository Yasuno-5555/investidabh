import os
import psycopg
import logging
import asyncio

DB_DSN = os.getenv("DATABASE_URL", "postgres://user:password@postgres:5432/investidubh")
logger = logging.getLogger("migration")
logging.basicConfig(level=logging.INFO)

async def migrate():
    logger.info("[*] Checking DB Schema for 'score' column...")
    try:
        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as cur:
                # Check if column exists
                await cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='intelligence' AND column_name='score';
                """)
                res = await cur.fetchone()
                
                if not res:
                    logger.info("[*] 'score' column missing. Adding it...")
                    await cur.execute("ALTER TABLE intelligence ADD COLUMN score FLOAT DEFAULT 0;")
                    await aconn.commit()
                    logger.info("[+] Column 'score' added successfully.")
                else:
                    logger.info("[-] 'score' column already exists.")
                    
    except Exception as e:
        logger.error(f"[!] Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())

import os
import psycopg
import logging
import asyncio

DB_DSN = os.getenv("DATABASE_URL", "postgres://investidubh:secret@localhost:5432/investidubh_core")
logger = logging.getLogger("migration")
logging.basicConfig(level=logging.INFO)

async def check_and_create_enum(cur, enum_name, values):
    await cur.execute(f"SELECT 1 FROM pg_type WHERE typname = '{enum_name}'")
    if not await cur.fetchone():
        logger.info(f"[*] Creating ENUM type '{enum_name}'...")
        # Postgres cannot parameterize type names or values easily in CREATE TYPE
        values_str = ", ".join([f"'{v}'" for v in values])
        await cur.execute(f"CREATE TYPE {enum_name} AS ENUM ({values_str});")
        logger.info(f"[+] ENUM '{enum_name}' created.")
    else:
        logger.info(f"[-] ENUM '{enum_name}' already exists. (Skipping value check for now)")

async def add_column_if_not_exists(cur, table, column, definition):
    await cur.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='{table}' AND column_name='{column}';
    """)
    if not await cur.fetchone():
        logger.info(f"[*] Adding column '{column}' to '{table}'...")
        await cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition};")
        logger.info(f"[+] Column '{column}' added.")
    else:
        logger.info(f"[-] Column '{column}' already exists.")

async def migrate():
    logger.info("Starting Database Migration for Phase 24...")
    try:
        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as cur:
                
                # 1. Define ENUMs
                entity_types = [
                    'person', 'organization', 'location',
                    'email', 'phone', 'subdomain', 'ip',
                    'url', 'hashtag', 'mastodon_account', 'github_user',
                    'github_repo', 'rss_article', 'company_product',
                    'position_title', 'misc', 'certificate'
                ]
                await check_and_create_enum(cur, 'entity_type_enum', entity_types)
                
                source_types = [
                    'rss', 'mastodon', 'twitter', 'github', 'infra', 'wayback', 'manual'
                ]
                await check_and_create_enum(cur, 'source_type_enum', source_types)

                # 2. Add Columns
                # score (existing)
                await add_column_if_not_exists(cur, 'intelligence', 'score', 'FLOAT DEFAULT 0')
                
                # confidence_score
                await add_column_if_not_exists(cur, 'intelligence', 'confidence_score', 'FLOAT DEFAULT 1.0')
                
                # metadata
                await add_column_if_not_exists(cur, 'intelligence', 'metadata', "JSONB DEFAULT '{}'::jsonb")
                
                # source_type
                # Note: creating as text first or directly enum? enum is better.
                # But if we use 'manual' as default, we need to cast.
                await add_column_if_not_exists(cur, 'intelligence', 'source_type', "source_type_enum DEFAULT 'manual'")

                # 3. Alter entity_type to use ENUM if it's currently text
                # Check current type
                await cur.execute("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name='intelligence' AND column_name='entity_type';
                """)
                res = await cur.fetchone()
                current_type = res[0] if res else None
                
                if current_type and current_type not in ('USER-DEFINED', 'entity_type_enum'):
                    logger.info(f"[*] Converting entity_type from {current_type} to entity_type_enum...")
                    # Sanitize data first: set anything not in ENUM to 'misc'
                    # Construct a safe list for the query
                    safe_types = ", ".join([f"'{t}'" for t in entity_types])
                    await cur.execute(f"""
                        UPDATE intelligence 
                        SET entity_type = 'misc' 
                        WHERE entity_type NOT IN ({safe_types});
                    """)
                    
                    # Alter type
                    await cur.execute("""
                        ALTER TABLE intelligence 
                        ALTER COLUMN entity_type TYPE entity_type_enum 
                        USING entity_type::entity_type_enum;
                    """)
                    logger.info("[+] Converted entity_type to ENUM.")
                
                await aconn.commit()
                logger.info("[+] Migration completed successfully.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[!] Migration failed: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate())

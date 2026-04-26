import os
import sys
import psycopg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://investidubh:secret@localhost:5432/investidubh_core")

def migrate():
    logger.info(f"Connecting to database to check schema...")
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Check if intelligence table exists
                cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'intelligence');")
                if not cur.fetchone()[0]:
                    logger.error("Table 'intelligence' does not exist. Please run init.sql first.")
                    return

                # Check if metadata column exists
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'intelligence' AND column_name = 'metadata';
                """)
                if not cur.fetchone():
                    logger.info("Adding 'metadata' column to 'intelligence' table...")
                    cur.execute("ALTER TABLE intelligence ADD COLUMN metadata JSONB;")
                    logger.info("Column 'metadata' added successfully.")
                else:
                    logger.info("Column 'metadata' already exists.")

                # Check if normalized_value column exists (just in case)
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'intelligence' AND column_name = 'normalized_value';
                """)
                if not cur.fetchone():
                    logger.info("Adding 'normalized_value' column to 'intelligence' table...")
                    cur.execute("ALTER TABLE intelligence ADD COLUMN normalized_value TEXT;")
                    logger.info("Column 'normalized_value' added successfully.")
                
                conn.commit()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()

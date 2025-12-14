import os
import time
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/investidubh")

def migrate_nlp():
    print("Starting Advanced NLP DB Migration...")
    retries = 5
    while retries > 0:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    # Add sentiment_score column
                    cur.execute("""
                        ALTER TABLE intelligence 
                        ADD COLUMN IF NOT EXISTS sentiment_score FLOAT;
                    """)
                    
                    # Add metadata column for JSONB (relations, etc)
                    cur.execute("""
                        ALTER TABLE intelligence 
                        ADD COLUMN IF NOT EXISTS metadata JSONB;
                    """)
                    
                    conn.commit()
                    print("Advanced NLP DB Migration successful: Added sentiment_score and metadata columns.")
                    return
        except Exception as e:
            print(f"Migration failed (Retrying in 2s): {e}")
            retries -= 1
            time.sleep(2)
    print("Migration failed after retries.")

if __name__ == "__main__":
    migrate_nlp()

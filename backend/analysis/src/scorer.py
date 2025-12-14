import os
import psycopg
import logging
import asyncio

DB_DSN = os.getenv("DATABASE_URL", "postgres://user:password@postgres:5432/investidubh")
logger = logging.getLogger("scorer")

class EntityScorer:
    def __init__(self, dsn):
        self.dsn = dsn

    async def calculate_score(self, investigation_id):
        """
        Calculate and update scores for all entities in an investigation.
        """
        logger.info(f"[*] Calculating scores for investigation: {investigation_id}")
        
        async with await psycopg.AsyncConnection.connect(self.dsn) as aconn:
            async with aconn.cursor() as cur:
                # 1. Fetch all entities for this investigation
                await cur.execute(
                    "SELECT id, type, value, normalized_value, created_at FROM intelligence WHERE investigation_id = %s",
                    (investigation_id,)
                )
                entities = await cur.fetchall()
                
                for ent in entities:
                    ent_id, ent_type, ent_val, ent_norm, created_at = ent
                    
                    score = 0.0
                    
                    # --- A. Type Bonus ---
                    if ent_type == 'organization': score += 30
                    elif ent_type == 'person': score += 20
                    elif ent_type == 'location': score += 10
                    elif ent_type == 'email': score += 25
                    elif ent_type == 'phone': score += 15
                    elif ent_type == 'ip': score += 5
                    
                    # --- B. Frequency / Global Relevance (Cross-Investigation) ---
                    if ent_norm:
                        await cur.execute(
                            "SELECT COUNT(*) FROM intelligence WHERE normalized_value = %s AND investigation_id != %s",
                            (ent_norm, investigation_id)
                        )
                        global_count = (await cur.fetchone())[0]
                        # If it appears in other investigations, it's very important
                        score += (global_count * 10)

                    # --- C. Ghost Penalty (Simulated) ---
                    # In a real app we'd compare created_at vs investigation start time.
                    # Here we trust the result is already in created_at.
                    # If it's very old compared to NOW (assuming investigation is new)
                    # Logic: If imported from WayBack machine, created_at is old.
                    # Let's say if created_at is > 1 year ago.
                    # For simplicity, we skip complex date math here or use Python datetime.
                    # We will assume new entities are high priority.
                    
                    # --- D. Default Floor/Ceiling ---
                    score = min(max(score, 0), 100)
                    
                    # Update DB
                    await cur.execute(
                        "UPDATE intelligence SET score = %s WHERE id = %s",
                        (score, ent_id)
                    )
            
            await aconn.commit()
        logger.info(f"[+] Scoring complete for {investigation_id}")

async def run_scoring(investigation_id):
    scorer = EntityScorer(DB_DSN)
    await scorer.calculate_score(investigation_id)

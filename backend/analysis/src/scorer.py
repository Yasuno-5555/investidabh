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
        Optimized: Batch queries and updates.
        """
        logger.info(f"[*] Calculating scores for investigation: {investigation_id}")
        
        async with await psycopg.AsyncConnection.connect(self.dsn) as aconn:
            async with aconn.cursor() as cur:
                # 1. Fetch all eligible entities for this investigation
                await cur.execute(
                    "SELECT id, type, value, normalized_value FROM intelligence WHERE investigation_id = %s",
                    (investigation_id,)
                )
                entities = await cur.fetchall()
                
                if not entities:
                     return

                # Collect normalized values for batch frequency check
                # Only care about non-empty normalized values
                norm_values = [ent[3] for ent in entities if ent[3]]
                
                global_counts = {}
                if norm_values:
                    # 2. Batch Frequency Check (1 Query)
                    # We want count across ALL investigations (excluding current if needed? logic said != investigation_id)
                    # "SELECT count(*) ... WHERE normalized_value = %s AND investigation_id != %s"
                    # Optimized: Group by normalized_value
                    
                    await cur.execute(
                        """
                        SELECT normalized_value, COUNT(*) 
                        FROM intelligence 
                        WHERE normalized_value = ANY(%s) 
                          AND investigation_id != %s
                        GROUP BY normalized_value
                        """,
                        (norm_values, investigation_id)
                    )
                    rows = await cur.fetchall()
                    for r in rows:
                        global_counts[r[0]] = r[1]
                
                update_params = []
                
                for ent in entities:
                    ent_id, ent_type, ent_val, ent_norm = ent
                    
                    score = 0.0
                    
                    # --- A. Type Bonus ---
                    if ent_type == 'organization': score += 30
                    elif ent_type == 'person': score += 20
                    elif ent_type == 'location': score += 10
                    elif ent_type == 'email': score += 25
                    elif ent_type == 'phone': score += 15
                    elif ent_type == 'ip': score += 5
                    
                    # --- B. Frequency / Global Relevance ---
                    # Logic: If it appears in other investigations, it's very important
                    count = global_counts.get(ent_norm, 0)
                    score += (count * 10)

                    # --- D. Default Floor/Ceiling ---
                    score = min(max(score, 0), 100)
                    
                    update_params.append((score, ent_id))
                    
                # 3. Batch Update (1 effective operation)
                if update_params:
                    await cur.executemany(
                        "UPDATE intelligence SET score = %s WHERE id = %s",
                        update_params
                    )
            
            await aconn.commit()
        logger.info(f"[+] Scoring complete for {investigation_id}")

async def run_scoring(investigation_id):
    scorer = EntityScorer(DB_DSN)
    await scorer.calculate_score(investigation_id)

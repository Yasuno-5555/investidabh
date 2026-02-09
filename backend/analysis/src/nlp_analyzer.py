import spacy
import asyncio
import os
import psycopg
import logging
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger("analysis.nlp")

# Lazy Loading Spacy Model
_nlp_model = None

def get_nlp_model():
    global _nlp_model
    if _nlp_model is None:
        try:
            logger.info("[-] Loading NLP Model (en_core_web_sm)...")
            _nlp_model = spacy.load("en_core_web_sm")
            logger.info("[-] NLP Model loaded.")
        except OSError:
            logger.warning("[!] SpaCy model not found. Downloading...")
            from spacy.cli import download
            download("en_core_web_sm")
            _nlp_model = spacy.load("en_core_web_sm")
    return _nlp_model

DB_DSN = os.getenv("DATABASE_URL", "postgresql://investidubh:secret@localhost:5432/investidubh_core")

TARGET_ENTITIES = ["ORG", "PERSON", "GPE"]

async def analyze_and_save(investigation_id: str, text: str, db_pool: AsyncConnectionPool = None):
    """
    Extract specific entities from text and save to DB.
    Optimized: Non-blocking NLP and Batch DB Inserts.
    Uses DB Pool if provided.
    """
    if not text:
        return

    # Offload blocking NLP processing to a separate thread
    loop = asyncio.get_running_loop()
    
    def process_text_sync(txt):
        nlp = get_nlp_model()
        doc = nlp(txt)
        
        extracted_entities = []
        seen = set()
        
        for ent in doc.ents:
            if ent.label_ in TARGET_ENTITIES:
                val = ent.text.strip()
                if len(val) < 2: continue
                
                # Simple dedup in this document
                key = (ent.label_, val.lower())
                if key in seen:
                    continue
                seen.add(key)
                
                type_map = {
                    "ORG": "organization",
                    "PERSON": "person",
                    "GPE": "location"
                }
                
                extracted_entities.append({
                    "type": type_map.get(ent.label_, "unknown"),
                    "value": val,
                    "normalized": val.lower(),
                    # Store original spacy entity for relationship extraction
                    "_spacy_ent": ent 
                })
        
        # --- Phase 25: Relationship Engine 2.0 ---
        relations = []
        
        # We need to reconstruct the doc-level lookups for relationship extraction
        # Since we are inside the sync function, we can still use 'doc'
        
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                sent = ent.sent
                orgs_in_sent = [e for e in sent.ents if e.label_ == "ORG"]
                
                for org in orgs_in_sent:
                    start = min(ent.end, org.start)
                    end = max(ent.end, org.start)
                    between_text = doc[start:end].text.lower()
                    
                    indicators = ['at', 'for', 'of', 'ceo', 'founder', 'engineer', 'developer', 'manager', 'director']
                    if any(ind in between_text for ind in indicators):
                        relations.append({
                            "source": ent.text.strip(),
                            "source_type": "person",
                            "target": org.text.strip(),
                            "target_type": "organization",
                            "relation_type": "is_related_to",
                            "confidence": 0.6
                        })
        
        return extracted_entities, relations

    # Run the heavy lifting in executor
    entities, relations = await loop.run_in_executor(None, process_text_sync, text)

    # Initialize metadata for new entities
    relations_map = {}
    for rel in relations:
        if rel['source'] not in relations_map:
            relations_map[rel['source']] = []
        relations_map[rel['source']].append({
            "label": "is_related_to",
            "target": rel['target'],
            "target_type": "organization"
        })

    logger.info(f"[*] Extracted {len(entities)} entities and {len(relations)} relations.")

    import json
    
    try:
        # DB Connection Logic - Support Pool or Direct Connect
        if db_pool:
             aconn_cm = db_pool.connection()
        else:
             aconn_cm = await psycopg.AsyncConnection.connect(DB_DSN)

        async with aconn_cm as aconn:
            async with aconn.cursor() as cur:
                # Prepare batch data
                params_list = []
                for item in entities:
                    metadata = {}
                    if item['value'] in relations_map:
                        metadata['relations'] = relations_map[item['value']]
                    
                    params_list.append((
                        investigation_id, 
                        item['type'], 
                        item['value'], 
                        item['normalized'], 
                        json.dumps(metadata)
                    ))
                
                if params_list:
                    # Fix: Column names must match init.sql (type, confidence, metadata)
                    # init.sql: id, investigation_id, type, value, normalized_value, confidence, created_at
                    # Added via ALTER: user_id (on investigations), metadata (need to add)
                    
                    # We need to make sure 'metadata' column exists or we store it elsewhere?
                    # Proceeding assuming we will ADD 'metadata' to init.sql
                    
                    await cur.executemany(
                        """
                        INSERT INTO intelligence 
                        (investigation_id, type, value, normalized_value, confidence, metadata)
                        VALUES (%s, %s, %s, %s, 0.7, %s)
                        """,
                        params_list
                    )
            
            # Commit logic: 
            # If using psycopg_pool connection context manager, it might not commit automatically?
            # Correct, we must commit explicitly.
            await aconn.commit()
            
    except Exception as e:
        logger.error(f"[!] DB Error saving entities: {e}")

import spacy
import asyncio
import os
import psycopg
import logging

logger = logging.getLogger("analysis.nlp")

# Load model globally to avoid reloading
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("[-] NLP Model (en_core_web_sm) loaded.")
except OSError:
    logger.warning("[!] SpaCy model not found. Downloading...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

DB_DSN = os.getenv("DATABASE_URL", "postgresql://investidubh:secret@postgres:5432/investidubh_core")

TARGET_ENTITIES = ["ORG", "PERSON", "GPE"]

async def analyze_and_save(investigation_id: str, text: str):
    """
    Extract specific entities from text and save to DB.
    """
    if not text:
        return
        
    doc = nlp(text)
    
    entities = []
    seen = set()
    
    for ent in doc.ents:
        if ent.label_ in TARGET_ENTITIES:
            # Normalize: strip whitespace, lowercase for uniqueness check (but save original case?)
            # Actually, standardizing for linking is good.
            val = ent.text.strip()
            if len(val) < 2: continue # Ignore single letters
            
            # Simple dedup in this document
            key = (ent.label_, val.lower())
            if key in seen:
                continue
            seen.add(key)
            
            # Map spaCy label to our internal type
            # ORG -> organization
            # PERSON -> person
            # GPE -> location
            type_map = {
                "ORG": "organization",
                "PERSON": "person",
                "GPE": "location"
            }
            
            entities.append({
                "type": type_map.get(ent.label_, "unknown"),
                "value": val,
                "normalized": val.lower()
            })
            
    if not entities:
        logger.info(f"[-] No entities found in investigation {investigation_id}")
        return

    logger.info(f"[*] Saving {len(entities)} extracted entities for {investigation_id}")
    
    try:
        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as cur:
                for item in entities:
                    # Check if exists to avoid noise? 
                    # For now just insert. The graph query can aggregate by value.
                    # Or we can insert and let UUID be unique.
                    await cur.execute(
                        """
                        INSERT INTO intelligence (investigation_id, type, value, normalized_value, confidence)
                        VALUES (%s, %s, %s, %s, 0.7)
                        """,
                        (investigation_id, item['type'], item['value'], item['normalized'])
                    )
            await aconn.commit()
            
    except Exception as e:
        logger.error(f"[!] DB Error saving entities: {e}")

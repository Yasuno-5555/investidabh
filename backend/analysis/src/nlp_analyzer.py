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

DB_DSN = os.getenv("DATABASE_URL", "postgresql://investidubh:secret@localhost:5432/investidubh_core")

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
            
    
    # --- Phase 25: Relationship Engine 2.0 ---
    # Heuristic 1: Dependency Parsing for Employment (PERSON -> ORG)
    # Pattern: [PERSON] ... (works|at|for|of) ... [ORG]
    
    relations = []
    
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            # Check head or children for prepositions linking to ORG
            # Simplified approach: Look at the sentence containing the PERSON
            sent = ent.sent
            
            # Find ORGs in the same sentence
            orgs_in_sent = [e for e in sent.ents if e.label_ == "ORG"]
            
            for org in orgs_in_sent:
                # Check for connecting keywords between them in the sentence text
                # This is a naive but effective approximation for "Zero-Cost"
                # Distance valid check
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
                        "relation_type": "is_related_to", # generic for now, could be 'is_employee_of'
                        "confidence": 0.6
                    })
                    
    # Initialize metadata for new entities
    # We need to attach relations to the source entity (PERSON)
    # We'll map relations by source value for quick lookup
    relations_map = {}
    for rel in relations:
        if rel['source'] not in relations_map:
            relations_map[rel['source']] = []
        relations_map[rel['source']].append({
            "label": "is_related_to",
            "target": rel['target'],
            "target_type": "organization"
        })

    logger.info(f"[*] Extracted {len(relations)} potential relationships.")

    import json
    
    try:
        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as cur:
                for item in entities:
                    # nlp_analyzer map keys: type, value, normalized
                    # map schema: 
                    # entity_type = item['type'] (already mapped to 'organization', 'person', 'location' in code)
                    # source_type = 'manual' (from nlp)
                    
                    # We should align item['type'] with entity_type_enum
                    # nlp_analyzer maps: ORG->organization, PERSON->person, GPE->location. These are in ENUM.
                    
                    # Attach relations if any
                    metadata = {}
                    if item['value'] in relations_map:
                        metadata['relations'] = relations_map[item['value']]
                    
                    await cur.execute(
                        """
                        INSERT INTO intelligence 
                        (investigation_id, entity_type, value, normalized_value, confidence_score, metadata, source_type)
                        VALUES (%s, %s::entity_type_enum, %s, %s, 0.7, %s, 'manual'::source_type_enum)
                        """,
                        (investigation_id, item['type'], item['value'], item['normalized'], json.dumps(metadata))
                    )
            await aconn.commit()
            
    except Exception as e:
        logger.error(f"[!] DB Error saving entities: {e}")

import spacy
import asyncio
import os
import psycopg
import logging
import re
import json
from psycopg_pool import AsyncConnectionPool
from psycopg.types.json import Jsonb

logger = logging.getLogger("analysis.nlp")

# Lazy Loading Spacy Model
_nlp_model = None

def get_nlp_model():
    """
    Get or load the SpaCy NLP model with improved error handling.
    """
    global _nlp_model
    if _nlp_model is None:
        try:
            logger.info("[-] Loading NLP Model (en_core_web_sm)...")
            _nlp_model = spacy.load("en_core_web_sm")
            logger.info("[-] NLP Model loaded.")
        except OSError:
            logger.warning("[!] SpaCy model not found. Attempting to download...")
            try:
                from spacy.cli import download
                download("en_core_web_sm")
                _nlp_model = spacy.load("en_core_web_sm")
                logger.info("[-] NLP Model downloaded and loaded.")
            except Exception as e:
                logger.critical(f"[!!!] Failed to load or download SpaCy model: {e}")
                # Raising RuntimeError to ensure the system doesn't continue in an unstable state.
                raise RuntimeError(f"NLP Model Load Failure: {e}")
    return _nlp_model

DB_DSN = os.getenv("DATABASE_URL", "postgresql://investidubh:secret@localhost:5432/investidubh_core")

TARGET_ENTITIES = ["ORG", "PERSON", "GPE", "LOC", "FAC", "PRODUCT", "EVENT"]

# OSINT-specific Regex Patterns
RE_CVE = re.compile(r'CVE-\d{4}-\d{4,}', re.IGNORECASE)
RE_BTC = re.compile(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b')
RE_ETH = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
RE_IPV4 = re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
RE_EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
RE_DOMAIN = re.compile(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}\b')
RE_HASH_SHA256 = re.compile(r'\b[a-fA-F0-9]{64}\b')
RE_ASN = re.compile(r'\bAS\d{2,}\b', re.IGNORECASE)

async def analyze_and_save(investigation_id: str, text: str, db_pool: AsyncConnectionPool = None):
    """
    Extract OSINT entities and save to DB in a batch.
    """
    if not text:
        return

    try:
        # 1. NLP Extraction (blocking, offload to executor)
        loop = asyncio.get_running_loop()
        entities, relations = await loop.run_in_executor(None, _process_text_sync, text)
        
        # 2. Regex Extraction
        regex_entities = _extract_regex_entities(text)
        entities.extend(regex_entities)

        if not entities:
            logger.debug("[*] No entities discovered in text.")
            return

        # 3. Consolidate relations for metadata
        relations_map = {}
        for rel in relations:
            src = rel['source']
            if src not in relations_map:
                relations_map[src] = []
            relations_map[src].append({
                "label": rel['relation_type'],
                "target": rel['target'],
                "target_type": rel['target_type'],
                "confidence": rel['confidence'],
                "evidence": rel.get('evidence', '')
            })

        logger.info(f"[*] Analysis complete for {investigation_id}: {len(entities)} entities found.")

        # 4. DB Persistence with batching and error handling
        await _save_to_db(investigation_id, entities, relations_map, db_pool)
            
    except RuntimeError as re:
        logger.critical(f"Analysis aborted: {re}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in NLP analysis pipeline: {e}")

async def _save_to_db(investigation_id, entities, relations_map, db_pool):
    """Handles the DB saving logic with retries and pooling support."""
    params_list = []
    seen_in_batch = set()

    for item in entities:
        # Local deduplication in case of overlapping results
        batch_key = (item['type'], item['value'])
        if batch_key in seen_in_batch:
            continue
        seen_in_batch.add(batch_key)

        metadata = {}
        if item['value'] in relations_map:
            metadata['relations'] = relations_map[item['value']]
        
        params_list.append((
            investigation_id, 
            item['type'], 
            item['value'], 
            item['normalized'], 
            item.get('confidence', 0.7),
            Jsonb(metadata)
        ))

    if not params_list:
        return

    try:
        if db_pool:
            aconn_cm = db_pool.connection()
        else:
            aconn_cm = await psycopg.AsyncConnection.connect(DB_DSN)

        async with aconn_cm as aconn:
            async with aconn.cursor() as cur:
                await cur.executemany(
                    """
                    INSERT INTO intelligence 
                    (investigation_id, type, value, normalized_value, confidence, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (investigation_id, type, value) DO UPDATE 
                    SET confidence = EXCLUDED.confidence,
                        metadata = intelligence.metadata || EXCLUDED.metadata,
                        normalized_value = EXCLUDED.normalized_value
                    """,
                    params_list
                )
            await aconn.commit()
            logger.info(f"[+] Saved {len(params_list)} intelligence units to DB.")
    except psycopg.Error as e:
        logger.error(f"[!] Database error while saving intelligence: {e}")
        # In case of DB error, we might want to raise it to trigger a retry at the worker level
        raise

def _process_text_sync(txt):
    """Synchronous NLP processing."""
    nlp = get_nlp_model()
    doc = nlp(txt)
    
    entities = []
    seen = set()
    
    for ent in doc.ents:
        if ent.label_ in TARGET_ENTITIES:
            val = ent.text.strip()
            if len(val) < 2: continue
            
            key = (ent.label_, val.lower())
            if key in seen: continue
            seen.add(key)
            
            type_map = {
                "ORG": "organization",
                "PERSON": "person",
                "GPE": "location",
                "LOC": "location",
                "FAC": "facility",
                "PRODUCT": "product",
                "EVENT": "event"
            }
            
            entities.append({
                "type": type_map.get(ent.label_, "entity"),
                "value": val,
                "normalized": val.lower(),
                "confidence": 0.8
            })
    
    # Simple relationship extraction logic
    relations = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            sent = ent.sent
            for other in sent.ents:
                if other == ent: continue
                
                # Check for indicators between entities
                start = min(ent.end, other.start)
                end = max(ent.start, other.end)
                between_text = doc[start:end].text.lower()
                
                rel_type = None
                if other.label_ == "ORG" and any(ind in between_text for ind in ['at', 'for', 'of', 'ceo', 'founder', 'engineer']):
                    rel_type = "employed_by"
                elif other.label_ == "GPE" and any(ind in between_text for ind in ['from', 'in', 'at', 'lives']):
                    rel_type = "located_at"
                
                if rel_type:
                    relations.append({
                        "source": ent.text.strip(),
                        "source_type": "person",
                        "target": other.text.strip(),
                        "target_type": type_map.get(other.label_, "entity"),
                        "relation_type": rel_type,
                        "confidence": 0.65,
                        "evidence": sent.text.strip()
                    })
    
    return entities, relations

def _extract_regex_entities(text):
    """Regex-based OSINT entity extraction."""
    results = []
    seen = set()

    def add_match(m_type, val, norm, conf=0.9):
        key = (m_type, val)
        if key not in seen:
            results.append({
                "type": m_type,
                "value": val,
                "normalized": norm,
                "confidence": conf
            })
            seen.add(key)

    # CVE
    for m in RE_CVE.finditer(text):
        add_match("vulnerability", m.group().upper(), m.group().upper(), 0.95)

    # BTC
    for m in RE_BTC.finditer(text):
        add_match("crypto_btc", m.group(), m.group(), 0.9)

    # ETH
    for m in RE_ETH.finditer(text):
        add_match("crypto_eth", m.group(), m.group().lower(), 0.95)

    # IPv4
    for m in RE_IPV4.finditer(text):
        add_match("ip_address", m.group(), m.group(), 0.95)

    # Email
    for m in RE_EMAIL.finditer(text):
        add_match("email", m.group(), m.group().lower(), 0.98)

    # Domain
    for m in RE_DOMAIN.finditer(text):
        domain = m.group().lower()
        if not domain.endswith(('.py', '.js', '.png', '.jpg', '.css', '.html')): # Basic filter
            add_match("domain", domain, domain, 0.85)

    # SHA256
    for m in RE_HASH_SHA256.finditer(text):
        add_match("hash_sha256", m.group().lower(), m.group().lower(), 0.9)

    # ASN
    for m in RE_ASN.finditer(text):
        add_match("asn", m.group().upper(), m.group().upper(), 1.0)

    return results

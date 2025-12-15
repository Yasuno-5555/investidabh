import spacy
from textblob import TextBlob
import logging
import json
import networkx as nx
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class AdvancedNLP:
    def __init__(self):
        self.nlp = nlp

    def analyze_text(self, text):
        """
        Analyzes text to extract:
        1. Entities (NER)
        2. Sentiment Score (TextBlob)
        3. Relations (Heuristic)
        
        This is the synchronous, CPU-bound implementation.
        """
        doc = self.nlp(text)
        blob = TextBlob(text)

        # 1. Sentiment (Overall for simplicity, or per sentence)
        # We assign the sentence's sentiment to the entities found in it.
        overall_sentiment = blob.sentiment.polarity

        results = []
        unique_entities = {}

        # 2. Relation Extraction Heuristics
        # We look for connections in the dependency graph or co-occurrence in sentences.
        relations = []
        
        for sent in doc.sents:
            sent_blob = TextBlob(sent.text)
            sent_sentiment = sent_blob.sentiment.polarity
            
            # Find entities in this sentence
            sent_ents = [ent for ent in sent.ents if ent.label_ in ["ORG", "PERSON", "GPE", "LOC"]]
            
            # Pairwise relations in the same sentence
            if len(sent_ents) > 1:
                # Naive: Link all entities in the same sentence as "Related"
                # Refined: Look for specific patterns (e.g., PERSON works at ORG)
                for i in range(len(sent_ents)):
                    for j in range(i + 1, len(sent_ents)):
                        src = sent_ents[i]
                        dst = sent_ents[j]
                        
                        label = "Related"
                        # Simple rule: PERSON + ORG = "Affiliated"
                        if (src.label_ == "PERSON" and dst.label_ == "ORG") or \
                           (src.label_ == "ORG" and dst.label_ == "PERSON"):
                            label = "Affiliated"
                        
                        relations.append({
                            "src": src.text,
                            "dst": dst.text,
                            "label": label
                        })

            for ent in sent_ents:
                clean_val = ent.text.strip()
                if clean_val not in unique_entities:
                    unique_entities[clean_val] = {
                        "value": clean_val,
                        "type": ent.label_,
                        "confidence": 0.8, # spacy doesn't give conf, assume high
                        "sentiment": sent_sentiment, # Assign sentence sentiment to entity
                        "relations": []
                    }
                else:
                    # Average sentiment if extracted multiple times
                    prev_sent = unique_entities[clean_val]["sentiment"]
                    unique_entities[clean_val]["sentiment"] = (prev_sent + sent_sentiment) / 2

        # Attach relations to entities
        for rel in relations:
            # Add to source
            if rel["src"] in unique_entities:
                unique_entities[rel["src"]]["relations"].append({
                    "target": rel["dst"],
                    "label": rel["label"]
                })
            # Add to dest (undirected)
            if rel["dst"] in unique_entities:
                unique_entities[rel["dst"]]["relations"].append({
                    "target": rel["src"],
                    "label": rel["label"]
                })

        return list(unique_entities.values())

    async def analyze_text_async(self, text):
        """
        Non-blocking wrapper for analyze_text.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.analyze_text, text)

    async def save_results(self, investigation_id, results, conn):
        """
        Saves extracted intelligence to the database including Advanced NLP fields.
        Optimized with executemany.
        """
        try:
            async with conn.cursor() as cur:
                # Prepare batch data
                params_list = []
                for item in results:
                    # JSON serialization for metadata
                    metadata = json.dumps({"relations": item["relations"]})
                    
                    params_list.append((
                        investigation_id, 
                        item["type"], 
                        item["value"], 
                        item["confidence"], 
                        item["sentiment"], 
                        metadata
                    ))

                if params_list:
                    # Using ON CONFLICT with executemany is valid.
                    await cur.executemany(
                        """
                        INSERT INTO intelligence (investigation_id, entity_type, value, confidence_score, sentiment_score, metadata)
                        VALUES (%s, %s::entity_type_enum, %s, %s, %s, %s)
                        ON CONFLICT (investigation_id, entity_type, value) 
                        DO UPDATE SET 
                            confidence_score = EXCLUDED.confidence_score,
                            sentiment_score = EXCLUDED.sentiment_score,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                        """,
                        params_list
                    )
            await conn.commit()
            logger.info(f"Saved {len(results)} advanced intelligence items.")
        except Exception as e:
            logger.error(f"Failed to save advanced NLP results: {e}")

# Usage
nlp_advanced = AdvancedNLP()

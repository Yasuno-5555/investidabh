import spacy
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nlp_test")

def verify_nlp_heuristics():
    logger.info("[-] Loading NLP Model...")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.error("[!] Model not found.")
        return

    test_sentences = [
        "John Smith works for ACME Corp as a developer.",
        "Jane Doe is the CEO of Global Tech Inc.",
        "Bob Johnson at CyberSec Ltd reported the breach."
    ]

    logger.info(f"[-] Analyzing {len(test_sentences)} sentences...")

    for text in test_sentences:
        doc = nlp(text)
        relations = []
        
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
                        relations.append(f"{ent.text} -> {org.text}")

        logger.info(f"Text: '{text}' => Extracted: {relations}")
        if not relations:
            logger.warning(f"[!] Failed to extract relation from: {text}")

if __name__ == "__main__":
    verify_nlp_heuristics()

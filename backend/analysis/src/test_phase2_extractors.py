import sys
import os
import re

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nlp_analyzer import _extract_regex_entities, _process_text_sync

def test_extractors():
    test_text = """
    We found a vulnerability CVE-2023-12345 in our infrastructure.
    The attacker used a bitcoin wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa.
    Another ETH address 0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe was also found.
    The traffic originated from AS12345.
    Subdomains like dev.example.com and api.example.com were accessed.
    John Doe works for SecureCorp.
    """

    print("[-] Testing Regex Extractors...")
    entities = _extract_regex_entities(test_text)
    
    found_types = [e['type'] for e in entities]
    print(f"Found entity types: {set(found_types)}")
    
    for ent in entities:
        print(f"  [+] {ent['type']}: {ent['value']} (Conf: {ent['confidence']})")

    # Check for specific ones
    assert any(e['type'] == 'vulnerability' and 'CVE-2023-12345' in e['value'] for e in entities)
    assert any(e['type'] == 'crypto_btc' for e in entities)
    assert any(e['type'] == 'crypto_eth' for e in entities)
    assert any(e['type'] == 'asn' and 'AS12345' in e['value'] for e in entities)
    assert any(e['type'] == 'domain' and 'example.com' in e['value'] for e in entities)

    print("[-] Testing NLP Relations with Metadata...")
    _, relations = _process_text_sync(test_text)
    for rel in relations:
        print(f"  [R] {rel['source']} --({rel['relation_type']})--> {rel['target']}")
        print(f"      Confidence: {rel['confidence']}")
        print(f"      Evidence: {rel['evidence']}")
        
        assert 'confidence' in rel
        assert 'evidence' in rel
        assert len(rel['evidence']) > 0

    print("[!] All Phase 2 Extractors Verified!")

if __name__ == "__main__":
    test_extractors()

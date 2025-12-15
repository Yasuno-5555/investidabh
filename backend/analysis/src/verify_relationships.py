import asyncio
import sys
import os

# Adjust path to import modules
sys.path.append(os.path.join(os.getcwd(), 'backend', 'analysis', 'src'))

from entity_mapper import entity_mapper
from nlp_analyzer import analyze_and_save

# Mock DB for NLP test (Optional: just test the logic if possible, or run full stack)
# Since analyze_and_save writes to DB, we ideally want to test that or mock it.
# For simplicity, let's test EntityMapper directly and trust NLP logic or mock the DB call?
# Actually, nlp_analyzer requires a running DB. We can mock psycopg.

async def verify_entity_mapper():
    print("[-] Verifying Entity Mapper Static Linking...")
    
    # Test Email
    email_res = entity_mapper.map_entity({'value': 'john.doe@example.com', 'type': 'email'})
    print(f"Email Result: {email_res}")
    assert 'relations' in email_res['metadata']
    assert email_res['metadata']['relations'][0]['target'] == 'example.com'
    assert email_res['metadata']['relations'][0]['label'] == 'belongs_to'
    
    # Test Subdomain
    sub_res = entity_mapper.map_entity({'value': 'mail.google.com', 'type': 'subdomain'}, source_type='infra')
    print(f"Subdomain Result: {sub_res}")
    assert 'relations' in sub_res['metadata']
    assert sub_res['metadata']['relations'][0]['target'] == 'google.com'
    assert sub_res['metadata']['relations'][0]['label'] == 'subdomain_of'
    
    print("[+] Entity Mapper Verification Passed.")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(verify_entity_mapper())

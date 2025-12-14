import asyncio
import os
import psycopg
from nlp_advanced import nlp_advanced

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/investidubh")

async def verify():
    test_text = "Alice is the CEO of TechCorp. Bob works with her in Tokyo. They hate the CompetitorInc." 
    print(f"Testing with text: {test_text}")

    results = nlp_advanced.analyze_text(test_text)
    
    print("\n--- Extracted Results ---")
    for r in results:
        print(f"Entity: {r['value']} ({r['type']})")
        print(f"  Sentiment: {r['sentiment']:.2f}")
        print(f"  Relations: {r['relations']}")
        
        # Validation
        if r['value'] == "Alice" and r['type'] == "PERSON":
            print("  ✅ Alice detected as PERSON")
        if r['value'] == "TechCorp" and r['type'] == "ORG":
            print("  ✅ TechCorp detected as ORG")
        if r['value'] == "CompetitorInc":
             if r['sentiment'] < 0:
                 print("  ✅ Negative sentiment detected for CompetitorInc")
             else:
                 print("  ❌ Sentiment check failed for CompetitorInc")

    # DB Save Test (using dummy ID 0)
    print("\nTesting DB Save...")
    try:
        conn = await psycopg.AsyncConnection.connect(DATABASE_URL)
        await nlp_advanced.save_results(0, results, conn)
        await conn.close()
        print("✅ Save successful")
    except Exception as e:
        print(f"❌ Save failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify())

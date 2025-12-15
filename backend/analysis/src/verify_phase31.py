import asyncio
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_phase31")

# Import components
try:
    from enrichers import WhoisEnricher, DNSEnricher
    from alerts import AlertManager
    from ttp_map import TTPMapper
except ImportError:
    # Fix path if needed
    sys.path.append('.')
    from enrichers import WhoisEnricher, DNSEnricher
    from alerts import AlertManager
    from ttp_map import TTPMapper

async def verify_enrichers():
    logger.info("--- Verifying Enrichers ---")
    
    # 1. Whois
    w = WhoisEnricher()
    if w.can_handle('domain'):
        logger.info("[*] Testing WhoisEnricher with 'google.com'...")
        try:
            res = w.enrich('domain', 'google.com')
            if res and 'whois' in res:
                logger.info(f"[PASS] Whois result: {res['whois'].get('registrar')}")
            else:
                logger.error("[FAIL] Whois returned empty result")
        except Exception as e:
            logger.error(f"[FAIL] Whois failed: {e}")

    # 2. DNS
    d = DNSEnricher()
    if d.can_handle('domain'):
        logger.info("[*] Testing DNSEnricher with 'example.com'...")
        try:
            res = d.enrich('domain', 'example.com')
            if res and 'dns_records' in res:
                logger.info(f"[PASS] DNS records: {res['dns_records']}")
            else:
                logger.error("[FAIL] DNS returned empty result")
        except Exception as e:
            logger.error(f"[FAIL] DNS failed: {e}")

async def verify_ttp():
    logger.info("--- Verifying TTP Map ---")
    mapper = TTPMapper()
    text = "This looks like a phishing attempt with some sql injection and malware."
    logger.info(f"Text: {text}")
    tags = mapper.map_text(text)
    if 'T1566' in tags and 'T1190' in tags:
        logger.info(f"[PASS] TTPs identified: {tags}")
    else:
        logger.error(f"[FAIL] TTPs missing. Got: {tags}")

async def verify_alerts():
    logger.info("--- Verifying Alerts ---")
    am = AlertManager()
    am.load_watchlist(['bad.com'])
    
    # Mock redis publish
    class MockRedis:
        def publish(self, channel, msg):
            logger.info(f"[PASS] Redis Publish called on {channel}: {msg}")
            
    am.redis = MockRedis()
    
    logger.info("[*] Testing Watchlist Alert...")
    am.check_and_alert('domain', 'bad.com', {'role': 'test'})
    
    logger.info("[*] Testing No Alert...")
    am.check_and_alert('domain', 'good.com')

if __name__ == "__main__":
    asyncio.run(verify_enrichers())
    asyncio.run(verify_ttp())
    asyncio.run(verify_alerts())

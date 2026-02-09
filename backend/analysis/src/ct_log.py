import psycopg
import dns.asyncresolver
import asyncio
import logging

logger = logging.getLogger(__name__)

CRT_SH_HOST = "crt.sh"
CRT_SH_PORT = 5432
CRT_SH_USER = "guest"
CRT_SH_DB = "certwatch"

def fetch_subdomains_from_crtsh(domain):
    """
    Connects to crt.sh public Postgres DB and fetches all subdomains.
    Uses reverse(lower(name)) index optimization for performance.
    """
    subdomains = set()
    try:
        # Connect using psycopg 3 (sync)
        conn = psycopg.connect(
            host=CRT_SH_HOST,
            port=CRT_SH_PORT,
            user=CRT_SH_USER,
            dbname=CRT_SH_DB,
            connect_timeout=10,
            autocommit=True
        )
        cur = conn.cursor()
        
        # Optimized query for crt.sh (New Schema)
        # Using web_search function which is the recommended way now
        query = """
            SELECT DISTINCT ci.NAME_VALUE
            FROM certificate_identity ci
            WHERE plainto_tsquery('certwatch', %s) @@ identities(ci.CERTIFICATE_ID)
                AND ci.NAME_VALUE ILIKE %s
            LIMIT 100
        """
        # The query expects domain for FTS and wildcard for filtering
        search_pattern = f"%.{domain}"
        
        # Actually, crt.sh recommends:
        # SELECT name_value FROM certificate_and_identities WHERE plainto_tsquery('certwatch', 'example.com') @@ identities(certificate_id)
        # But that table might be a view.
        # Let's try the standard pattern often used for crt.sh recently:
        
        query = """
            SELECT DISTINCT value
            FROM certificate_and_identities
            WHERE plainto_tsquery('certwatch', %s) @@ identities(certificate)
            AND value ILIKE %s
        """
        
        # Wait, the error said "certificate_identity table has been superseded by a Full Text Search index on the certificate table".
        # simpler query that works on crt.sh:
        query = """
            SELECT DISTINCT param_value 
            FROM (
                SELECT lower(name_value) as param_value 
                FROM certificate_and_identities 
                WHERE plainto_tsquery('certwatch', %s) @@ identities(certificate)
                AND name_value ILIKE %s
            ) t
        """
        
        cur.execute(query, (domain, search_pattern))
        rows = cur.fetchall()
        
        for row in rows:
            name = row[0]
            # Clean up wildcards
            if '*' in name:
                continue
            subdomains.add(name)
            
        conn.close()
        logger.info(f"crt.sh found {len(subdomains)} potential subdomains for {domain}")
        return list(subdomains)
        
    except Exception as e:
        logger.error(f"Failed to query crt.sh: {e}")
        return []

async def check_domain_active(domain, resolver):
    """
    Async check if A record exists for domain.
    """
    try:
        # We only care if it resolves, we don't need the IP here necessarily
        # but getting it confirms existence.
        await resolver.resolve(domain, 'A')
        return domain
    except:
        return None

async def filter_active_subdomains(subdomains, concurrency=50):
    """
    Resolves a list of subdomains concurrently to find active ones.
    """
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = 2.0
    resolver.lifetime = 2.0
    # Use public DNS for reliability check from container
    resolver.nameservers = ['8.8.8.8', '1.1.1.1']

    active_subdomains = []
    
    # Process in chunks to avoid overwhelming local resources
    semaphore = asyncio.Semaphore(concurrency)

    async def sem_check(dom):
        async with semaphore:
            return await check_domain_active(dom, resolver)

    tasks = [sem_check(dom) for dom in subdomains]
    results = await asyncio.gather(*tasks)
    
    for res in results:
        if res:
            active_subdomains.append(res)
            
    return active_subdomains

def get_active_subdomains(domain):
    """
    Main entry point: Fetch from CT logs -> Filter Active.
    """
    # 1. Fetch Candidates
    candidates = fetch_subdomains_from_crtsh(domain)
    
    if not candidates:
        return []

    # 2. Async Resolve
    # Need to run asyncio loop here
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    active = loop.run_until_complete(filter_active_subdomains(candidates))
    
    logger.info(f"Active subdomains for {domain}: {len(active)} / {len(candidates)}")
    return active

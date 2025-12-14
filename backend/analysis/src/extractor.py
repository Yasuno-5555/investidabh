import os
import re
import socket
from urllib.parse import urlparse

def resolve_infrastructure(target_url):
    """Resolve Domain and IP from URL"""
    results = []
    try:
        parsed = urlparse(target_url)
        # Handle cases where urlparse might not get netloc if scheme is missing
        if not parsed.netloc:
             if "//" not in target_url:
                 parsed = urlparse("//" + target_url)
        
        domain = parsed.netloc.split(':')[0] # Remove port if present
        
        if not domain:
            return results

        # 1. Domain Entity
        results.append({
            'type': 'domain',
            'value': domain,
            'normalized': domain.lower(),
            'confidence': 1.0
        })

        # 2. IP Resolution
        try:
            ip_address = socket.gethostbyname(domain)
            results.append({
                'type': 'ip',
                'value': ip_address,
                'normalized': ip_address,
                'confidence': 1.0
            })
        except Exception as e:
            print(f"[!] IP Resolution failed: {e}")
        
    except Exception as e:
        print(f"[!] Infrastructure Resolution failed for {target_url}: {e}")
    
    return results

async def extract_and_save(investigation_id, target_url=""): # Added target_url
    """
    1. Fetch HTML from MinIO (using DB to find path)
    2. Infrastructure Recon (DNS/IP)
    3. Parse HTML
    4. Extract Entities (Email, Phone, SNS) with Normalization
    5. Save to Intelligence table
    """
    
    # 1. Get Artifact Path from DB
    html_path = None
    try:
        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as cur:
                await cur.execute(
                    "SELECT storage_path FROM artifacts WHERE investigation_id = %s AND artifact_type = 'html'",
                    (investigation_id,)
                )
                row = await cur.fetchone()
                if row:
                    html_path = row[0]
    except Exception as e:
        print(f"[!] DB Read Error: {e}")
        return

    if not html_path:
        print(f"[!] No HTML artifact found for {investigation_id}")
        return

    # 2. Fetch HTML from MinIO
    try:
        response = minio_client.get_object(BUCKET_NAME, html_path)
        html_content = response.read().decode('utf-8')
        response.close()
        response.release_conn()
    except Exception as e:
        print(f"[!] MinIO Fetch Error: {e}")
        return

    entities = []

    # --- [New] Infrastructure Recon (Phase 12/14) ---
    if target_url:
        # Phase 12: IP/Domain
        entities.extend(resolve_infrastructure(target_url))
        
        # Phase 14: Subdomain Hunter
        try:
            from ct_log import get_active_subdomains
            subdomains = get_active_subdomains(target_url.split('://')[-1].split('/')[0]) # Extract domain
            for sub in subdomains:
                entities.append({
                    'type': 'subdomain',
                    'value': sub,
                    'normalized': sub,
                    'confidence': 1.0
                })
        except Exception as e:
            print(f"[!] Subdomain Discovery Failed: {e}")

    # 3. Parse & Extract HTML Content (Present Day)
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text()
    

    def normalize_entity(entity_type, value):
        """Link Analysis Normalization"""
        if entity_type == 'email':
            return value.lower().strip()
        if entity_type == 'phone':
            return re.sub(r'\D', '', value) # Simple digits only
        if entity_type == 'social' or entity_type == 'domain':
            return value.lower().strip()
        return value.strip()

    # Emails
    emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))
    for email in emails:
        entities.append({
            'type': 'email',
            'value': email,
            'normalized': normalize_entity('email', email),
            'confidence': 0.9
        })

    # Phone Numbers (Loose regex)
    phones = set(re.findall(r'\+?[\d\-\(\)\s]{10,20}', text))
    for phone in phones:
        if sum(c.isdigit() for c in phone) > 6: 
            entities.append({
                'type': 'phone',
                'value': phone.strip(),
                'normalized': normalize_entity('phone', phone),
                'confidence': 0.6
            })

    # Social Links
    social_domains = ['twitter.com', 'x.com', 'facebook.com', 'linkedin.com', 'instagram.com', 'github.com', 'youtube.com']
    for link in soup.find_all('a', href=True):
        href = link['href']
        if any(d in href for d in social_domains):
            entities.append({
                'type': 'social',
                'value': href,
                'normalized': normalize_entity('social', href),
                'confidence': 0.8
            })

    # Page Title
    if soup.title and soup.title.string:
         val = f"Title: {soup.title.string.strip()}"
         entities.append({
             'type': 'entity',
             'value': val,
             'normalized': None, # No linking on titles usually
             'confidence': 1.0
         })

    print(f"[+] Extracted {len(entities)} entities for {investigation_id}")

    # --- [Phase 15] The Time Traveler (Historical) ---
    if target_url:
        try:
            from wayback import fetch_snapshots, get_historical_content
            snapshots = fetch_snapshots(target_url)
            
            for snap in snapshots:
                print(f"[*] Time Travel: Analyzing {snap['timestamp']}...")
                hist_html = get_historical_content(snap['url'])
                
                if hist_html:
                    hist_soup = BeautifulSoup(hist_html, 'html.parser')
                    hist_text = hist_soup.get_text()
                    
                    # Reuse extraction logic (Simplified for brevity, ideally refactor into function)
                    # Extract Emails
                    hist_emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', hist_text))
                    for email in hist_emails:
                        # Append with HISTORICAL timestamp
                        # Format YYYYMMDDHHMMSS -> YYYY-MM-DD HH:MM:SS
                        ts_str = snap['timestamp']
                        dt_iso = f"{ts_str[:4]}-{ts_str[4:6]}-{ts_str[6:8]} {ts_str[8:10]}:{ts_str[10:12]}:{ts_str[12:14]}+00"
                        
                        entities.append({
                            'type': 'email',
                            'value': email,
                            'normalized': normalize_entity('email', email),
                            'confidence': 0.8,
                            'created_at': dt_iso # Special field for history
                        })
        except Exception as e:
            print(f"[!] Time Travel Failed: {e}")

    # 4. Save to DB
    if entities:
        try:
            async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
                async with aconn.cursor() as cur:
                    for ent in entities:
                        # Default to NOW() if not historical
                        created_at = ent.get('created_at', 'NOW()')
                        
                        if created_at == 'NOW()':
                            await cur.execute(
                                """
                                INSERT INTO intelligence (investigation_id, type, value, normalized_value, confidence)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (investigation_id, ent['type'], ent['value'], ent['normalized'], ent['confidence'])
                            )
                        else:
                            await cur.execute(
                                """
                                INSERT INTO intelligence (investigation_id, type, value, normalized_value, confidence, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (investigation_id, ent['type'], ent['value'], ent['normalized'], ent['confidence'], created_at)
                            )
                await aconn.commit()
            print(f"[-] Saved intelligence data.")
        except Exception as e:
            print(f"[!] DB Write Error: {e}")

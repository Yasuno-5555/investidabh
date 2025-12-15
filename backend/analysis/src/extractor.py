import os
import re
import socket
import datetime
import json
import asyncio
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import psycopg
from minio import Minio

# Config
DB_DSN = os.getenv("DATABASE_URL", "postgresql://investidubh:secret@localhost:5432/investidubh_core")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.getenv("MINIO_BUCKET", "investigations")

# Setup MinIO Client locally to avoid circular imports
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def resolve_infrastructure(target_url):
    """Resolve Domain and IP from URL (Blocking)"""
    results = []
    try:
        parsed = urlparse(target_url)
        if not parsed.netloc:
             if "//" not in target_url:
                 parsed = urlparse("//" + target_url)
        
        domain = parsed.netloc.split(':')[0]
        
        if not domain:
            return results

        results.append({
            'type': 'domain',
            'value': domain,
            'normalized': domain.lower(),
            'confidence': 1.0
        })

        try:
            ip_address = socket.gethostbyname(domain)
            results.append({
                'type': 'ip',
                'value': ip_address,
                'normalized': ip_address,
                'confidence': 1.0
            })
        except Exception:
            pass
        
    except Exception as e:
        print(f"[!] Infrastructure Resolution failed for {target_url}: {e}")
    
    return results

async def extract_and_save(investigation_id, target_url=""): 
    """
    1. Fetch HTML from MinIO (using DB to find path)
    2. Infrastructure Recon (DNS/IP)
    3. Parse HTML
    4. Extract Entities (Email, Phone, SNS) with Normalization
    5. Save to Intelligence table
    """
    loop = asyncio.get_running_loop()

    # 1. Get Artifact Path from DB
    html_path = None
    try:
        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as cur:
                await cur.execute(
                    "SELECT storage_path, artifact_type FROM artifacts WHERE investigation_id = %s",
                    (investigation_id,)
                )
                rows = await cur.fetchall()
                for row in rows:
                    if row[1] == 'html':
                        html_path = row[0]
                    elif row[1] == 'raw_data':
                        await process_raw_data_artifact(investigation_id, row[0])
    except Exception as e:
        print(f"[!] DB Read Error: {e}")
        return

    # If no html path, skipping html part (handled implicitly by checks below)

    html_content = ""
    if html_path:
        # 2. Fetch HTML from MinIO (Offload blocking IO)
        try:
            def fetch_minio():
                try:
                    resp = minio_client.get_object(BUCKET_NAME, html_path)
                    data = resp.read().decode('utf-8')
                    resp.close()
                    resp.release_conn()
                    return data
                except Exception as ex:
                    print(f"[!] MinIO inner error: {ex}")
                    return ""

            html_content = await loop.run_in_executor(None, fetch_minio)
        except Exception as e:
            print(f"[!] MinIO Fetch Error: {e}")

    entities = []

    # --- [New] Infrastructure Recon (Phase 12/14) ---
    if target_url:
        # Phase 12: IP/Domain (Offload blocking DNS)
        infra_results = await loop.run_in_executor(None, resolve_infrastructure, target_url)
        entities.extend(infra_results)
        
        # Phase 14: Subdomain Hunter
        try:
            from ct_log import get_active_subdomains
            # Offload blocking CT log request
            domain_part = target_url.split('://')[-1].split('/')[0]
            if domain_part:
                subdomains = await loop.run_in_executor(None, get_active_subdomains, domain_part)
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
    if html_content:
        # Offload CPU-bound soup parsing
        def parse_html(content):
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text()
            extracted = []
            
            def normalize_entity(entity_type, value):
                if entity_type == 'email':
                    return value.lower().strip()
                if entity_type == 'phone':
                    return re.sub(r'\D', '', value)
                if entity_type == 'social' or entity_type == 'domain':
                    return value.lower().strip()
                return value.strip()

            # Emails
            emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))
            for email in emails:
                extracted.append({
                    'type': 'email',
                    'value': email,
                    'normalized': normalize_entity('email', email),
                    'confidence': 0.9
                })

            # Phone Numbers 
            phones = set(re.findall(r'\+?[\d\-\(\)\s]{10,20}', text))
            for phone in phones:
                if sum(c.isdigit() for c in phone) > 6: 
                    extracted.append({
                        'type': 'phone',
                        'value': phone.strip(),
                        'normalized': normalize_entity('phone', phone),
                        'confidence': 0.6
                    })

            # Social Links
            social_domains = ['twitter.com', 'x.com', 'facebook.com', 'linkedin.com', 'instagram.com', 'github.com', 'youtube.com']
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and any(d in href for d in social_domains):
                    extracted.append({
                        'type': 'social',
                        'value': href,
                        'normalized': normalize_entity('social', href),
                        'confidence': 0.8
                    })

            # Page Title
            if soup.title and soup.title.string:
                 val = f"Title: {soup.title.string.strip()}"
                 extracted.append({
                     'type': 'entity',
                     'value': val,
                     'normalized': None,
                     'confidence': 1.0
                 })
            
            return extracted

        html_entities = await loop.run_in_executor(None, parse_html, html_content)
        entities.extend(html_entities)

    print(f"[+] Extracted {len(entities)} entities for {investigation_id}")

    # --- [Phase 15] The Time Traveler (Historical) ---
    if target_url:
        try:
            from wayback import fetch_snapshots, get_historical_content
            # Offload blocking wayback calls
            snapshots = await loop.run_in_executor(None, fetch_snapshots, target_url)
            
            for snap in snapshots:
                # Offload blocking fetch
                hist_html = await loop.run_in_executor(None, get_historical_content, snap['url'])
                
                if hist_html:
                    # Offload parsing (using simple regex on text for speed/simplicity here, or full soup if needed)
                    # We'll do a quick regex scan in executor
                    def parse_hist(h_html):
                        h_soup = BeautifulSoup(h_html, 'html.parser')
                        h_text = h_soup.get_text()
                        h_emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', h_text))
                        return h_emails
                    
                    hist_emails = await loop.run_in_executor(None, parse_hist, hist_html)
                    
                    for email in hist_emails:
                        ts_str = snap['timestamp']
                        dt_iso = f"{ts_str[:4]}-{ts_str[4:6]}-{ts_str[6:8]} {ts_str[8:10]}:{ts_str[10:12]}:{ts_str[12:14]}+00"
                        
                        entities.append({
                            'type': 'email',
                            'value': email,
                            'normalized': email.lower().strip(),
                            'confidence': 0.8,
                            'created_at': dt_iso 
                        })
        except Exception as e:
            print(f"[!] Time Travel Failed: {e}")

    # 4. Save to DB (Batch Insert)
    if entities:
        await save_entities_batch(investigation_id, entities)


async def process_raw_data_artifact(investigation_id, storage_path):
    """
    Reads JSON artifact from MinIO and saves entities.
    Optimized: Batch inserts, Non-blocking I/O
    """
    from entity_mapper import entity_mapper
    loop = asyncio.get_running_loop()
    
    print(f"[*] Processing Raw Data: {storage_path}")
    
    try:
        def fetch_json():
            response = minio_client.get_object(BUCKET_NAME, storage_path)
            d = json.loads(response.read().decode('utf-8'))
            response.close()
            response.release_conn()
            return d

        data = await loop.run_in_executor(None, fetch_json)
        
        source_type = data.get('source_type', 'manual')
        extracted_entities = []
        items = data.get('data', [])
        if isinstance(items, dict): items = [items]
            
        for item in items:
            raws = []
            if source_type == 'rss':
                if item.get('title'):
                    raws.append({'value': item['title'], 'type': 'rss_article', 'metadata': {'link': item.get('link')}})
                if item.get('author'):
                     raws.append({'value': item['author'], 'type': 'person'})
                if item.get('link'):
                     raws.append({'value': item['link'], 'type': 'url'})

            elif source_type == 'sns':
                if item.get('account'):
                    acct = item['account']
                    if acct.get('url'):
                         raws.append({'value': acct['url'], 'type': 'mastodon_account'})
                    if acct.get('username'):
                         raws.append({'value': acct['username'], 'type': 'person'})
                if item.get('url'):
                    raws.append({'value': item['url'], 'type': 'url'})

            elif source_type == 'git':
                if item.get('login'):
                     raws.append({'value': item['login'], 'type': 'github_user'})
                if item.get('email'):
                     raws.append({'value': item['email'], 'type': 'email'})
                if item.get('company'):
                     raws.append({'value': item['company'], 'type': 'organization'})
                if item.get('url'):
                     raws.append({'value': item['url'], 'type': 'url'})
                     
            elif source_type == 'infra':
                if item.get('domain'):
                    raws.append({'value': item['domain'], 'type': 'subdomain'})
                if item.get('ip'):
                    raws.append({'value': item['ip'], 'type': 'ip'})

            for raw in raws:
                mapped = entity_mapper.map_entity(raw, source_type=source_type)
                # Normalize for internal list
                extracted_entities.append({
                    'type': mapped['entity_type'],
                    'value': mapped['value'],
                    'normalized': mapped['value'].lower(),
                    'confidence': mapped['confidence_score'],
                    'metadata': mapped['metadata'],
                    'source_type': mapped['source_type']
                })
        
        # Batch Save
        if extracted_entities:
            await save_entities_batch(investigation_id, extracted_entities)
                    
    except Exception as e:
        print(f"[!] Error processing raw data {storage_path}: {e}")

async def save_entities_batch(investigation_id, entities):
    """Helper to save entities in batch"""
    try:
        async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
            async with aconn.cursor() as cur:
                params_list = []
                for ent in entities:
                    val_type = ent.get('type')
                    val_value = ent.get('value')
                    val_norm = ent.get('normalized', val_value.lower() if val_value else '')
                    val_conf = ent.get('confidence', 0.8)
                    val_meta = ent.get('metadata', {})
                    val_source = ent.get('source_type', 'manual')
                    
                    if val_type in ['subdomain', 'ip']: val_source = 'infra'
                    elif val_type == 'social' and val_source == 'manual': pass 
                    elif ent.get('created_at'): val_source = 'wayback'
                    
                    val_created = ent.get('created_at') 
                    
                    if isinstance(val_meta, dict):
                        val_meta = json.dumps(val_meta)
                        
                    params_list.append((
                        investigation_id,
                        val_type,
                        val_value,
                        val_norm,
                        val_conf,
                        val_meta,
                        val_source,
                        val_created if val_created else datetime.datetime.now()
                    ))
                
                if params_list:
                    await cur.executemany(
                        """
                        INSERT INTO intelligence 
                        (investigation_id, entity_type, value, normalized_value, confidence_score, metadata, source_type, created_at)
                        VALUES (%s, %s::entity_type_enum, %s, %s, %s, %s, %s::source_type_enum, %s)
                        ON CONFLICT (investigation_id, entity_type, value) DO NOTHING
                        """,
                        params_list
                    )
            await aconn.commit()
            print(f"[-] Saved {len(entities)} intelligence items.")
    except Exception as e:
        print(f"[!] DB Batch Write Error: {e}")

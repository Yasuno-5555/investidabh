import os
import re
import socket
import datetime
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
                    "SELECT storage_path, artifact_type FROM artifacts WHERE investigation_id = %s",
                    (investigation_id,)
                )
                rows = await cur.fetchall()
                for row in rows:
                    if row[1] == 'html':
                        html_path = row[0]
                    elif row[1] == 'raw_data':
                        # New Logic for Phase 23/24
                        await process_raw_data_artifact(investigation_id, row[0])
    except Exception as e:
        print(f"[!] DB Read Error: {e}")
        return

    if not html_path:
        # It's possible we only have raw_data (e.g. RSS feed), so we shouldn't return if html missing but raw_data processed.
        # But legacy code depends on html_content.
        # If no HTML, we just skip the HTML parsing part.
        pass

    html_content = ""
    if html_path:
        # 2. Fetch HTML from MinIO
        try:
            response = minio_client.get_object(BUCKET_NAME, html_path)
            html_content = response.read().decode('utf-8')
            response.close()
            response.release_conn()
        except Exception as e:
            print(f"[!] MinIO Fetch Error: {e}")

    # ... continue with entities list ...
    entities = []

async def process_raw_data_artifact(investigation_id, storage_path):
    """
    Reads JSON artifact from MinIO and saves entities.
    """
    import json
    from entity_mapper import entity_mapper
    
    print(f"[*] Processing Raw Data: {storage_path}")
    
    try:
        response = minio_client.get_object(BUCKET_NAME, storage_path)
        data = json.loads(response.read().decode('utf-8'))
        response.close()
        response.release_conn()
        
        # Data format from collector:
        # { source_type: 'rss'|'sns'|'git'|'infra', data: [...] }
        source_type = data.get('source_type', 'manual')
        
        extracted_entities = []
        
        items = data.get('data', [])
        # If items is dict (e.g. single object), wrap in list
        if isinstance(items, dict):
            items = [items]
            
        for item in items:
            # Map item to raw_entity format for mapper
            # logic depends on source_type
            
            raws = []
            
            if source_type == 'rss':
                # RSS Item: title, link, summary
                if item.get('title'):
                    raws.append({'value': item['title'], 'type': 'rss_article', 'metadata': {'link': item.get('link')}})
                if item.get('author'):
                     raws.append({'value': item['author'], 'type': 'person'})
                if item.get('link'):
                     raws.append({'value': item['link'], 'type': 'url'})

            elif source_type == 'sns': # Mastodon/Twitter
                # Content, account, url
                # User
                if item.get('account'):
                    acct = item['account']
                    if acct.get('url'):
                         raws.append({'value': acct['url'], 'type': 'mastodon_account'})
                    if acct.get('username'):
                         raws.append({'value': acct['username'], 'type': 'person'})
                
                # Hashtags/Mentions (Need regex extraction from content?)
                # For now just use content as 'misc' or extract urls
                if item.get('content'):
                    # Trivial extractions
                    pass
                if item.get('url'):
                    raws.append({'value': item['url'], 'type': 'url'})

            elif source_type == 'git': # GitHub
                # login, name, email, company, html_url
                if item.get('login'):
                     raws.append({'value': item['login'], 'type': 'github_user'})
                if item.get('email'):
                     raws.append({'value': item['email'], 'type': 'email'})
                if item.get('company'):
                     raws.append({'value': item['company'], 'type': 'organization'})
                if item.get('url'):
                     raws.append({'value': item['url'], 'type': 'url'})
                     
            elif source_type == 'infra': # crt.sh
                if item.get('domain'):
                    raws.append({'value': item['domain'], 'type': 'subdomain'})
                if item.get('ip'):
                    raws.append({'value': item['ip'], 'type': 'ip'})

            # Process Raws
            for raw in raws:
                mapped = entity_mapper.map_entity(raw, source_type=source_type)
                
                # Insert directly here (duplicated logic from extract_and_save, should refactor but speed is key)
                async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
                    async with aconn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO intelligence 
                            (investigation_id, entity_type, value, normalized_value, confidence_score, metadata, source_type)
                            VALUES (%s, %s::entity_type_enum, %s, %s, %s, %s, %s::source_type_enum)
                            """,
                            (
                                investigation_id, 
                                mapped['entity_type'], 
                                mapped['value'], 
                                mapped['value'].lower(), # simple normalization 
                                mapped['confidence_score'], 
                                json.dumps(mapped['metadata']),
                                mapped['source_type']
                            )
                        )
                    await aconn.commit()
                    
    except Exception as e:
        print(f"[!] Error processing raw data {storage_path}: {e}")

# ... (rest of extract_and_save) ...

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
        from entity_mapper import entity_mapper
        import json

        try:
            async with await psycopg.AsyncConnection.connect(DB_DSN) as aconn:
                async with aconn.cursor() as cur:
                    for ent in entities:
                        # Prepare raw entity for mapping
                        # ent includes: type, value, normalized, confidence, created_at(optional)
                        
                        source_type = 'manual'
                        if ent.get('type') in ['subdomain', 'ip']:
                             source_type = 'infra'
                        elif ent.get('type') == 'social':
                             source_type = 'manual' # extracted from HTML
                        elif ent.get('created_at'):
                             source_type = 'wayback'
                             
                        raw_entity = {
                            'value': ent['value'],
                            'type': ent['type'],
                            'metadata': {}
                        }
                        
                        mapped = entity_mapper.map_entity(raw_entity, source_type=source_type)
                        
                        # Use mapped values but respect override confidence/data from extractor if needed
                        final_type = mapped['entity_type']
                        final_val = mapped['value']
                        final_conf = ent.get('confidence', mapped['confidence_score'])
                        final_meta = mapped['metadata']
                        
                        # Preserve normalized if present in original, else use mapped value
                        final_norm = ent.get('normalized', final_val.lower())
                        
                        created_at = ent.get('created_at') # None means default default

                        # Construct values
                        # (investigation_id, type, value, normalized_value, confidence, metadata, source_type, created_at)
                        
                        query = """
                            INSERT INTO intelligence 
                            (investigation_id, entity_type, value, normalized_value, confidence_score, metadata, source_type, created_at)
                            VALUES (%s, %s::entity_type_enum, %s, %s, %s, %s, %s::source_type_enum, %s)
                        """
                        params = (
                            investigation_id, 
                            final_type, 
                            final_val, 
                            final_norm, 
                            final_conf, 
                            json.dumps(final_meta),
                            source_type, 
                            created_at if created_at else datetime.datetime.now()
                        )
                        
                        # Handle created_at separately if needed, but parameterizing is safer.
                        # Note: 'created_at' in DB usually defaults to NOW(), but if we pass it explicitly it works.
                        # If created_at is None, we should pass NOW() or let DB handle it. 
                        # Easier to just pass datetime object.
                        
                        if not created_at:
                             # Let DB default handle it? No, query has 8 params.
                             # If we pass None for created_at, does it default? No, usually inserts NULL.
                             # We should modify the query or pass datetime.now()
                             params = (
                                investigation_id, 
                                final_type, 
                                final_val, 
                                final_norm, 
                                final_conf, 
                                json.dumps(final_meta),
                                source_type, 
                                datetime.datetime.now()
                            )
                        
                        await cur.execute(query, params)
                        
                await aconn.commit()
            print(f"[-] Saved intelligence data.")
        except Exception as e:
            print(f"[!] DB Write Error: {e}")

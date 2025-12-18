import requests
import datetime
import logging
import socket
import asyncio
import os

logger = logging.getLogger("infra-collector")

class InfraCollector:
    def __init__(self):
        self.max_subdomains = int(os.getenv("MAX_SUBDOMAINS", "500"))
        self.dns_concurrency = int(os.getenv("DNS_CONCURRENCY", "20"))

    async def collect(self, query: str) -> dict:
        """
        Collects infrastructure data (Subdomains via crt.sh).
        Query should be a domain name (e.g., example.com).
        """
        logger.info(f"Collecting infrastructure info for: {query}")
        
        loop = asyncio.get_running_loop()
        
        # Offload blocking http request
        subdomains = await loop.run_in_executor(None, self._get_crt_sh, query)
        
        # Limit the number of subdomains to prevent timeout/explosion
        subdomains_list = list(subdomains)
        if len(subdomains_list) > self.max_subdomains:
            logger.warning(f"Truncating subdomains from {len(subdomains_list)} to {self.max_subdomains}")
            subdomains_list = subdomains_list[:self.max_subdomains]
            
        logger.info(f"Resolving DNS for {len(subdomains_list)} subdomains...")
        
        # Parallel DNS Resolution with Semaphore
        semaphore = asyncio.Semaphore(self.dns_concurrency)
        
        async def sem_resolve(domain):
            async with semaphore:
                ip = await loop.run_in_executor(None, self._resolve_dns, domain)
                return {
                    "domain": domain,
                    "ip": ip
                }

        tasks = [sem_resolve(domain) for domain in subdomains_list]
        resolved_data = await asyncio.gather(*tasks)

        # Filter out None IPs if preferred? Or keep them to show existence?
        # User didn't specify, but keeping them shows "it exists but didn't resolve".

        return {
            "source_type": "infra",
            "source": "crt.sh",
            "query": query,
            "timestamp": datetime.datetime.now().isoformat(),
            "data": resolved_data,
            "count": len(resolved_data)
        }

    def _get_crt_sh(self, domain: str) -> set:
        # Blocking function
        # crt.sh rate limits: IP based. 
        # We try to be nice with headers and timeouts.
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; InvestidabhBot/1.0; +http://github.com/investidabh)'
        }
        
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        subs = set()
                        for entry in data:
                            name_value = entry.get('name_value')
                            if name_value:
                                for name in name_value.split('\n'):
                                    if '*' not in name:
                                        subs.add(name)
                        return subs
                    except ValueError:
                         logger.error("crt.sh returned non-JSON")
                         return set()
                elif resp.status_code in [502, 503, 504, 429]:
                     logger.warning(f"crt.sh error {resp.status_code}, retrying...")
                     import time
                     time.sleep(5 * (attempt + 1))
                else:
                    logger.error(f"crt.sh failed with status {resp.status_code}")
                    return set()
            except Exception as e:
                logger.error(f"crt.sh fetch failed: {e}")
                # Simple backoff
                import time
                time.sleep(2)
                
        return set()

    def _resolve_dns(self, domain: str) -> str | None:
        # Blocking function
        try:
            return socket.gethostbyname(domain)
        except:
            return None

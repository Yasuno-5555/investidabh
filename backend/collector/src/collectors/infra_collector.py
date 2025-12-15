import requests
import datetime
import logging
import socket
import asyncio

logger = logging.getLogger("infra-collector")

class InfraCollector:
    def __init__(self):
        pass

    async def collect(self, query: str) -> dict:
        """
        Collects infrastructure data (Subdomains via crt.sh).
        Query should be a domain name (e.g., example.com).
        """
        logger.info(f"Collecting infrastructure info for: {query}")
        
        loop = asyncio.get_running_loop()
        
        # Offload blocking http request
        subdomains = await loop.run_in_executor(None, self._get_crt_sh, query)
        
        # Resolve distinct subdomains
        resolved_data = []
        
        # We can resolve these concurrently if we want, but let's keep it simple first
        # Batch resolution? Or just sequential offloading?
        # Sequential offload is safer for rate limits, though slower.
        # Let's parallelize with gather for speed if list is small, but crt.sh can return thousands.
        # Let's stick to sequential offloading to avoid flooding DNS resolver or just offload bulk?
        # Actually resolving thousands of domains will take forever if sequential.
        # We should limit or assume we just want the domains. But we said we'd resolve.
        # For Optimization: Only resolve top 20 or use bulk?
        # Let's keep existing logic but prevent BLOCKING the event loop.
        
        for domain in subdomains:
            # Offload blocking DNS
            ip = await loop.run_in_executor(None, self._resolve_dns, domain)
            resolved_data.append({
                "domain": domain,
                "ip": ip
            })

        return {
            "source_type": "infra",
            "source": "crt.sh",
            "query": query,
            "timestamp": datetime.datetime.now().isoformat(),
            "data": resolved_data
        }

    def _get_crt_sh(self, domain: str) -> set:
        # Blocking function
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                subs = set()
                for entry in data:
                    name_value = entry.get('name_value')
                    if name_value:
                        for name in name_value.split('\n'):
                            if '*' not in name:
                                subs.add(name)
                return subs
        except Exception as e:
            logger.error(f"crt.sh fetch failed: {e}")
        return set()

    def _resolve_dns(self, domain: str) -> str:
        # Blocking function
        try:
            return socket.gethostbyname(domain)
        except:
            return None

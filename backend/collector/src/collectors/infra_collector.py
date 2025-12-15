import requests
import datetime
import logging
import socket

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
        
        subdomains = self._get_crt_sh(query)
        
        # Resolve distinct subdomains
        resolved_data = []
        for domain in subdomains:
            ip = self._resolve_dns(domain)
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
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                subs = set()
                for entry in data:
                    name_value = entry.get('name_value')
                    if name_value:
                        # name_value can be multi-line
                        for name in name_value.split('\n'):
                            if '*' not in name:
                                subs.add(name)
                return subs
        except Exception as e:
            logger.error(f"crt.sh fetch failed: {e}")
        return set()

    def _resolve_dns(self, domain: str) -> str:
        try:
            return socket.gethostbyname(domain)
        except:
            return None

import whois
import dns.resolver
import logging
import os
from typing import Dict, Any, Optional
from .base import BaseEnricher

logger = logging.getLogger(__name__)

class WhoisEnricher(BaseEnricher):
    def __init__(self):
        super().__init__("WhoisEnricher")

    def can_handle(self, entity_type: str) -> bool:
        return entity_type in ['domain']

    def enrich(self, entity_type: str, entity_value: str) -> Optional[Dict[str, Any]]:
        if not self.can_handle(entity_type):
            return None
            
        try:
            logger.info(f"Running WHOIS for {entity_value}")
            
            # OPSEC: Check for Tor Proxy
            proxy_url = os.getenv("TOR_PROXY_URL") 
            
            if proxy_url and proxy_url.startswith("socks5"):
                # python-whois wraps the 'whois' binary via subprocess.
                # Monkeypatching socket does not work. 
                # To convert this to Tor, the entire worker process should be run with 'torsocks',
                # or we must use a native python whois library that supports proxies.
                # For now, we log a warning as we cannot enforce proxying here.
                logger.warning(f"Tor Proxy configured but 'python-whois' does not support it natively. Ensure worker is running with 'torsocks' for OPSEC.")
            
            w = whois.whois(entity_value)

            # Convert to dict and Handle datetime objects for serialization if needed
            result = {
                "registrar": getattr(w, 'registrar', None),
                "creation_date": str(w.creation_date) if getattr(w, 'creation_date', None) else None,
                "expiration_date": str(w.expiration_date) if getattr(w, 'expiration_date', None) else None,
                "emails": getattr(w, 'emails', None),
                "org": getattr(w, 'org', None)
            }
            return {"whois": result}
        except Exception as e:
            logger.error(f"WHOIS lookup failed for {entity_value}: {e}")
            return None

class DNSEnricher(BaseEnricher):
    def __init__(self):
        super().__init__("DNSEnricher")
        self.resolver = dns.resolver.Resolver()
        # Use Google and Cloudflare DNS to avoid local blocking
        self.resolver.nameservers = ['8.8.8.8', '1.1.1.1']

    def can_handle(self, entity_type: str) -> bool:
        return entity_type in ['domain', 'subdomain']

    def enrich(self, entity_type: str, entity_value: str) -> Optional[Dict[str, Any]]:
        if not self.can_handle(entity_type):
            return None
            
        records = {}
        for rtype in ['A', 'MX', 'TXT', 'NS']:
            try:
                answers = self.resolver.resolve(entity_value, rtype)
                records[rtype] = [r.to_text() for r in answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, dns.resolver.Timeout):
                continue
            except Exception as e:
                logger.error(f"DNS lookup {rtype} failed for {entity_value}: {e}")
        
        if not records:
            return None
            
        return {"dns_records": records}

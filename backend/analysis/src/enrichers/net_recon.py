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
        return entity_type in ['domain', 'ip']

    def enrich(self, entity_type: str, entity_value: str) -> Optional[Dict[str, Any]]:
        if not self.can_handle(entity_type):
            return None
            
        try:
            logger.info(f"Running WHOIS for {entity_value} ({entity_type})")
            
            # OPSEC: Check for Tor Proxy
            proxy_url = os.getenv("TOR_PROXY_URL") 
            
            w = None
            if entity_type == 'domain':
                w = whois.whois(entity_value)
            elif entity_type == 'ip':
                # Try generic whois for IP
                try:
                    w = whois.whois(entity_value)
                except:
                    # Fallback to simple command if available (optional)
                    pass

            if not w:
                return None

            # Convert to dict and Handle datetime objects for serialization
            def safe_str(val):
                if isinstance(val, (list, tuple)):
                    return [str(v) for v in val]
                return str(val) if val else None

            result = {
                "registrar": getattr(w, 'registrar', None),
                "creation_date": safe_str(getattr(w, 'creation_date', None)),
                "expiration_date": safe_str(getattr(w, 'expiration_date', None)),
                "emails": getattr(w, 'emails', None),
                "org": getattr(w, 'org', None) or getattr(w, 'name', None),
                "country": getattr(w, 'country', None)
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

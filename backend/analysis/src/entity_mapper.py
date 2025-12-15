import re

class EntityMapper:
    def __init__(self):
        pass

    def map_entity(self, raw_entity: dict, source_type: str = 'manual') -> dict:
        """
        Refines a raw entity dictionary into a schema-compliant format.
        
        Args:
            raw_entity: {'value': '...', 'type': '...', 'context': '...'}
            source_type: 'rss', 'mastodon', 'github', 'infra'
            
        Returns:
            dict with keys: value, entity_type, source_type, confidence_score, metadata
        """
        value = raw_entity.get('value', '').strip()
        inferred_type = raw_entity.get('type', 'misc')
        metadata = raw_entity.get('metadata', {})
        confidence = 1.0

        # 1. Normalize Value
        if inferred_type == 'email':
            value = value.lower()
        
        # 2. Type Refinement Rules
        final_type = 'misc'
        
        # GitHub Handling
        if source_type == 'git':
            if inferred_type == 'user':
                final_type = 'github_user'
            elif inferred_type == 'repo':
                final_type = 'github_repo'
            elif inferred_type == 'email':
                final_type = 'email'
            elif inferred_type == 'organization':
                final_type = 'organization'
                
        # SNS Handling
        elif source_type == 'sns':
            if value.startswith('@'):
                final_type = 'mastodon_account' # defaulting strictly for now
            elif value.startswith('#'):
                final_type = 'hashtag'
            elif 'http' in value:
                final_type = 'url'
                
        # Infrastructure
        elif source_type == 'infra':
            if '.' in value and not value.replace('.', '').isdigit():
                final_type = 'subdomain'
            elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
                final_type = 'ip'
                
        # Fallback / Direct Mapping
        if final_type == 'misc':
             # Map allow-listed types directly
             allowed_types = [
                 'person', 'organization', 'location', 'email', 'phone', 
                 'url', 'company_product', 'position_title', 'rss_article'
             ]
             if inferred_type in allowed_types:
                 final_type = inferred_type
             elif inferred_type == 'subdomain':
                 final_type = 'subdomain'
             elif inferred_type == 'ip':
                 final_type = 'ip'

        # --- Phase 25: Static Relationship Linking ---
        relations = []
        
        # 1. Email -> Domain
        if final_type == 'email' and '@' in value:
             domain_part = value.split('@')[-1]
             relations.append({
                 "label": "belongs_to",
                 "target": domain_part,
                 "target_type": "domain" # Using generic domain, could be subdomain
             })
             
        # 2. Subdomain -> Domain
        if final_type == 'subdomain':
             parts = value.split('.')
             if len(parts) > 2:
                 # heuristic: take last 2 parts as domain (naive but works for .com, .org)
                 # better to use tldextract but we keep it zero-dependency simple for now
                 root_domain = ".".join(parts[-2:])
                 relations.append({
                     "label": "subdomain_of",
                     "target": root_domain,
                     "target_type": "domain"
                 })

        if relations:
            metadata['relations'] = relations

        return {
            "value": value,
            "entity_type": final_type,
            "source_type": source_type,
            "confidence_score": confidence,
            "metadata": metadata
        }

# Singleton instance
entity_mapper = EntityMapper()

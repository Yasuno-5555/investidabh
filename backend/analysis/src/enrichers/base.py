from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseEnricher(ABC):
    """Base class for all OSINT enrichers."""
    
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def enrich(self, entity_type: str, entity_value: str) -> Optional[Dict[str, Any]]:
        """
        Enrich the given entity with external data.
        
        Args:
            entity_type: The type of entity (e.g., 'domain', 'email', 'ip').
            entity_value: The value of the entity via string.
            
        Returns:
            A dictionary of enriched data or None if no data found/error.
        """
        pass
        
    def can_handle(self, entity_type: str) -> bool:
        """Override to specify which entity types this enricher handles."""
        return False

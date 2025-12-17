import logging
import json
import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class AlertManager:
    """
    Manages simple watchlist-based alerts.
    """
    def __init__(self, redis_client=None):
        self.redis = redis_client
        # Simple in-memory watchlist for MVP. 
        # Ideally this comes from DB or Redis.
        self.watchlist = set() 
        self.channel = "alerts"

    def load_watchlist(self, items: List[str]):
        """Load watchlist items."""
        for item in items:
            self.watchlist.add(item.lower())

    def check_and_alert(self, entity_type: str, entity_value: str, investigation_id: str, metadata: Dict[str, Any] = None):
        """
        Check if entity matches watchlist, if so, log/publish alert.
        """
        if entity_value.lower() in self.watchlist:
            self._trigger_alert(entity_type, entity_value, investigation_id, "Watchlist Match", metadata)
            
        # Potentially check enriched data too
        if metadata:
            pass

    def _trigger_alert(self, entity_type: str, entity_value: str, investigation_id: str, reason: str, metadata: Dict[str, Any]):
        alert_msg = {
            "type": "ALERT",
            "investigation_id": investigation_id,
            "entity": entity_value,
            "entity_type": entity_type,
            "reason": reason,
            "details": metadata,
            "timestamp": datetime.datetime.now().isoformat()
        }
        logger.warning(f"!!! ALERT TRIGGERED: {reason} for {entity_value} !!!")
        
        # Publish to Redis if available
        if self.redis:
            try:
                self.redis.publish(self.channel, json.dumps(alert_msg))
            except Exception as e:
                logger.error(f"Failed to publish alert to Redis: {e}")

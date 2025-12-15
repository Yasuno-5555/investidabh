import os
from mastodon import Mastodon
import datetime
import logging

logger = logging.getLogger("sns-collector")

class SNSCollector:
    def __init__(self):
        # Mastodon Setup - implicitly uses environment variables or anonymous if allowed
        # For 'free' scraping, we might not have client credentials yet, 
        # but Mastodon.py often requires app registration for search.
        # We'll try to use a public instance without auth if possible or require env vars.
        self.mastodon_base_url = os.getenv("MASTODON_BASE_URL", "https://mastodon.social")
        self.mastodon_token = os.getenv("MASTODON_ACCESS_TOKEN", None)
        
        self.mastodon = None
        if self.mastodon_token:
            self.mastodon = Mastodon(
                access_token=self.mastodon_token,
                api_base_url=self.mastodon_base_url
            )
        else:
            # Fallback or try unauthenticated public timeline if library supports it (often needs client_id)
            pass

    async def collect(self, query: str, platform: str = "mastodon") -> dict:
        """
        Searches SNS and returns structured data.
        
        Args:
            query: The search query (hashtag, keyword).
            platform: 'mastodon' or 'twitter'.
        """
        if platform == "mastodon":
            return await self._collect_mastodon(query)
        elif platform == "twitter":
            return await self._collect_twitter(query)
        else:
            raise ValueError(f"Unknown platform: {platform}")

    async def _collect_mastodon(self, query: str) -> dict:
        logger.info(f"Searching Mastodon for: {query}")
        results = []
        
        if self.mastodon:
            try:
                # Search for toots (statuses)
                search_res = self.mastodon.search(query, result_type='statuses')
                statuses = search_res.get('statuses', [])
                
                for status in statuses:
                    results.append({
                        "content": status.get('content', ''),
                        "url": status.get('url', ''),
                        "created_at": str(status.get('created_at', '')),
                        "account": {
                            "username": status['account'].get('username'),
                            "display_name": status['account'].get('display_name'),
                            "url": status['account'].get('url')
                        }
                    })
            except Exception as e:
                logger.error(f"Mastodon search error: {e}")
        else:
            logger.warning("Mastodon credentials not found. Skipping.")

        return {
            "source_type": "sns",
            "platform": "mastodon",
            "query": query,
            "timestamp": datetime.datetime.now().isoformat(),
            "data": results
        }

    async def _collect_twitter(self, query: str) -> dict:
        logger.info(f"Searching Twitter (Stub) for: {query}")
        # Real Twitter API v2 Free implementation would go here.
        # For now, return a placeholder to avoid breaking if called.
        return {
            "source_type": "sns",
            "platform": "twitter",
            "query": query,
            "timestamp": datetime.datetime.now().isoformat(),
            "note": "Twitter collection not configured or limited.",
            "data": []
        }

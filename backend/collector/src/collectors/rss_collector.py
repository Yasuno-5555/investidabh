import feedparser
import datetime
import logging

logger = logging.getLogger("rss-collector")

class RSSCollector:
    def __init__(self):
        pass

    async def collect(self, url: str) -> dict:
        """
        Fetches an RSS feed and returns structured data.
        
        Args:
            url: The RSS feed URL.
            
        Returns:
            dict: {
                "source_type": "rss",
                "source_url": url,
                "timestamp": datetime.datetime.now().isoformat(),
                "data": [list of items]
            }
        """
        logger.info(f"Fetching RSS feed: {url}")
        # feedparser is synchronous, might block event loop if not careful.
        # Ideally run in executor, but for now direct call is okay for MVP or use asyncio.to_thread if needed.
        feed = feedparser.parse(url)
        
        items = []
        for entry in feed.entries:
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", ""),
                "published": entry.get("published", ""),
                "author": entry.get("author", "")
            })
            
        return {
            "source_type": "rss",
            "source_url": url,
            "timestamp": datetime.datetime.now().isoformat(),
            "feed_title": feed.feed.get("title", ""),
            "data": items
        }

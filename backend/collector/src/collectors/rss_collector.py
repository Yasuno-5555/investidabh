import feedparser
import datetime
import logging
import asyncio

logger = logging.getLogger("rss-collector")

class RSSCollector:
    def __init__(self):
        pass

    async def collect(self, url: str) -> dict:
        """
        Fetches an RSS feed and returns structured data.
        """
        logger.info(f"Fetching RSS feed: {url}")
        
        loop = asyncio.get_running_loop()
        
        # Offload blocking feedparser
        # feedparser.parse can take a URL or string. If URL, it does network I/O blocking.
        feed = await loop.run_in_executor(None, feedparser.parse, url)
        
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

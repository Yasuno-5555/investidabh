from github import Github
import os
import datetime
import logging

logger = logging.getLogger("git-collector")

class GitCollector:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN", None)
        self.g = Github(self.github_token) if self.github_token else Github()

    async def collect(self, query: str) -> dict:
        """
        Searches GitHub for users or code and returns data.
        Arg: query (username or keyword)
        """
        logger.info(f"Searching GitHub for: {query}")
        results = []
        
        try:
            # Simple User Search
            users = self.g.search_users(query)
            # Limit to top 5 to avoid API limits on free tier
            for user in users[:5]:
                user_data = {
                    "login": user.login,
                    "name": user.name,
                    "company": user.company,
                    "blog": user.blog,
                    "location": user.location,
                    "email": user.email, # Public email only
                    "bio": user.bio,
                    "public_repos": user.public_repos,
                    "url": user.html_url
                }
                results.append(user_data)
                
        except Exception as e:
            logger.error(f"GitHub search error: {e}")

        return {
            "source_type": "git",
            "platform": "github",
            "query": query,
            "timestamp": datetime.datetime.now().isoformat(),
            "data": results
        }

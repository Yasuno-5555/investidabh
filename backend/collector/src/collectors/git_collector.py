from github import Github
import os
import datetime
import logging
import asyncio

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
            # Offload blocking PyGithub search
            loop = asyncio.get_running_loop()
            
            def search_gh_users():
                users = self.g.search_users(query)
                # Iterating over PaginatedList is blocking and lazy
                top_users = []
                for user in users[:5]:
                    top_users.append({
                        "login": user.login,
                        "name": user.name,
                        "company": user.company,
                        "blog": user.blog,
                        "location": user.location,
                        "email": user.email, 
                        "bio": user.bio,
                        "public_repos": user.public_repos,
                        "url": user.html_url
                    })
                return top_users
            
            user_data_list = await loop.run_in_executor(None, search_gh_users)
            results.extend(user_data_list)
                
        except Exception as e:
            logger.error(f"GitHub search error: {e}")

        return {
            "source_type": "git",
            "platform": "github",
            "query": query,
            "timestamp": datetime.datetime.now().isoformat(),
            "data": results
        }

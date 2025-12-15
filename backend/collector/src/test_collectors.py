import sys
import os
import asyncio

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from collectors.rss_collector import RSSCollector
from collectors.sns_collector import SNSCollector
from collectors.git_collector import GitCollector
from collectors.infra_collector import InfraCollector

async def test_instantiation():
    print("Testing RSSCollector...")
    rss = RSSCollector()
    assert rss is not None
    
    print("Testing SNSCollector...")
    sns = SNSCollector()
    assert sns is not None
    
    print("Testing GitCollector...")
    git = GitCollector()
    assert git is not None
    
    print("Testing InfraCollector...")
    infra = InfraCollector()
    assert infra is not None
    
    print("All collectors instantiated successfully.")

if __name__ == "__main__":
    asyncio.run(test_instantiation())

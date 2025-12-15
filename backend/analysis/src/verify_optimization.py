import sys
from unittest.mock import MagicMock, patch
import asyncio
import time
import threading
import json
import os

# --- 1. Setup Mocks BEFORE imports ---
sys.modules["spacy"] = MagicMock()
sys.modules["textblob"] = MagicMock()
sys.modules["psycopg"] = MagicMock()
sys.modules["networkx"] = MagicMock()
sys.modules["mastodon"] = MagicMock()
sys.modules["minio"] = MagicMock()
sys.modules["github"] = MagicMock()
sys.modules["ct_log"] = MagicMock()
sys.modules["bs4"] = MagicMock()
sys.modules["urllib3"] = MagicMock() # MinIO dep

# Spacy Mock
mock_nlp = MagicMock()
sys.modules["spacy"].load.return_value = mock_nlp
def side_effect_nlp(text):
    time.sleep(0.01)
    doc = MagicMock()
    doc.ents = []
    doc.sents = []
    return doc
mock_nlp.side_effect = side_effect_nlp

# TextBlob Mock
mock_blob = MagicMock()
mock_blob.sentiment.polarity = 0.5
sys.modules["textblob"].TextBlob.return_value = mock_blob

# --- 2. Imports ---
sys.path.append(os.path.abspath("backend/analysis/src"))
sys.path.append(os.path.abspath("backend/collector/src/collectors"))

try:
    from nlp_analyzer import analyze_and_save
    from nlp_advanced import AdvancedNLP
    from sns_collector import SNSCollector
    from infra_collector import InfraCollector
    from git_collector import GitCollector
    from extractor import extract_and_save, process_raw_data_artifact
except ImportError as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)

# --- 3. Tests ---

async def verify_phase1():
    print("[-] Verifying Phase 1 (NLP/SNS)...")
    # ... (Phase 1 tests skipped for brevity or can be re-run) ...
    pass 

async def verify_extractor():
    print("\n[-] Verifying extractor.py...")
    
    # Mock DB Connection/Cursor
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    async def async_cm_conn(): return mock_conn
    async def async_cm_cur(): return mock_cur
    
    # Patch psycopg locally for extractor
    with patch('psycopg.AsyncConnection.connect') as mock_connect:
        mock_connect.return_value.__aenter__ = async_cm_conn
        mock_cur.executemany = MagicMock(side_effect=lambda q, p: asyncio.sleep(0))
        mock_cur.fetchall = MagicMock(side_effect=lambda: asyncio.Future())
        mock_cur.fetchall.return_value.set_result([('raw_data_path.json', 'raw_data')])
        
        # Mock MinIO
        # Since we overwrote extractor, minio_client is initialized there.
        # We need to patch the instance in extractor module.
        import extractor
        extractor.minio_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "source_type": "rss",
            "data": [{"title": "Test RSS", "link": "http://example.com"}]
        }).encode('utf-8')
        extractor.minio_client.get_object.return_value = mock_resp

        # Run process_raw_data_artifact
        await process_raw_data_artifact("inv_1", "raw_data_path.json")

        if mock_cur.executemany.called:
             print("    [PASS] executemany was called (Batch Insert).")
        else:
             print("    [FAIL] executemany was NOT called.")

        # Test extract_and_save with blocking IO offload
    
    with patch('asyncio.base_events.BaseEventLoop.run_in_executor', wraps=asyncio.get_running_loop().run_in_executor) as mock_exec:
        # Reset DB mock to return HTML path
        mock_cur.fetchall.return_value = asyncio.Future()
        mock_cur.fetchall.return_value.set_result([('index.html', 'html')])
        extractor.minio_client.get_object.return_value.read.return_value = b"<html><body>Hello</body></html>"
        
        # Mock ct_log in modules
        import ct_log
        ct_log.get_active_subdomains.return_value = []

        await extract_and_save("inv_1", "http://example.com")
        
        # Check if executor was used for minio or resolution
        if mock_exec.called:
            print("    [PASS] run_in_executor was called (Blocking IO offload).")
        else:
            print("    [FAIL] run_in_executor was NOT called.")


async def verify_infra_collector():
    print("\n[-] Verifying infra_collector...")
    col = InfraCollector()
    
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{"name_value": "sub.example.com"}]
        
        with patch('socket.gethostbyname') as mock_socket:
            mock_socket.return_value = "1.2.3.4"
            
            with patch('asyncio.base_events.BaseEventLoop.run_in_executor', wraps=asyncio.get_running_loop().run_in_executor) as mock_exec:
                res = await col.collect("example.com")
                
                if mock_exec.call_count >= 1:
                    print(f"    [PASS] run_in_executor called {mock_exec.call_count} times.")
                else:
                    print("    [FAIL] run_in_executor NOT called.")
                
                if len(res['data']) > 0:
                    print("    [PASS] Data collected.")

async def verify_git_collector():
    print("\n[-] Verifying git_collector...")
    col = GitCollector()
    col.g = MagicMock()
    
    # Mock lazy list
    mock_user = MagicMock()
    mock_user.login = "testuser"
    col.g.search_users.return_value = [mock_user]
    
    with patch('asyncio.base_events.BaseEventLoop.run_in_executor', wraps=asyncio.get_running_loop().run_in_executor) as mock_exec:
        res = await col.collect("test")
        
        if mock_exec.called:
            print("    [PASS] run_in_executor called for PyGithub.")
        else:
             print("    [FAIL] run_in_executor NOT called.")

async def main():
    await verify_extractor()
    await verify_infra_collector()
    await verify_git_collector()

if __name__ == "__main__":
    asyncio.run(main())

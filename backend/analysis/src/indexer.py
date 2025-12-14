import os
import meilisearch
from bs4 import BeautifulSoup

# Meilisearch設定
MEILI_HOST = os.getenv("MEILI_HOST", "http://meilisearch:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")

# クライアント初期化 (エラーハンドリングは呼び出し元で行うこと推奨だが、ここでは簡易化)
try:
    client = meilisearch.Client(MEILI_HOST, MEILI_KEY)
    
    # インデックス作成 (主キー設定)
    # 実際にはサーバー起動時に一度だけやるべきだが、簡易実装として毎回確認/作成を試みる
    # もしくは create_index を使わずに get_or_create 的な挙動を利用する
    index = client.index('contents')
    index.update_settings({
        'searchableAttributes': ['text', 'title', 'url'],
        'filterableAttributes': ['investigation_id'],
        'displayedAttributes': ['investigation_id', 'title', 'url', 'snippet']
    })
except Exception as e:
    print(f"[!] Meilisearch Connection Error: {e}")
    client = None
    index = None

def strip_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    # スクリプトやスタイルを除去
    for script in soup(["script", "style", "meta", "noscript"]):
        script.decompose()
    
    text = soup.get_text(separator=' ', strip=True)
    return text[:100000] # 容量制限のため10万文字程度でカット

def index_content(investigation_id, url, html_content):
    if not index:
        print("[!] Meilisearch index not initialized.")
        return False

    try:
        text_content = strip_html(html_content)
        
        doc = {
            'id': investigation_id, # Meilisearchのdocument IDとして使用
            'investigation_id': investigation_id,
            'url': url,
            'title': url, # 本当はHTML titleタグを取得した方が良いが、今回はURLで代用
            'text': text_content,
            # 'indexed_at': str(os.getenv("TIMESTAMP", "")) # 必要なら追加
        }
        
        # 追加または更新
        task = index.add_documents([doc])
        print(f"[+] Indexed investigation {investigation_id} to Meilisearch.")
        return True
    except Exception as e:
        print(f"[!] Indexing failed: {e}")
        return False

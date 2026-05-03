# Investidubh CLI リファレンス

このドキュメントは、Investidubh CLIツールの全コマンド、オプション、および使用例を網羅したリファレンスです。

## グローバルオプション

これらのオプションは、すべてのコマンドで使用できます。

- `--api-url <URL>`: Investidubh APIのエンドポイントを指定します。デフォルトは `http://localhost:4001` です。環境変数 `API_URL` でも設定可能です。

---

## コマンド一覧

### `auth`

ユーザー認証を管理します。

#### `auth register`

新しいユーザーアカウントを登録します。

- **オプション:**
  - `--username`: 登録するユーザー名（指定しない場合はプロンプトが表示されます）。
  - `--password`: パスワード（指定しない場合はプロンプトが表示されます）。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py auth register
  ```

#### `auth login`

プラットフォームにログインし、認証トークンを取得・保存します。

- **オプション:**
  - `--username`: ログインするユーザー名（指定しない場合はプロンプトが表示されます）。
  - `--password`: パスワード（指定しない場合はプロンプトが表示されます）。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py auth login
  ```

---

### `scan`

新しいWeb調査を開始します。

- **引数:**
  - `URL`: 調査対象のURL（必須）。
- **オプション:**
  - `--wait`: 調査が完了するまで待機し、進捗スピナーを表示します。
- **使用例:**
  ```bash
  # 調査を開始
  python3 cli/investidubh_cli.py scan example.com

  # 完了まで待機
  python3 cli/investidubh_cli.py scan example.com --wait
  ```

---

### `list`

最近の調査を一覧表示します。

- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py list
  ```

---

### `show`

指定した調査の詳細情報を表示します。

- **引数:**
  - `ID`: 調査ID（必須）。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py show <investigation_id>
  ```

---

### `search`

インジケーター、エンティティ、または調査を検索します。

#### `search investigations`

調査とアーティファクトを全文検索します。

- **引数:**
  - `QUERY`: 検索クエリ（必須）。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py search investigations "admin panel"
  ```

#### `search indicator`

特定のインジケーター（IP、ドメイン、ハッシュなど）を検索します。

- **引数:**
  - `QUERY`: 検索するインジケーターの値（必須）。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py search indicator "8.8.8.8"
  ```

#### `search entity`

特定のエンティティ（メールアドレス、名前、組織など）を検索します。

- **引数:**
  - `QUERY`: 検索するエンティティの値（必須）。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py search entity "example@example.com"
  ```

---

### `entity`

エンティティの管理を行います。

#### `entity update`

特定のエンティティのメタデータを更新します。

- **引数:**
  - `TYPE`: エンティティの種類（例: `ip_address`, `domain`）。
  - `VALUE`: エンティティの値（例: `8.8.8.8`）。
- **オプション:**
  - `--metadata`: 更新するメタデータのJSON文字列（必須）。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py entity update ip_address 8.8.8.8 --metadata '{"note": "Known malicious"}'
  ```

---

### `alerts`

リアルタイムアラートの監視を行います。

#### `alerts stream`

プラットフォームから送信されるリアルタイムアラートをストリーミング表示します。

- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py alerts stream
  ```

---

### `graph`

システム全体のエンティティとそれらの関係（グローバルグラフ）を取得します。

- **オプション:**
  - 実行後、結果を `graph.json` に保存するかどうかを尋ねるプロンプトが表示されます。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py graph
  ```

---

### `timeline`

指定した調査の時系列イベントデータを取得します。

- **引数:**
  - `ID`: 調査ID（必須）。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py timeline <investigation_id>
  ```

---

### `report`

指定した調査のPDFレポートを生成し、ダウンロードします。

- **引数:**
  - `ID`: 調査ID（必須）。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py report <investigation_id>
  ```

---

### `audit`

指定した調査の証拠の連鎖（Chain of Custody）ログを取得します。

- **引数:**
  - `ID`: 調査ID（必須）。
- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py audit <investigation_id>
  ```

---

### `verify`

システム全体のアーティファクトの整合性チェックを実行します（管理者向け）。

- **使用例:**
  ```bash
  python3 cli/investidubh_cli.py verify
  ```

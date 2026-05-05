# Sentinel RAG - セットアップ & 使い方ガイド

## 目次

1. [システム要件](#システム要件)
2. [クイックスタート](#クイックスタート)
3. [環境変数の設定](#環境変数の設定)
4. [起動と停止](#起動と停止)
5. [初回ログイン](#初回ログイン)
6. [GUI の使い方](#gui-の使い方)
7. [API の使い方](#api-の使い方)
8. [LLM プロバイダー設定](#llm-プロバイダー設定)
9. [監視スタックの有効化](#監視スタックの有効化)
10. [バックアップとリストア](#バックアップとリストア)
11. [トラブルシューティング](#トラブルシューティング)

---

## システム要件

| 項目 | 最小 | 推奨 |
|------|------|------|
| CPU | 4 コア | 8 コア以上 |
| メモリ | 16 GB | 32 GB以上 |
| ストレージ | 50 GB | 200 GB以上 (SSD) |
| OS | Linux / Windows 10+ / macOS | Ubuntu 22.04 LTS |
| Docker | 24.0+ | 最新安定版 |
| Docker Compose | v2.20+ | 最新安定版 |

Ollama でローカル LLM を使用する場合、十分なメモリが必要です（3B モデルで約 4GB、7B モデルで約 8GB）。

---

## クイックスタート

```bash
# 1. リポジトリのクローン
git clone https://github.com/your-org/sentinel-rag.git
cd sentinel-rag

# 2. 環境変数ファイルの作成
cp .env.example .env

# 3. .env を編集してパスワードを設定（後述）
# 最低限 POSTGRES_PASSWORD, REDIS_PASSWORD, QDRANT_API_KEY, MINIO_ROOT_PASSWORD,
# SECRET_KEY を変更してください

# 4. フロントエンドのビルド
cd services/frontend
npm install
npm run build
cd ../..

# 5. Docker Compose で起動
docker compose up -d

# 6. フロントエンドをデプロイ
docker run --rm \
  -v sentinel-rag_frontend_build:/html \
  -v "$(pwd)/services/frontend/dist:/src:ro" \
  alpine sh -c "cp -r /src/* /html/"

# 7. Ollama モデルのダウンロード（初回のみ）
docker exec sentinel-ollama ollama pull nomic-embed-text
docker exec sentinel-ollama ollama pull qwen2.5:3b

# 8. ブラウザでアクセス
#   開発: http://localhost:8080
#   本番: https://your-domain.com
```

---

## 環境変数の設定

`.env.example` をコピーして `.env` を作成し、以下の項目を必ず変更してください。

### 必須項目

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `SECRET_KEY` | JWT 署名用の秘密鍵（64文字以上推奨） | `openssl rand -hex 32` で生成 |
| `POSTGRES_PASSWORD` | PostgreSQL パスワード | 強力なパスワード |
| `REDIS_PASSWORD` | Redis パスワード | 強力なパスワード |
| `QDRANT_API_KEY` | Qdrant API キー | 任意の文字列 |
| `MINIO_ROOT_USER` | MinIO 管理者ユーザー名 | `sentinel-admin` |
| `MINIO_ROOT_PASSWORD` | MinIO 管理者パスワード（8文字以上） | 強力なパスワード |
| `ALLOWED_HOSTS` | 許可するホスト名 | `rag.example.com` |

### LLM プロバイダー（任意）

| 変数名 | 説明 |
|--------|------|
| `DEFAULT_LLM_PROVIDER` | デフォルト LLM（`ollama` / `anthropic` / `openai` / `google`） |
| `DEFAULT_EMBEDDING_PROVIDER` | デフォルト埋め込み（`ollama` / `openai` / `google`） |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) API キー |
| `OPENAI_API_KEY` | OpenAI API キー |
| `GOOGLE_API_KEY` | Google (Gemini) API キー |

デフォルトは Ollama（ローカル推論）で、外部 API キー不要です。

---

## 起動と停止

```bash
# 全サービス起動（開発モード）
docker compose up -d

# ログ確認
docker compose logs -f api worker

# 個別サービスのログ
docker logs sentinel-api -f
docker logs sentinel-worker -f

# 全サービス停止
docker compose down

# データボリュームも含めて完全削除
docker compose down -v
```

### コンテナ構成

| コンテナ | 役割 | ポート (開発時) |
|---------|------|----------------|
| sentinel-nginx | リバースプロキシ / 静的ファイル配信 | 8080 (HTTP), 443 (HTTPS) |
| sentinel-api | FastAPI アプリケーション | 8000 |
| sentinel-worker | Celery ワーカー (文書処理) | - |
| sentinel-beat | Celery Beat (定期タスク) | - |
| sentinel-ollama | ローカル LLM サーバー | 11434 |
| sentinel-postgres | データベース | 5432 |
| sentinel-redis | キャッシュ / メッセージブローカー | 6379 |
| sentinel-qdrant | ベクトルデータベース | 6333 |
| sentinel-minio | オブジェクトストレージ | 9000, 9001 |

### ヘルスチェック

```bash
# 全コンテナの状態確認
docker ps --format "table {{.Names}}\t{{.Status}}"

# API ヘルスチェック
curl http://localhost:8000/api/v1/health

# 詳細ヘルスチェック (認証必要)
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/v1/health/ready
```

---

## 初回ログイン

初回起動時、デフォルトのテナントと管理者ユーザーが自動作成されます。

1. ブラウザで `http://localhost:8080` にアクセス
2. 以下の情報でログイン:
   - **メール**: `admin@sentinel.local`
   - **パスワード**: 不要（開発モードではメールのみで認証）

> **本番環境**: OIDC/SSO を設定するか、`auth.py` でパスワード認証を有効化してください。

### ユーザーロール

| ロール | 権限 |
|--------|------|
| `system_admin` | 全操作。テナント管理、ユーザー管理、プロバイダー設定 |
| `tenant_admin` | テナント内の全操作。ユーザー管理 |
| `content_manager` | ドキュメントのアップロード・削除、チャット |
| `user` | ドキュメント閲覧、チャット、自分がアップロードしたファイルの削除 |
| `auditor` | 監査ログの閲覧（読み取り専用） |
| `read_only` | ドキュメント閲覧、チャットのみ |

---

## GUI の使い方

### Dashboard

システム全体の概要を表示します。
- ドキュメント数、クエリ数、ユーザー数
- 最近のクエリ履歴

### Chat（質問応答）

RAG ベースの質問応答インターフェースです。

1. テキストボックスに質問を入力
2. Enter キーまたは送信ボタンで質問を送信
3. AI がドキュメントから関連情報を検索し、回答を生成
4. 回答の下に参照元ドキュメント（ソース）が表示されます

### Documents（ドキュメント管理）

ドキュメントのアップロード・管理・内容確認ができます。

**アップロード:**
1. 「Upload」ボタンをクリック
2. ファイルを選択（複数選択可）
3. アップロード後、自動的にインジェスションパイプラインが開始
   - テキスト抽出 → DLP スキャン → チャンキング → 埋め込み生成 → ベクトル DB 登録

**ステータス:**
| ステータス | 意味 |
|-----------|------|
| `pending` | アップロード済み、処理待ち |
| `processing` | テキスト抽出・埋め込み生成中 |
| `indexed` | 処理完了、検索可能 |
| `failed` | 処理失敗 |

**ドキュメント詳細:**
- ドキュメント一覧の行をクリックすると、右側にチャンクの内容が表示されます
- 各チャンクのインデックス番号、トークン数、テキスト内容を確認できます

**対応ファイル形式:**
- テキスト: `.txt`, `.md`, `.rst`, `.csv`, `.json`, `.yaml`, `.xml`
- オフィス: `.pdf`, `.docx`, `.xlsx`, `.pptx`（unstructured ライブラリ経由）
- 最大ファイルサイズ: 100 MB

### Settings

ユーザー設定の表示・変更。

### Admin（管理者のみ）

- **Tenants**: テナントの作成・管理
- **Users**: ユーザーの作成・ロール変更
- **Providers**: LLM プロバイダーの設定・有効化
- **Audit Log**: 監査ログの検索・閲覧
- **Health**: システムのヘルスステータス

---

## API の使い方

ベース URL: `http://localhost:8000/api/v1`

### 認証

```bash
# トークン取得
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sentinel.local"}' | jq -r '.access_token')

# 以降のリクエストでヘッダーに付与
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
```

### ドキュメント操作

```bash
# ドキュメント一覧
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/documents

# ドキュメントアップロード
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf" \
  http://localhost:8000/api/v1/documents

# ドキュメント詳細
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/documents/{document_id}

# ドキュメントのチャンク取得
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/documents/{document_id}/chunks

# ドキュメント削除（ソフトデリート）
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/documents/{document_id}
```

### 質問応答

```bash
# 質問を投げる
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "このドキュメントは何について書かれていますか？"}' \
  http://localhost:8000/api/v1/qa/ask

# 質問履歴
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/qa/history
```

### 管理 API

```bash
# テナント一覧
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/admin/tenants

# ユーザー一覧
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/admin/users

# 監査ログ
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/admin/audit-logs

# ヘルスチェック (詳細)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/health/ready
```

---

## LLM プロバイダー設定

### Ollama（デフォルト / ローカル推論）

外部 API キー不要。初回起動時にモデルをダウンロードしてください。

```bash
# 推論モデル
docker exec sentinel-ollama ollama pull qwen2.5:3b    # 軽量 (推奨)
docker exec sentinel-ollama ollama pull qwen2.5:7b    # 高品質

# 埋め込みモデル
docker exec sentinel-ollama ollama pull nomic-embed-text
```

### 外部プロバイダー

`.env` に API キーを設定後、GUI の Admin > Providers から有効化するか、API で設定します。

```bash
# プロバイダー有効化の例
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": true}' \
  http://localhost:8000/api/v1/admin/providers/{provider_id}
```

**機密度による制限**: `confidential` / `restricted` レベルのドキュメントは外部 LLM API に送信されません（Ollama のみ使用可能）。

---

## 監視スタックの有効化

Prometheus + Grafana + Loki によるモニタリングが利用可能です。

```bash
# 監視スタックを含めて起動
docker compose --profile monitoring up -d

# Grafana にアクセス
# URL: https://your-domain.com/grafana/
# デフォルト: admin / admin
```

---

## バックアップとリストア

```bash
# データベースバックアップ
./scripts/backup.sh

# リストア
./scripts/restore.sh <backup-file>
```

バックアップ対象:
- PostgreSQL データベース
- MinIO オブジェクトストレージ
- Qdrant ベクトルデータ

---

## トラブルシューティング

### コンテナが起動しない

```bash
# コンテナのステータスと理由を確認
docker ps -a --format "table {{.Names}}\t{{.Status}}"

# エラーログの確認
docker logs sentinel-api --tail 50
docker logs sentinel-worker --tail 50
```

### ドキュメントが `pending` のまま

Celery ワーカーが正常に動作しているか確認:

```bash
docker logs sentinel-worker --tail 20
# "ready" メッセージとキュー名を確認
```

Ollama モデルがダウンロード済みか確認:

```bash
docker exec sentinel-ollama ollama list
# nomic-embed-text と qwen2.5:3b が表示されること
```

### ドキュメントが `failed` になる

```bash
# ワーカーログでエラー詳細を確認
docker logs sentinel-worker 2>&1 | grep -A 5 "ingestion_failed"
```

よくある原因:
- Ollama モデル未ダウンロード
- メモリ不足（Ollama の埋め込み生成に必要）
- 非対応ファイル形式

### API に接続できない

```bash
# API コンテナのヘルスチェック
curl http://localhost:8000/api/v1/health

# nginx 経由
curl http://localhost:8080/api/v1/health
```

### データの完全リセット

```bash
docker compose down -v
docker compose up -d
# → 全データが削除され、初期状態から再スタート
```

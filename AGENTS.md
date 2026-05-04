# Sentinel RAG Platform

エンタープライズ向けオンプレミスRAGプラットフォーム。単一VM / Docker Compose構成。

## 技術スタック
- Backend: Python 3.11+ / FastAPI / Celery / SQLAlchemy
- Frontend: React 18 / TypeScript / Vite / Tailwind CSS
- Data: PostgreSQL 16 / Qdrant / Redis 7 / MinIO
- AI: Anthropic / OpenAI / Google / Ollama
- Infra: Docker Compose / nginx / Prometheus / Grafana / Loki
- Package: uv (Python) / npm (Frontend)

## ディレクトリ構成
```
sentinel-rag/
├── docker-compose.yml          # 本番構成
├── docker-compose.override.yml # 開発用オーバーライド
├── .env.example
├── config/                     # nginx, postgres, prometheus等の設定
├── services/
│   ├── api/                    # FastAPI + Celery (Python)
│   │   └── src/
│   │       ├── main.py         # FastAPIアプリ
│   │       ├── api/routes/     # エンドポイント
│   │       ├── core/           # RAGパイプライン, チャンカー
│   │       ├── providers/      # LLMプロバイダー抽象化
│   │       ├── security/       # DLP, RBAC, 暗号化
│   │       ├── models/         # SQLAlchemy モデル
│   │       ├── audit/          # 監査ログ (ハッシュチェーン)
│   │       └── worker/         # Celery タスク
│   └── frontend/               # React SPA
│       └── src/
│           ├── pages/          # Dashboard, Chat, Documents, Admin
│           ├── components/     # 共通コンポーネント
│           └── lib/            # API client, store
├── scripts/                    # backup, restore, health-check
└── docs/                       # アーキテクチャ, デプロイ, セキュリティ
```

## コーディング規約
- Python: ruff (E,F,I,N,W,UP,S,B,A,C4,SIM), line-length 100, 型ヒント必須
- TypeScript: strict mode, ESLint
- ファイル命名: snake_case (Python), kebab-case (TS/config)
- テストカバレッジ 80%以上を目標

## 開発コマンド
```bash
# 開発環境起動
docker compose up -d

# API テスト
cd services/api && uv run pytest

# フロントエンド
cd services/frontend && npm run dev

# リント
cd services/api && uv run ruff check src/
cd services/frontend && npm run lint

# 型チェック
cd services/api && uv run mypy src/
cd services/frontend && npm run typecheck
```

## 制約
- `.env`, `secrets/` を絶対にコミットしない
- APIキーは平文保存禁止（Vault or pgcrypto暗号化）
- 機密度 confidential/restricted のデータは外部LLM API送信禁止
- RLSを迂回するクエリを書かない
- コンテナ間通信は内部ネットワーク経由のみ

## エージェントロール
- explorer / planner / generator / critic / evaluator

## 推奨ワークフロー
- 複雑: Explorer → Planner → Generator → Critic → Evaluator
- 簡単: Generator → Evaluator

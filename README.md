# Sentinel RAG

エンタープライズ向けオンプレミスRAGプラットフォーム。

## 概要

大規模で利用可能なRAGプラットフォーム。単一VM上にDocker Composeで構築し、マルチテナント・エンタープライズ認証・コンプライアンス対応を実現。

### 主要機能

- **マルチテナント**: PostgreSQL RLS + Qdrant Collection分離 + MinIOバケット分離
- **マルチLLMプロバイダー**: Claude / OpenAI / Gemini / Ollama（ローカル）
- **DLP（情報漏洩防止）**: マイナンバー、クレジットカード等の自動検出・機密度分類
- **機密度ベースLLMルーティング**: confidential/restrictedデータは外部API送信禁止
- **監査ログ**: SHA-256ハッシュチェーンによる改ざん検知
- **RBAC**: 6段階のロールベースアクセス制御
- **SSO対応**: SAML2.0 / OpenID Connect

## クイックスタート

```bash
# 1. 環境変数を設定
cp .env.example .env
# .env を編集してパスワード等を設定

# 2. 起動（開発モード）
docker compose up -d

# 3. ヘルスチェック
curl http://localhost:8000/api/v1/health/ready

# 4. フロントエンド開発
cd services/frontend
npm install
npm run dev
```

## 技術スタック

| 領域 | 技術 |
|---|---|
| Backend | Python 3.11+ / FastAPI / Celery |
| Frontend | React 18 / TypeScript / Vite / Tailwind CSS |
| Database | PostgreSQL 16 (RLS) / Qdrant / Redis 7 |
| Storage | MinIO (S3互換) |
| AI/LLM | Anthropic / OpenAI / Google / Ollama |
| Auth | OIDC / SAML2.0 / Casbin RBAC |
| Monitoring | Prometheus / Grafana / Loki |
| Container | Docker Compose v2 |

## ドキュメント

- [アーキテクチャ](docs/architecture.md)
- [デプロイガイド](docs/deployment.md)
- [セキュリティ](docs/security.md)
- [要件定義](docs/requirements.md)

## ライセンス

Private - All rights reserved.

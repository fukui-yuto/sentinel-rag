# 要件定義

## プロジェクト概要

グループ企業全社（1000人以上）で利用可能なオンプレミスRAGプラットフォーム。
単一VM上にDocker Composeで構築。

## 主要要件

- 単一VMデプロイ: 16 vCPU / 64GB RAM / GPUなし
- Docker Compose構成
- マルチLLMプロバイダー対応 (Claude / OpenAI / Gemini / Ollama)
- クローズド環境対応 (完全エアギャップ時はOllamaのみ)
- マルチテナント (部署・グループ会社単位)
- エンタープライズ認証 (SSO / MFA / RBAC)
- 完全な監査証跡

## 制約事項

| 項目 | 制約 | 緩和策 |
|---|---|---|
| 可用性 | 単一VMのためSPOF | 自動再起動・ヘルスチェック (稼働率99%目標) |
| DR | リアルタイム冗長化なし | 日次バックアップ (RPO≤24h, RTO≤4h) |
| スケール | 垂直のみ | 同時接続50-200、コンテナ並列で対応 |
| GPU | なし | Embeddingはcpu、大型LLMは外部API |

## 想定ワークロード

- 登録ユーザー: 1000+
- 同時アクティブ: 50-200
- 日次クエリ: 5000-10000
- ドキュメント総数: 10万件以下
- データ総量: 500GB以下

## コンプライアンス

SOC2 / ISO27001 / HIPAA / PCI-DSS / GDPR / 個人情報保護法に可能な範囲で準拠。

## API エンドポイント

### 認証
- `GET /api/v1/auth/login` - SSO リダイレクト
- `POST /api/v1/auth/callback` - OIDC コールバック
- `POST /api/v1/auth/logout` - ログアウト
- `GET /api/v1/auth/me` - ユーザー情報

### ドキュメント
- `GET /api/v1/documents` - 一覧 (テナントスコープ)
- `POST /api/v1/documents` - アップロード
- `GET /api/v1/documents/{id}` - 詳細
- `DELETE /api/v1/documents/{id}` - 論理削除

### QA
- `POST /api/v1/qa/query` - RAG実行
- `POST /api/v1/qa/query/stream` - SSEストリーミング
- `GET /api/v1/qa/history` - 対話履歴

### 管理
- `CRUD /api/v1/admin/tenants` - テナント管理
- `CRUD /api/v1/admin/users` - ユーザー管理
- `GET/PUT /api/v1/admin/providers` - LLMプロバイダー設定
- `GET /api/v1/admin/audit-logs` - 監査ログ
- `GET /api/v1/admin/health` - システムヘルス
- `GET /api/v1/admin/metrics` - 使用状況

### 同期
- `GET /api/v1/sync/status` - 同期状態
- `POST /api/v1/sync/trigger` - 手動同期

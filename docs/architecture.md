# アーキテクチャ

## 論理構成

```
                    ┌─────────────┐
                    │   nginx     │ TLS終端 / WAF / Rate Limit
                    └──────┬──────┘
                           │ edge network
                    ┌──────┴──────┐
                    │  FastAPI    │ 認証 / API / WebSocket
                    └──────┬──────┘
              ┌────────────┼────────────┐ app network
        ┌─────┴─────┐ ┌───┴───┐ ┌──────┴──────┐
        │  Celery    │ │ Beat  │ │   Ollama    │
        │  Worker    │ │       │ │  (Local LLM)│
        └─────┬─────┘ └───────┘ └─────────────┘
              │ data network (internal)
    ┌─────────┼──────────┬──────────┐
┌───┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐
│Postgres│ │ Redis │ │Qdrant │ │ MinIO │
└───────┘ └───────┘ └───────┘ └───────┘
```

## ネットワーク分離

| ネットワーク | 用途 | 参加コンテナ |
|---|---|---|
| edge | nginx ⇔ api | nginx, api |
| app | api ⇔ worker/ollama | api, worker, beat, ollama |
| data | データ層内部通信 | postgres, redis, qdrant, minio |
| monitoring | 監視系 | prometheus, grafana, loki, promtail |

`data` と `monitoring` は `internal: true` で外部公開不可。

## マルチテナント分離

| レイヤー | 分離方式 |
|---|---|
| PostgreSQL | Row Level Security (RLS) + `app.current_tenant_id` |
| Qdrant | Collection単位 (`tenant_{slug}`) |
| MinIO | Bucket単位 (`tenant-{uuid}`) |
| API | 全リクエストに tenant_id 強制注入 |

## RAGパイプライン

1. 質問受信 → テナント・権限スコープ取得
2. Embedding生成
3. Qdrant検索 (top_k, テナントフィルター)
4. リランキング
5. 機密度判定 → LLMプロバイダー自動選択
6. プロンプト構築 → LLM生成 (ストリーミング)
7. 応答 + 引用元返却
8. 監査ログ記録

## 機密度ベースLLMルーティング

| 機密度 | 利用可能LLM |
|---|---|
| public | 全プロバイダー |
| internal | 全プロバイダー |
| confidential | Ollama（ローカル）のみ |
| restricted | Ollama + 追加承認 |

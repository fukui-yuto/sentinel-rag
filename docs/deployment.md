# デプロイガイド

## 前提条件

- VM: 16 vCPU / 64GB RAM / 1TB NVMe SSD
- OS: Ubuntu 22.04 LTS (推奨)
- Docker Engine 24+ / Docker Compose v2
- 社内ネットワーク・DNS・SSO IdP 構築済み

## セットアップ

### 1. 環境変数の設定

```bash
cp .env.example .env
# 全てのパスワード・APIキーを変更
```

### 2. TLS証明書の配置

```bash
cp /path/to/server.crt config/nginx/tls/
cp /path/to/server.key config/nginx/tls/
```

### 3. サービス起動

```bash
# 本番環境（override.ymlを無効化）
docker compose -f docker-compose.yml up -d

# 監視スタックも起動
docker compose -f docker-compose.yml --profile monitoring up -d

# Keycloak（SSO IdP）も起動
docker compose -f docker-compose.yml --profile auth up -d
```

### 4. 初期確認

```bash
./scripts/health-check.sh
```

## バックアップ

```bash
# 手動実行
./scripts/backup.sh

# cron設定（毎日3:00）
echo "0 3 * * * /opt/sentinel-rag/scripts/backup.sh" | crontab -
```

## アップグレード

1. メンテナンス窓を告知
2. VMスナップショット取得
3. `docker compose pull`
4. `docker compose up -d`
5. `./scripts/health-check.sh`
6. 問題があればスナップショットからロールバック

## リソース割当

| サービス | CPU | Memory |
|---|---|---|
| nginx | 1 | 2GB |
| api | 6 | 12GB |
| worker | 4 | 16GB |
| beat | 0.5 | 1GB |
| postgres | 2 | 8GB |
| redis | 1 | 4GB |
| qdrant | 2 | 12GB |
| minio | 1 | 2GB |
| ollama | 4 | 8GB |

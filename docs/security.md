# セキュリティ

## 暗号化

| 領域 | 実装 |
|---|---|
| 通信 | TLS 1.3 (nginx) |
| データ保存 | LUKS (ディスク) + pgcrypto (カラム) |
| シークレット | Vault or pgcrypto暗号化保存 |
| バックアップ | AES-256暗号化 |

## 認証フロー

1. ユーザー → nginx → SSO IdP (SAML/OIDC) リダイレクト
2. IdPで認証 + MFA
3. IDトークン → API でJWT検証
4. セッション発行 (Redis, 8時間TTL)

## RBAC

| ロール | 権限 |
|---|---|
| system_admin | 全テナント管理、システム設定 |
| tenant_admin | 自テナントのユーザー・ドキュメント管理 |
| content_manager | ドキュメントCRUD |
| user | QA実行 + 自分のドキュメント管理 |
| auditor | 監査ログ閲覧専用 |
| read_only | QAのみ |

## DLP (Data Loss Prevention)

取り込み時に自動スキャン:
- マイナンバー (12桁)
- クレジットカード番号 (Luhnチェック)
- メールアドレス
- APIキー / パスワード / 秘密鍵
- AWS アクセスキー

検知結果に基づき自動で機密度ラベルを付与。

## 監査ログ

- SHA-256ハッシュチェーンで改ざん検知
- 全操作を記録 (認証, 認可, データアクセス, 変更, セキュリティ)
- 7年間保管
- SIEM連携 (syslog RFC 5424) 対応

## ネットワーク

- 外部接続はForward Proxy経由のみ
- 外部APIはホワイトリスト制
- データ層コンテナは内部ネットワーク (external access不可)
- Dockerデーモン TCP公開禁止

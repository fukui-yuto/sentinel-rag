# Claude Code 設定

このプロジェクトの主指示書は [AGENTS.md](AGENTS.md) を参照。
詳細な設計思想は [docs/requirements.md](docs/requirements.md) を参照。

## Claude Code 固有の注意事項
- サブエージェント定義は `.claude/agents/` 配下
- MCP 設定は `.mcp.json`（リポジトリルート）。`.claude/` の中に置くと認識されない
- Skill を追加する場合は `.claude/skills/` 配下に配置


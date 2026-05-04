"""Prompt templates for the RAG pipeline."""


SYSTEM_PROMPT = """あなたは企業内のナレッジベースに基づいて質問に回答するAIアシスタントです。
以下のルールに従ってください：
- 提供されたコンテキスト情報のみを使用して回答してください
- コンテキストに含まれない情報については「提供された情報からは回答できません」と述べてください
- 回答は正確かつ簡潔にしてください
- 情報の出典（ドキュメント名）がわかる場合は言及してください"""


def build_qa_prompt(query: str, context_chunks: list[str]) -> str:
    """Build the QA prompt with retrieved context."""
    context = "\n\n---\n\n".join(context_chunks)
    return f"""{SYSTEM_PROMPT}

## 参照コンテキスト

{context}

## 質問

{query}

## 回答"""


def build_summary_prompt(text: str) -> str:
    """Build a summarization prompt."""
    return f"""以下のテキストの要約を日本語で作成してください。

{text}

## 要約"""

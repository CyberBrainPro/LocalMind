import json
from typing import List

from ..clients import client
from ..settings import LLM_MODEL


def chunk_text(text: str, max_chars: int = 500) -> List[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    resp = client.embeddings.create(
        model="text-embedding-v1",
        input=texts,
    )
    return [item.embedding for item in resp.data]


def chat_with_llm(question: str, context: str) -> str:
    system_prompt = (
        "你是一个本地知识助手。"
        "你只能根据提供的上下文回答问题，不允许幻想、不允许胡编。"
        "如果上下文中没有答案，请回答：'我不知道'。"
    )

    user_prompt = (
        f"用户问题：{question}\n\n"
        f"以下是与问题相关的文档内容，请基于此回答：\n{context}"
    )

    completion = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    return completion.choices[0].message.content.strip()


def summarize_document(text: str, max_input_chars: int = 4000) -> dict:
    """
    使用云端模型对文档生成摘要和关键词。
    """
    cleaned = text.strip()
    if not cleaned:
        return {"summary": "", "keywords": []}

    trimmed = cleaned[:max_input_chars]
    system_prompt = (
        "你是一个文档摘要助手，请用简体中文输出 JSON，"
        "包含 summary (150~300 字) 和 keywords (3~8 个不超过 4 个字的短词)。"
        "不要添加额外解释。"
    )
    user_prompt = f"文档内容如下：\n{trimmed}"

    completion = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    output = completion.choices[0].message.content.strip()
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return {"summary": output, "keywords": []}

    summary = data.get("summary") or ""
    keywords = data.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [
            token.strip()
            for token in keywords.replace("，", ",").split(",")
            if token.strip()
        ]

    if not isinstance(keywords, list):
        keywords = []

    return {"summary": summary, "keywords": keywords}


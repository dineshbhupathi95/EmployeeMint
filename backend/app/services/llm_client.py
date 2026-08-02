"""OpenAI-compatible chat + embeddings client (works with OpenAI, Azure, Ollama, etc.)."""

from __future__ import annotations

import math
from typing import Any

from openai import AsyncOpenAI


def make_client(api_key: str, base_url: str) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key, base_url=base_url.rstrip("/"))


async def chat_completion(
    *,
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
) -> str:
    client = make_client(api_key, base_url)
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
    )
    content = resp.choices[0].message.content
    return (content or "").strip()


async def embed_texts(
    *,
    api_key: str,
    base_url: str,
    model: str,
    texts: list[str],
) -> list[list[float]]:
    if not texts:
        return []
    client = make_client(api_key, base_url)
    resp = await client.embeddings.create(model=model, input=texts)
    # Ensure order by index
    ordered = sorted(resp.data, key=lambda d: d.index)
    return [list(d.embedding) for d in ordered]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def tokenize(text: str) -> set[str]:
    return {t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if len(t) > 2}


def keyword_score(query: str, content: str) -> float:
    q = tokenize(query)
    c = tokenize(content)
    if not q or not c:
        return 0.0
    return len(q & c) / len(q)

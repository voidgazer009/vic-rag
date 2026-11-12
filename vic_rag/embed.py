"""Pluggable dense embedders. Dense retrieval is optional: BM25 alone works offline.

Choose with env vars (or `embedder:` in pack.yaml):
  VIC_RAG_EMBEDDER = none | openai | fastembed
  openai   -> any OpenAI-compatible /v1/embeddings endpoint (OpenAI, SiliconFlow, Ollama, vLLM, Jina...)
              VIC_RAG_EMBED_BASE_URL (default https://api.openai.com/v1)
              VIC_RAG_EMBED_API_KEY, VIC_RAG_EMBED_MODEL (default text-embedding-3-small)
  fastembed-> local ONNX model, VIC_RAG_EMBED_MODEL (default BAAI/bge-small-zh-v1.5); pip install fastembed
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Protocol

import math


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _unit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class OpenAICompatEmbedder:
    def __init__(self, model: str | None = None, base_url: str | None = None, api_key: str | None = None):
        self.model = model or os.getenv("VIC_RAG_EMBED_MODEL", "text-embedding-3-small")
        self.base_url = (base_url or os.getenv("VIC_RAG_EMBED_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("VIC_RAG_EMBED_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        self.name = f"openai:{self.model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 64):
            body = json.dumps({"model": self.model, "input": texts[i:i + 64]}).encode()
            req = urllib.request.Request(f"{self.base_url}/embeddings", data=body, headers={
                "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())["data"]
            out.extend(_unit(d["embedding"]) for d in sorted(data, key=lambda d: d["index"]))
        return out


class FastEmbedEmbedder:
    def __init__(self, model: str | None = None):
        from fastembed import TextEmbedding  # type: ignore
        self.model = model or os.getenv("VIC_RAG_EMBED_MODEL", "BAAI/bge-small-zh-v1.5")
        self._m = TextEmbedding(self.model)
        self.name = f"fastembed:{self.model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_unit(list(map(float, v))) for v in self._m.embed(texts)]


def get_embedder(kind: str | None = None) -> Embedder | None:
    kind = (kind or os.getenv("VIC_RAG_EMBEDDER", "none")).lower()
    if kind in ("", "none", "bm25"):
        return None
    if kind == "openai":
        return OpenAICompatEmbedder()
    if kind == "fastembed":
        return FastEmbedEmbedder()
    raise ValueError(f"Unknown embedder: {kind}")

"""Embedding providers.

A small interface with two implementations so the rest of the system never
cares where embeddings come from:

- LocalEmbeddingProvider  (default): fastembed / ONNX Runtime, no Azure, free.
- AzureEmbeddingProvider:           Azure OpenAI, enabled via EMBEDDING_PROVIDER=azure.

Swap providers by setting EMBEDDING_PROVIDER in .env — no other code changes.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from app.config import EMBEDDING_DIM, EMBEDDING_MODEL, EMBEDDING_PROVIDER


class EmbeddingProvider(ABC):
    name: str
    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors of length self.dim."""

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class LocalEmbeddingProvider(EmbeddingProvider):
    """fastembed (ONNX Runtime) — runs locally with no external API."""

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name)
        self.name = f"local:{model_name}"
        # Detect dimension from a probe embedding so callers never hardcode it.
        self.dim = len(next(iter(self._model.embed(["dimension probe"]))))

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() for vec in self._model.embed(texts)]


class AzureEmbeddingProvider(EmbeddingProvider):
    """Azure OpenAI embeddings — used when EMBEDDING_PROVIDER=azure."""

    def __init__(self):
        from openai import AzureOpenAI

        self._deployment = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]
        self._client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
        )
        self.name = f"azure:{self._deployment}"
        self.dim = EMBEDDING_DIM or 3072

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._deployment, input=texts)
        return [item.embedding for item in resp.data]


_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return a cached embedding provider based on EMBEDDING_PROVIDER."""
    global _provider
    if _provider is None:
        if EMBEDDING_PROVIDER == "azure":
            _provider = AzureEmbeddingProvider()
        else:
            _provider = LocalEmbeddingProvider()
    return _provider

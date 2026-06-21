"""Text embedding backends used for content-based recommendations.

Two backends are supported:

* ``sentence-transformers`` (default) - semantic embeddings via a transformer model.
* ``hash`` - a deterministic, fully-offline hashing vectorizer. Useful for tests
  and environments without network access / heavy ML dependencies.

Both produce L2-normalised vectors of ``settings.embedding_dim`` dimensions so the
``pgvector`` column dimensionality stays constant regardless of backend.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import numpy as np

from app.config import get_settings


class Embedder(Protocol):
    dim: int

    def encode(self, texts: list[str]) -> np.ndarray: ...


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class HashingEmbedder:
    """Deterministic, offline embeddings via scikit-learn's HashingVectorizer."""

    def __init__(self, dim: int) -> None:
        from sklearn.feature_extraction.text import HashingVectorizer

        self.dim = dim
        self._vectorizer = HashingVectorizer(
            n_features=dim,
            alternate_sign=False,
            norm=None,
            ngram_range=(1, 2),
        )

    def encode(self, texts: list[str]) -> np.ndarray:
        sparse = self._vectorizer.transform(texts)
        return _l2_normalize(sparse.toarray().astype(np.float32))


class SentenceTransformerEmbedder:
    """Semantic embeddings via the sentence-transformers library."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vectors, dtype=np.float32)


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embedder == "hash":
        return HashingEmbedder(dim=settings.embedding_dim)
    return SentenceTransformerEmbedder(model_name=settings.embedding_model)

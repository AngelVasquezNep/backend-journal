"""Explicit finite vector-space adapters; deterministic fixtures never prove real-provider quality."""

import hashlib
import math
import re

import tiktoken
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from taskify_knowledge.domain.errors import ApplicationError, DependencyUnavailable


def validate_vectors(vectors: object, expected: int) -> tuple[tuple[float, ...], ...]:
    """Require finite, ordered, nonzero 1536-dimensional vectors and the exact requested count."""
    if not isinstance(vectors, (list, tuple)) or len(vectors) != expected:
        raise DependencyUnavailable()
    validated: list[tuple[float, ...]] = []
    for vector in vectors:
        if (
            not isinstance(vector, (list, tuple))
            or len(vector) != 1536
            or any(type(value) not in (int, float) or not math.isfinite(value) for value in vector)
        ):
            raise DependencyUnavailable()
        converted = tuple(float(value) for value in vector)
        if not any(converted):
            raise DependencyUnavailable()
        validated.append(converted)
    return tuple(validated)


class DeterministicEmbedder:
    """Hash lexical fixture features into a separate pipeline space; no external/provider call occurs."""

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Return stable normalized 1536-dimensional test vectors, preserving input order."""
        result: list[list[float]] = []
        for text in texts:
            if not text.strip():
                raise ValueError("Embeddings require nonempty text.")
            vector = [0.0] * 1536
            words = re.findall(r"\w+", text.casefold()) or list(text)
            for word in words:
                index = (
                    int.from_bytes(hashlib.sha256(word.encode("utf-8")).digest()[:8], "big") % 1536
                )
                vector[index] += 1.0
            norm = math.sqrt(sum(value * value for value in vector))
            result.append([value / norm for value in vector])
        return validate_vectors(result, len(texts))


class OpenAIEmbedder:
    """Use explicit text-embedding-3-small/1536 with no SDK retries or silent model/vector fallback."""

    def __init__(self, api_key: str) -> None:
        """Configure the backend-only provider key; construction makes no paid availability call."""
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.client = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536,
            api_key=SecretStr(api_key),
            max_retries=0,
            timeout=10,
            chunk_size=32,
            check_embedding_ctx_length=False,
        )

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Embed <=32 chunks/25,600 tokens per request and reject out-of-context input explicitly."""
        output: list[tuple[float, ...]] = []
        batch: list[str] = []
        tokens = 0
        for text in texts:
            count = len(self.encoding.encode(text, disallowed_special=()))
            if not text.strip() or not 1 <= count <= 8191:
                raise ApplicationError(
                    "validation_failed", "Use shorter nonempty text for embedding.", 422
                )
            if batch and (len(batch) >= 32 or tokens + count > 25_600):
                output.extend(self.send(batch))
                batch, tokens = [], 0
            batch.append(text)
            tokens += count
        if batch:
            output.extend(self.send(batch))
        return tuple(output)

    def send(self, texts: list[str]) -> tuple[tuple[float, ...], ...]:
        """Perform one bounded provider request; private provider diagnostics never leave this adapter."""
        try:
            vectors = self.client.embed_documents(texts)
        except Exception:
            raise DependencyUnavailable() from None
        return validate_vectors(vectors, len(texts))

"""Dependency-free text embedding.

Hashed bag of character bigrams. Crude but effective for short Chinese/English
trading notes, and it keeps the default install free of model downloads.
Swap in a real embedding model via FUPAN_EMBEDDER=sentence-transformers later
(roadmap) — the store only sees vectors, so the upgrade is drop-in.
"""

from __future__ import annotations

import hashlib
import math

DIM = 256


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    t = "".join(text.lower().split())
    if not t:
        return vec
    grams = [t[i : i + 2] for i in range(len(t) - 1)] or [t]
    for g in grams:
        h = int.from_bytes(hashlib.md5(g.encode("utf-8")).digest()[:4], "little")
        idx = h % DIM
        sign = 1.0 if (h >> 31) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))

"""Okapi BM25, pure Python, serialisable."""
from __future__ import annotations

import math
from collections import Counter


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tfs: list[dict[str, int]] = []
        self.lens: list[int] = []
        self.df: Counter = Counter()

    def fit(self, docs: list[list[str]]) -> "BM25":
        self.tfs = [dict(Counter(d)) for d in docs]
        self.lens = [len(d) for d in docs]
        self.df = Counter(t for tf in self.tfs for t in tf)
        return self

    @property
    def avgdl(self) -> float:
        return (sum(self.lens) / len(self.lens)) if self.lens else 0.0

    def idf(self, t: str) -> float:
        n, df = len(self.tfs), self.df.get(t, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def scores(self, query: list[str]) -> list[float]:
        avg = self.avgdl or 1.0
        q = Counter(query)
        out = []
        for tf, dl in zip(self.tfs, self.lens):
            s = 0.0
            for t, qn in q.items():
                f = tf.get(t)
                if f:
                    s += self.idf(t) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / avg))
            out.append(s)
        return out

    def to_dict(self) -> dict:
        return {"k1": self.k1, "b": self.b, "tfs": self.tfs, "lens": self.lens}

    @classmethod
    def from_dict(cls, d: dict) -> "BM25":
        m = cls(d["k1"], d["b"])
        m.tfs, m.lens = d["tfs"], d["lens"]
        m.df = Counter(t for tf in m.tfs for t in tf)
        return m

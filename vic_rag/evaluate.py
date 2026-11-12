"""Retrieval evaluation. eval.jsonl lines: {"q": "...", "expect": ["substring of source or text", ...]}
A hit counts when any expected string appears in the hit's source path, title, section or text."""
from __future__ import annotations

import json

from .kb import KnowledgeBase


def evaluate(kb: KnowledgeBase, k: int = 5) -> dict:
    rows = [json.loads(l) for l in kb.pack.eval_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    hit1 = hitk = rr = 0.0
    fails = []
    for row in rows:
        hits = kb.search(row["q"], k=k)
        rank = next((h.rank for h in hits if any(e in f"{h.source} {h.title} {h.section} {h.text}" for e in row["expect"])), None)
        if rank:
            hitk += 1
            rr += 1 / rank
            hit1 += rank == 1
        else:
            fails.append(row["q"])
    n = len(rows) or 1
    return {"kb": kb.pack.id, "questions": len(rows), "hit@1": round(hit1 / n, 3), f"hit@{k}": round(hitk / n, 3),
            "mrr": round(rr / n, 3), "failed": fails}

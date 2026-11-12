"""KnowledgeBase: build, persist and search one industry pack plus the user's own docs."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .bm25 import BM25
from .chunker import Chunk, chunk_document
from .embed import get_embedder
from .loaders import SUPPORTED, load_dir
from .pack import Pack, load_pack
from .text import normalize, tokenize

INDEX_VERSION = 1


def data_home() -> Path:
    return Path(os.getenv("VIC_RAG_HOME", Path.home() / ".vic-rag"))


@dataclass
class SearchHit:
    rank: int
    score: float
    chunk_id: str
    title: str
    section: str
    source: str
    text: str
    meta: dict

    def citation(self) -> str:
        return f"{self.title}" + (f" › {self.section}" if self.section else "") + f" ({self.source})"


class KnowledgeBase:
    def __init__(self, pack: Pack | str, home: Path | None = None):
        self.pack = load_pack(pack) if isinstance(pack, (str, Path)) else pack
        self.home = (home or data_home()) / self.pack.id
        self.user_docs = self.home / "docs"
        self.index_dir = self.home / "index"
        self.chunks: list[Chunk] = []
        self.bm25: BM25 | None = None
        self.vectors: list[list[float]] | None = None
        self.embedder_name: str | None = None

    # ---------- build / load ----------
    def _source_dirs(self) -> list[tuple[str, Path]]:
        return [("pack", self.pack.docs_dir), ("user", self.user_docs)]

    def fingerprint(self) -> str:
        h = hashlib.sha1()
        for tag, d in self._source_dirs():
            if d.exists():
                for p in sorted(d.rglob("*")):
                    if p.is_file() and p.suffix.lower() in SUPPORTED:
                        st = p.stat()
                        h.update(f"{tag}:{p.relative_to(d)}:{st.st_size}:{int(st.st_mtime)}".encode())
        h.update((self.pack.embedder or os.getenv("VIC_RAG_EMBEDDER", "none")).encode())
        h.update(f"{self.pack.max_units}:{self.pack.overlap_units}:{INDEX_VERSION}".encode())
        return h.hexdigest()

    def build(self) -> dict:
        t0 = time.time()
        chunks: list[Chunk] = []
        for tag, d in self._source_dirs():
            if not d.exists():
                continue
            for doc in load_dir(d):
                doc.doc_id = doc.source = f"{tag}/{doc.source}"
                chunks.extend(chunk_document(doc, self.pack.max_units, self.pack.overlap_units))
        self.chunks = chunks
        self.bm25 = BM25().fit([tokenize(c.index_text) for c in chunks])
        emb = get_embedder(self.pack.embedder)
        self.vectors = emb.embed([c.index_text for c in chunks]) if (emb and chunks) else None
        self.embedder_name = emb.name if emb else None
        self._save()
        return {"kb": self.pack.id, "chunks": len(chunks), "docs": len({c.doc_id for c in chunks}),
                "embedder": self.embedder_name or "bm25-only", "seconds": round(time.time() - t0, 2)}

    def _save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": INDEX_VERSION, "fingerprint": self.fingerprint(), "embedder": self.embedder_name,
                   "chunks": [asdict(c) for c in self.chunks], "bm25": self.bm25.to_dict() if self.bm25 else None,
                   "vectors": self.vectors}
        tmp = self.index_dir / "index.json.tmp"
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.index_dir / "index.json")

    def load(self, auto_build: bool = True) -> "KnowledgeBase":
        f = self.index_dir / "index.json"
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("version") == INDEX_VERSION and data.get("fingerprint") == self.fingerprint():
                self.chunks = [Chunk(**c) for c in data["chunks"]]
                self.bm25 = BM25.from_dict(data["bm25"]) if data["bm25"] else None
                self.vectors, self.embedder_name = data.get("vectors"), data.get("embedder")
                return self
        if not auto_build:
            raise FileNotFoundError(f"No up-to-date index for {self.pack.id}; run build")
        self.build()
        return self

    # ---------- user documents ----------
    def add_document(self, title: str, text: str, tags: list[str] | None = None) -> str:
        self.user_docs.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", title).strip("-")[:60] or "doc"
        path = self.user_docs / f"{slug}.md"
        i = 2
        while path.exists():
            path, i = self.user_docs / f"{slug}-{i}.md", i + 1
        fm = {"title": title, "tags": tags or [], "added": time.strftime("%Y-%m-%d")}
        import yaml
        path.write_text(f"---\n{yaml.safe_dump(fm, allow_unicode=True).strip()}\n---\n# {title}\n\n{text.strip()}\n",
                        encoding="utf-8")
        self.build()
        return f"user/{path.name}"

    def import_path(self, src: str | Path) -> int:
        import shutil
        src = Path(src)
        self.user_docs.mkdir(parents=True, exist_ok=True)
        files = [src] if src.is_file() else [p for p in src.rglob("*") if p.is_file()]
        n = 0
        for p in files:
            if p.suffix.lower() in SUPPORTED:
                shutil.copy2(p, self.user_docs / p.name)
                n += 1
        self.build()
        return n

    # ---------- search ----------
    def expand_query(self, q: str) -> str:
        nq, extra = normalize(q), []
        for term, aliases in self.pack.synonyms.items():
            group = [term, *aliases]
            if any(normalize(g) in nq for g in group):
                extra.extend(g for g in group if normalize(g) not in nq)
        return q + (" " + " ".join(extra) if extra else "")

    def search(self, query: str, k: int = 5, tags: list[str] | None = None, source: str | None = None,
               rrf_k: int = 60) -> list[SearchHit]:
        if self.bm25 is None:
            self.load()
        if not self.chunks:
            return []
        eq = self.expand_query(query)
        lex = self.bm25.scores(tokenize(eq))
        allowed = [i for i, c in enumerate(self.chunks) if self._match(c, tags, source)]
        fused: dict[int, float] = {}
        lex_rank = sorted((i for i in allowed if lex[i] > 0), key=lambda i: -lex[i])
        for r, i in enumerate(lex_rank):
            fused[i] = fused.get(i, 0) + 1 / (rrf_k + r + 1)
        if self.vectors:
            emb = get_embedder(self.pack.embedder)
            qv = emb.embed([eq])[0] if emb else None
            if qv:
                dense = {i: sum(a * b for a, b in zip(qv, self.vectors[i])) for i in allowed}
                for r, i in enumerate(sorted(dense, key=lambda i: -dense[i])[: max(50, k * 10)]):
                    fused[i] = fused.get(i, 0) + 1 / (rrf_k + r + 1)
        ranked = sorted(fused, key=lambda i: -fused[i])
        hits, seen = [], set()
        for i in ranked:
            c = self.chunks[i]
            key = (c.doc_id, c.section)
            if key in seen and len(ranked) > k:
                continue
            seen.add(key)
            hits.append(SearchHit(len(hits) + 1, round(fused[i], 5), c.chunk_id, c.title, c.section,
                                  c.source, c.text, c.meta))
            if len(hits) >= k:
                break
        return hits

    @staticmethod
    def _match(c: Chunk, tags: list[str] | None, source: str | None) -> bool:
        if source and source not in c.source:
            return False
        if tags:
            ct = {str(t).lower() for t in (c.meta.get("tags") or [])}
            if not ct & {t.lower() for t in tags}:
                return False
        return True

    def context(self, question: str, k: int = 5, **kw) -> dict:
        hits = self.search(question, k=k, **kw)
        ctx = "\n\n".join(f"[{h.rank}] {h.citation()}\n{h.text}" for h in hits)
        return {"question": question, "context": ctx,
                "prompt": self.pack.answer_prompt.format(context=ctx or "（无相关资料）", question=question),
                "sources": [{"ref": h.rank, "citation": h.citation(), "chunk_id": h.chunk_id} for h in hits]}

    def stats(self) -> dict:
        if self.bm25 is None:
            self.load()
        return {"id": self.pack.id, "name": self.pack.name, "description": self.pack.description,
                "chunks": len(self.chunks), "docs": len({c.doc_id for c in self.chunks}),
                "user_docs_dir": str(self.user_docs), "retrieval": "hybrid" if self.vectors else "bm25"}

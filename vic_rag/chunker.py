"""Structure-aware chunking: split on markdown headings first, then pack
paragraphs up to `max_units` with `overlap_units` of carry-over. Every chunk
remembers its heading path, which is prepended for retrieval (contextual chunking)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .loaders import Document
from .text import count_units


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    section: str
    text: str
    source: str
    meta: dict = field(default_factory=dict)

    @property
    def index_text(self) -> str:
        return f"{self.title} > {self.section}\n{self.text}" if self.section else f"{self.title}\n{self.text}"


_HEAD = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)


def _sections(text: str) -> list[tuple[str, str]]:
    out, path = [], []
    pos, cur = 0, ""
    for m in _HEAD.finditer(text):
        body = text[pos:m.start()].strip()
        if body:
            out.append((cur, body))
        lvl = len(m.group(1))
        path = path[: lvl - 1] + [m.group(2)]
        path = [p for p in path if p]
        cur = " > ".join(path[1:] if len(path) > 1 else path)
        pos = m.end()
    tail = text[pos:].strip()
    if tail:
        out.append((cur, tail))
    return out


def _split_long(par: str, max_units: int) -> list[str]:
    if count_units(par) <= max_units:
        return [par]
    sents = re.split(r"(?<=[。！？；.!?;])\s*", par)
    parts, buf = [], ""
    for s in sents:
        if buf and count_units(buf + s) > max_units:
            parts.append(buf)
            buf = ""
        buf += s
    if buf:
        parts.append(buf)
    return parts


def chunk_document(doc: Document, max_units: int = 400, overlap_units: int = 60) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section, body in _sections(doc.text) or [("", doc.text)]:
        pars = []
        for block in re.split(r"\n\s*\n", body):
            pars.extend(_split_long(block.strip(), max_units))
        buf: list[str] = []
        for par in [p for p in pars if p]:
            if buf and count_units("\n".join(buf + [par])) > max_units:
                chunks.append(_mk(doc, section, "\n\n".join(buf), len(chunks)))
                carry, units = [], 0
                for prev in reversed(buf):
                    units += count_units(prev)
                    if units > overlap_units:
                        break
                    carry.insert(0, prev)
                buf = carry
            buf.append(par)
        if buf:
            chunks.append(_mk(doc, section, "\n\n".join(buf), len(chunks)))
    return chunks


def _mk(doc: Document, section: str, text: str, i: int) -> Chunk:
    return Chunk(f"{doc.doc_id}#{i}", doc.doc_id, doc.title, section, text, doc.source, dict(doc.meta))

"""Turn files into plain text. Markdown/txt/html/json/csv work out of the box;
PDF and DOCX are supported when `pypdf` / `python-docx` are installed."""
from __future__ import annotations

import csv
import html
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED = {".md", ".markdown", ".txt", ".html", ".htm", ".json", ".jsonl", ".csv", ".pdf", ".docx"}


@dataclass
class Document:
    doc_id: str
    title: str
    text: str
    source: str
    meta: dict = field(default_factory=dict)


_FRONT = re.compile(r"^---\n(.*?)\n---\n", re.S)


def _front_matter(text: str) -> tuple[dict, str]:
    m = _FRONT.match(text)
    if not m:
        return {}, text
    try:
        import yaml
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), text[m.end():]


def _html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", raw)
    raw = re.sub(r"(?i)<(br|/p|/div|/li|/tr|/h[1-6])[^>]*>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"[ \t]+", " ", html.unescape(raw))


def load_file(path: str | Path, root: str | Path | None = None) -> Document:
    p = Path(path)
    ext = p.suffix.lower()
    rel = str(p.relative_to(root)) if root else p.name
    meta: dict = {}
    if ext in {".md", ".markdown", ".txt"}:
        meta, text = _front_matter(p.read_text(encoding="utf-8"))
    elif ext in {".html", ".htm"}:
        text = _html_to_text(p.read_text(encoding="utf-8", errors="ignore"))
    elif ext == ".json":
        text = json.dumps(json.loads(p.read_text(encoding="utf-8")), ensure_ascii=False, indent=1)
    elif ext == ".jsonl":
        text = "\n".join(p.read_text(encoding="utf-8").splitlines())
    elif ext == ".csv":
        rows = list(csv.reader(io.StringIO(p.read_text(encoding="utf-8-sig"))))
        head = rows[0] if rows else []
        text = "\n".join("; ".join(f"{h}: {v}" for h, v in zip(head, r)) for r in rows[1:])
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("PDF support needs: pip install pypdf") from e
        text = "\n\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    elif ext == ".docx":
        try:
            import docx
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("DOCX support needs: pip install python-docx") from e
        d = docx.Document(str(p))
        lines = []
        for para in d.paragraphs:
            style = (para.style.name or "").lower()
            if style.startswith("heading"):
                lvl = "".join(ch for ch in style if ch.isdigit()) or "1"
                lines.append("#" * int(lvl) + " " + para.text)
            else:
                lines.append(para.text)
        text = "\n".join(lines)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    title = str(meta.get("title") or _first_heading(text) or p.stem)
    return Document(doc_id=rel, title=title, text=text.strip(), source=rel, meta=meta)


def _first_heading(text: str) -> str | None:
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else None


def load_dir(folder: str | Path) -> list[Document]:
    folder = Path(folder)
    docs = []
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.suffix.lower() in SUPPORTED and not p.name.startswith("."):
            docs.append(load_file(p, folder))
    return docs

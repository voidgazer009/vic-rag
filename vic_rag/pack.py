"""Industry knowledge packs: a folder with pack.yaml, docs/ and eval.jsonl.

pack.yaml keys:
  id, name, description, language
  chunk: {max_units, overlap_units}
  synonyms: {term: [aliases...]}      # query expansion, industry jargon
  answer_prompt: |                     # prompt template, {context} and {question}
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_PROMPT = (
    "你是专业顾问。只根据下面的资料回答问题；资料没有的内容请直接说“资料中没有”，不要编造。"
    "每个关键结论后用 [编号] 标注来源。\n\n资料：\n{context}\n\n问题：{question}\n回答："
)


@dataclass
class Pack:
    id: str
    name: str
    root: Path
    description: str = ""
    language: str = "zh"
    max_units: int = 400
    overlap_units: int = 60
    synonyms: dict[str, list[str]] = field(default_factory=dict)
    answer_prompt: str = DEFAULT_PROMPT
    embedder: str | None = None

    @property
    def docs_dir(self) -> Path:
        return self.root / "docs"

    @property
    def eval_file(self) -> Path:
        return self.root / "eval.jsonl"


def packs_root() -> Path:
    env = os.getenv("VIC_RAG_PACKS")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "packs"


def load_pack(id_or_path: str | Path) -> Pack:
    p = Path(id_or_path)
    if not (p / "pack.yaml").exists():
        p = packs_root() / str(id_or_path)
    cfg = yaml.safe_load((p / "pack.yaml").read_text(encoding="utf-8")) or {}
    ch = cfg.get("chunk") or {}
    return Pack(
        id=cfg.get("id", p.name), name=cfg.get("name", p.name), root=p,
        description=cfg.get("description", ""), language=cfg.get("language", "zh"),
        max_units=int(ch.get("max_units", 400)), overlap_units=int(ch.get("overlap_units", 60)),
        synonyms={k: list(v) for k, v in (cfg.get("synonyms") or {}).items()},
        answer_prompt=cfg.get("answer_prompt") or DEFAULT_PROMPT,
        embedder=cfg.get("embedder"),
    )


def list_packs() -> list[Pack]:
    root = packs_root()
    return [load_pack(d) for d in sorted(root.iterdir()) if (d / "pack.yaml").exists()] if root.exists() else []

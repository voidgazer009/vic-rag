"""vic-rag command line.

  vic-rag list                         # knowledge bases
  vic-rag build [KB|all]               # (re)build indexes
  vic-rag search KB "问题" [-k 5]
  vic-rag context KB "问题"             # prompt-ready context with citations
  vic-rag add KB path/to/file_or_dir   # import your own documents
  vic-rag eval [KB|all]
  vic-rag mcp                          # MCP server over stdio
  vic-rag http [--port 8765]           # JSON HTTP API
"""
from __future__ import annotations

import argparse
import json
import sys

from .evaluate import evaluate
from .kb import KnowledgeBase
from .pack import list_packs


def _kbs(name: str) -> list[KnowledgeBase]:
    return [KnowledgeBase(p) for p in list_packs()] if name == "all" else [KnowledgeBase(name)]


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vic-rag", description="Universal RAG engine with industry packs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    b = sub.add_parser("build"); b.add_argument("kb", nargs="?", default="all")
    s = sub.add_parser("search"); s.add_argument("kb"); s.add_argument("query"); s.add_argument("-k", type=int, default=5)
    s.add_argument("--tag", action="append")
    c = sub.add_parser("context"); c.add_argument("kb"); c.add_argument("query"); c.add_argument("-k", type=int, default=5)
    a = sub.add_parser("add"); a.add_argument("kb"); a.add_argument("path")
    e = sub.add_parser("eval"); e.add_argument("kb", nargs="?", default="all"); e.add_argument("-k", type=int, default=5)
    sub.add_parser("mcp")
    h = sub.add_parser("http"); h.add_argument("--host", default="127.0.0.1"); h.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)

    if args.cmd == "list":
        _print([{"id": p.id, "name": p.name, "description": p.description} for p in list_packs()])
    elif args.cmd == "build":
        _print([kb.build() for kb in _kbs(args.kb)])
    elif args.cmd == "search":
        kb = KnowledgeBase(args.kb).load()
        for h in kb.search(args.query, k=args.k, tags=args.tag):
            print(f"[{h.rank}] {h.score:.4f}  {h.citation()}\n{h.text[:300]}\n")
    elif args.cmd == "context":
        print(KnowledgeBase(args.kb).load().context(args.query, k=args.k)["prompt"])
    elif args.cmd == "add":
        n = KnowledgeBase(args.kb).import_path(args.path)
        print(f"imported {n} file(s) into {args.kb}")
    elif args.cmd == "eval":
        res = [evaluate(kb.load(), k=args.k) for kb in _kbs(args.kb)]
        _print(res)
        return 0 if all(r[f"hit@{args.k}"] >= 0.8 for r in res) else 1
    elif args.cmd == "mcp":
        from .mcp_server import main as mcp_main
        mcp_main()
    elif args.cmd == "http":
        from .http_api import serve
        serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())

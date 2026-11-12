"""Minimal JSON HTTP API (stdlib only) for GPTs Actions, Dify, n8n, Make, Coze...

GET  /kbs
POST /search   {"kb": "trade", "query": "...", "k": 5}
POST /context  {"kb": "trade", "question": "...", "k": 5}
Optional auth: set VIC_RAG_API_TOKEN and send "Authorization: Bearer <token>".
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .kb import KnowledgeBase
from .pack import list_packs

_cache: dict[str, KnowledgeBase] = {}


def _kb(kb_id: str) -> KnowledgeBase:
    if kb_id not in _cache:
        _cache[kb_id] = KnowledgeBase(kb_id).load()
    return _cache[kb_id]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authed(self) -> bool:
        tok = os.getenv("VIC_RAG_API_TOKEN")
        return not tok or self.headers.get("Authorization") == f"Bearer {tok}"

    def do_GET(self):  # noqa: N802
        if not self._authed():
            return self._send(401, {"error": "unauthorized"})
        if self.path.rstrip("/") == "/kbs":
            return self._send(200, [{"id": p.id, "name": p.name, "description": p.description} for p in list_packs()])
        self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if not self._authed():
            return self._send(401, {"error": "unauthorized"})
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            kb = _kb(req["kb"])
            if self.path.rstrip("/") == "/search":
                hits = kb.search(req["query"], k=int(req.get("k", 5)), tags=req.get("tags"))
                return self._send(200, [{"ref": h.rank, "citation": h.citation(), "text": h.text} for h in hits])
            if self.path.rstrip("/") == "/context":
                return self._send(200, kb.context(req["question"], k=int(req.get("k", 5))))
            self._send(404, {"error": "not found"})
        except (KeyError, ValueError, FileNotFoundError) as e:
            self._send(400, {"error": str(e)})

    def log_message(self, *a):
        pass


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    print(f"vic-rag HTTP API on http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()

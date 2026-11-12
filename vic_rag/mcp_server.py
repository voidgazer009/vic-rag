"""MCP server: plug every knowledge base into Claude Desktop / Claude Code / Cursor /
any MCP-capable agent. Works with the MCP Python SDK v1 (FastMCP) and v2 (MCPServer)."""
from __future__ import annotations

from .kb import KnowledgeBase
from .pack import list_packs

try:  # MCP SDK 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # MCP SDK 1.x
    from mcp.server.fastmcp import FastMCP as _Server

server = _Server("vic-rag", instructions=(
    "Vic RAG knowledge bases (foreign trade, international logistics, AI one-person company, "
    "global social media, plus any user docs). Call list_knowledge_bases first, then search or "
    "get_context. Always cite sources by their [n] reference."))

_cache: dict[str, KnowledgeBase] = {}


def _kb(kb_id: str) -> KnowledgeBase:
    if kb_id not in _cache:
        _cache[kb_id] = KnowledgeBase(kb_id).load()
    return _cache[kb_id]


@server.tool()
def list_knowledge_bases() -> list[dict]:
    """List available knowledge bases with id, name and description."""
    return [{"id": p.id, "name": p.name, "description": p.description} for p in list_packs()]


@server.tool()
def search(kb: str, query: str, k: int = 5, tags: list[str] | None = None) -> list[dict]:
    """Hybrid search one knowledge base. Returns ranked passages with citations.
    kb: knowledge base id (trade, logistics, opc, social). query: natural language, Chinese or English."""
    return [{"ref": h.rank, "score": h.score, "citation": h.citation(), "text": h.text}
            for h in _kb(kb).search(query, k=k, tags=tags)]


@server.tool()
def get_context(kb: str, question: str, k: int = 5) -> dict:
    """Return prompt-ready numbered context plus a grounded answer prompt and source list."""
    return _kb(kb).context(question, k=k)


@server.tool()
def add_document(kb: str, title: str, text: str, tags: list[str] | None = None) -> dict:
    """Add the user's own document (markdown/plain text) to a knowledge base and re-index it."""
    path = _kb(kb).add_document(title, text, tags)
    return {"added": path, "stats": _kb(kb).stats()}


@server.tool()
def kb_stats(kb: str) -> dict:
    """Size and retrieval mode of a knowledge base."""
    return _kb(kb).stats()


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()

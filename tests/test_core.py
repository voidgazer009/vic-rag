import json
import threading
import urllib.request

import pytest

from vic_rag import KnowledgeBase, list_packs
from vic_rag.chunker import chunk_document
from vic_rag.evaluate import evaluate
from vic_rag.loaders import Document
from vic_rag.text import tokenize


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("VIC_RAG_HOME", str(tmp_path))
    monkeypatch.setenv("VIC_RAG_EMBEDDER", "none")


def test_tokenize_mixed():
    toks = tokenize("FOB 离岸价 40HQ")
    assert "fob" in toks and "离岸" in toks and "40hq" in toks


def test_chunker_keeps_sections():
    doc = Document("d.md", "T", "# T\n## A\n" + "甲乙丙丁。" * 200 + "\n## B\nshort", "d.md")
    chunks = chunk_document(doc, max_units=300, overlap_units=40)
    assert len(chunks) >= 3
    assert {c.section for c in chunks} == {"A", "B"}


def test_four_packs_exist():
    assert {p.id for p in list_packs()} >= {"trade", "logistics", "opc", "social"}


@pytest.mark.parametrize("kb_id", ["trade", "logistics", "opc", "social"])
def test_retrieval_quality(kb_id):
    res = evaluate(KnowledgeBase(kb_id).load(), k=5)
    assert res["hit@5"] >= 0.9, res
    assert res["mrr"] >= 0.8, res


def test_synonym_expansion():
    kb = KnowledgeBase("trade").load()
    assert "信用证" in kb.expand_query("L/C 交单期")


def test_add_user_document_and_search():
    kb = KnowledgeBase("trade").load()
    kb.add_document("我司硅胶厨具报价表", "硅胶铲 SKU-SP01 FOB 宁波 0.85 美元/个，MOQ 3000 个。", tags=["price"])
    hits = kb.search("硅胶铲 MOQ", k=3)
    assert hits and hits[0].source.startswith("user/")
    assert kb.search("硅胶铲", tags=["price"])[0].source.startswith("user/")


def test_context_has_citations():
    ctx = KnowledgeBase("logistics").load().context("空运体积重怎么算", k=3)
    assert "[1]" in ctx["context"] and ctx["sources"] and "6000" in ctx["context"]


def test_index_reused_when_unchanged():
    kb = KnowledgeBase("social")
    kb.build()
    kb2 = KnowledgeBase("social").load(auto_build=False)
    assert len(kb2.chunks) == len(kb.chunks)


def test_http_api():
    from http.server import ThreadingHTTPServer
    from vic_rag.http_api import Handler
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    req = urllib.request.Request(f"http://127.0.0.1:{port}/search",
                                 data=json.dumps({"kb": "opc", "query": "LTV 怎么算", "k": 2}).encode(),
                                 headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    data = json.loads(opener.open(req).read())
    srv.shutdown()
    assert len(data) == 2 and "citation" in data[0]


def test_mcp_tools():
    mcp = pytest.importorskip("mcp")
    import asyncio
    from vic_rag.mcp_server import server
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert {"list_knowledge_bases", "search", "get_context", "add_document", "kb_stats"} <= names

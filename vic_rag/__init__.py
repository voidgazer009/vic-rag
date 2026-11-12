"""Vic RAG: a universal, model-agnostic RAG engine with industry knowledge packs."""
from .kb import KnowledgeBase, SearchHit
from .pack import Pack, load_pack, list_packs

__all__ = ["KnowledgeBase", "SearchHit", "Pack", "load_pack", "list_packs"]
__version__ = "0.1.0"

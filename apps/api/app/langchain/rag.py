"""Local keyword-based document retriever (no vector DB)."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_loaded_docs: list = []
_docs_loaded = False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_rag_documents() -> list:
    """Load markdown docs via LangChain TextLoader at startup."""
    global _loaded_docs, _docs_loaded
    if _docs_loaded:
        return _loaded_docs

    try:
        from langchain_community.document_loaders import TextLoader
    except ImportError:
        logger.warning("langchain-community not available; RAG docs empty")
        _docs_loaded = True
        return _loaded_docs

    root = _repo_root()
    paths: list[Path] = []
    for pattern_dir in ("docs/safety", "docs/architecture", "docs/runbooks"):
        dir_path = root / pattern_dir
        if dir_path.is_dir():
            paths.extend(sorted(dir_path.glob("*.md")))
    ctx = root / "PROJECT_CONTEXT.md"
    if ctx.is_file():
        paths.append(ctx)

    for path in paths:
        try:
            loader = TextLoader(str(path), encoding="utf-8")
            docs = loader.load()
            for doc in docs:
                doc.metadata["source_path"] = str(path.relative_to(root))
            _loaded_docs.extend(docs)
        except Exception as exc:
            logger.warning("Failed to load RAG doc %s: %s", path, exc)

    _docs_loaded = True
    logger.info("Loaded %d RAG documents for Phase 3", len(_loaded_docs))
    return _loaded_docs


def get_rag_docs() -> list:
    """Return loaded documents (lazy load on first call)."""
    if not _docs_loaded:
        load_rag_documents()
    return _loaded_docs

#!/usr/bin/env python3
"""
Retrieval-часть RAG: кодирование запроса той же моделью и поиск в Chroma.

Модель и коллекция загружаются один раз (ленивые синглтоны), чтобы в REPL
не платить за загрузку на каждый вопрос.
"""

import chromadb
from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION = "knowledge_base"
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000

_model: SentenceTransformer | None = None
_collection = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        _collection = client.get_collection(COLLECTION)
    return _collection


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Вернуть top-k чанков по запросу"""
    model = _get_model()
    col = _get_collection()
    qemb = model.encode([query], normalize_embeddings=True).tolist()
    res = col.query(
        query_embeddings=qemb,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    out = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        out.append({"text": doc, "metadata": meta, "similarity": 1 - dist})
    return out


def retrieve_expanded(query: str, k_search: int = 4, before: int = 1, after: int = 2) -> list[dict]:
    """Поиск с расширением контекста.

    1. Находим top чанков по сходству
    2. Берем чанк с наибольшей длиной текста
    3. Берем предыдущий и следующий соседний чанки из того же файла
    4. Возвращаем окно, упорядоченное по chunk_index.
    """
    hits = retrieve(query, k_search)
    if not hits:
        return []

    anchor = max(hits, key=lambda c: len(c["text"]))
    fn = anchor["metadata"].get("filename")
    idx = anchor["metadata"].get("chunk_index")
    if fn is None or idx is None:
        return [anchor]

    wanted = [i for i in range(idx - before, idx + after + 1) if i >= 0]
    col = _get_collection()
    res = col.get(
        where={"$and": [{"filename": fn}, {"chunk_index": {"$in": wanted}}]},
        include=["documents", "metadatas"],
    )

    sim_by_idx = {
        h["metadata"].get("chunk_index"): h["similarity"]
        for h in hits if h["metadata"].get("filename") == fn
    }
    items = [
        {"text": doc, "metadata": meta, "similarity": sim_by_idx.get(meta.get("chunk_index"))}
        for doc, meta in zip(res["documents"], res["metadatas"])
    ]
    items.sort(key=lambda c: c["metadata"].get("chunk_index", 0))
    return items

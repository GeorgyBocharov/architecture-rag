#!/usr/bin/env python3
"""
Тестовый поиск по векторному индексу Chroma (CLI).

Тонкая обёртка над scripts/rag/retriever.py: вся логика поиска (кодирование
запроса + запрос в Chroma) живёт в retriever.retrieve(); 

Запуск:
    .venv/bin/python3 scripts/search/search.py "кто лучший друг джависта?"        # top-4 по умолчанию
    .venv/bin/python3 scripts/search/search.py "кто лучший друг джависта?" -k 6   # 6 кандидатов
    .venv/bin/python3 scripts/search/search.py                                  # прогон демо-запросов
"""

import argparse
import sys
import textwrap
from pathlib import Path

# retriever.py лежит в ../rag/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))
import retriever

TOP_K = 4

DEMO_QUERIES = [
    "что находится на рабочем месте архитектора?",
    "о чём серия про флаг?",
]


def search(query: str, k: int = TOP_K) -> None:
    print(f"\n{'='*80}\n🔎 ЗАПРОС: {query}\n{'='*80}")
    for rank, ch in enumerate(retriever.retrieve(query, k), 1):
        m = ch["metadata"]
        loc = m.get("section") or "—"
        print(f"\n[{rank}] sim={ch['similarity']:.3f}  «{m.get('title')}» / {loc}")
        print(f"    источник: {m.get('source')}  (chunk {m.get('chunk_index')}, тип {m.get('doc_type')})\n")
        snippet = textwrap.shorten(ch["text"].replace("\n", " "), width=220, placeholder=" …")
        print(f"Фрагмент ответа:    {snippet}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Поиск по векторному индексу Chroma")
    ap.add_argument("query", nargs="*", help="вопрос (можно без кавычек); если пусто — демо-запросы")
    ap.add_argument("-k", "--top-k", type=int, default=TOP_K,
                    help=f"число кандидатов в выдаче (по умолчанию {TOP_K})")
    args = ap.parse_args()

    queries = [" ".join(args.query)] if args.query else DEMO_QUERIES
    for q in queries:
        search(q, k=args.top_k)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""RAG-чатбот (REPL) с отключаемым слоем безопасности."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import retriever
import prompt as prompt_mod
import llm
import safety

BLOCKED_MESSAGE = "Ответ: Запрос отклонён системой безопасности (возможная инъекция)."


def answer(query: str, safe: bool = True) -> tuple[str, list[dict], list[dict]]:
    if safe:
        ok, reason = safety.check_query(query)
        if not ok:
            return f"{BLOCKED_MESSAGE} [{reason}]", [], []

    chunks = retriever.retrieve(query)
    dropped: list[dict] = []
    if safe:
        chunks, dropped = safety.filter_chunks(chunks)

    system = prompt_mod.SYSTEM_PROMPT + (prompt_mod.SAFETY_RULE if safe else "")
    response = llm.ask(prompt_mod.build_prompt(query, chunks), system)
    return response, chunks, dropped


def print_sources(chunks: list[dict], dropped: list[dict]) -> None:
    print("\nИсточники:")
    for i, ch in enumerate(chunks, 1):
        m = ch["metadata"]
        sim = ch.get("similarity")
        sim_str = f"{sim:.2f}" if sim is not None else "—"
        print(f"  [{i}] {m.get('source')}  (раздел: {m.get('section') or '—'}, sim={sim_str})")
    for d in dropped:
        print(f"  [фильтр] отброшен {d['metadata'].get('source')} (вредоносный контент)")


def main() -> None:
    ap = argparse.ArgumentParser(description="RAG-чатбот (Haiku 4.5)")
    ap.add_argument("query", nargs="*", help="вопрос; если пусто — интерактивный режим")
    ap.add_argument("--unsafe", action="store_true", help="отключить слой безопасности")
    args = ap.parse_args()
    safe = not args.unsafe
    mode = "БЕЗОПАСНЫЙ" if safe else "НЕБЕЗОПАСНЫЙ"

    if args.query:
        resp, chunks, dropped = answer(" ".join(args.query), safe=safe)
        print(resp)
        print_sources(chunks, dropped)
        return

    print(f"RAG-бот (Haiku 4.5), режим: {mode}. Выход — 'exit' или Ctrl-D.")
    print("Загрузка модели эмбеддингов...")
    retriever.retrieve("разогрев", 1)
    print("Готово.\n")

    while True:
        try:
            query = input("Вопрос> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nПока!")
            break
        if not query:
            continue
        if query.lower() in ("exit", "quit", "выход"):
            print("Пока!")
            break
        try:
            resp, chunks, dropped = answer(query, safe=safe)
        except Exception as e:
            print(f"Ошибка: {e}\n")
            continue
        print("\n" + resp)
        print_sources(chunks, dropped)
        print()


if __name__ == "__main__":
    main()

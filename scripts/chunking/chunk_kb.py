#!/usr/bin/env python3
"""
Чанкинг базы знаний knowledge_base/ для последующей загрузки в Chroma.

Логика:
  1. Определяем тип документа по имени файла (4 типа).
  2. Чистим markdown/wiki-разметку (''' , ** , горизонтальные линии ---).
  3. Режем по заголовкам (MarkdownHeaderTextSplitter) -> логические секции,
     заголовки попадают в метаданные (h1/h2/h3).
  4. Длинные секции добиваем RecursiveCharacterTextSplitter с перекрытием.
  5. Для каждого чанка собираем метаданные и текст для эмбеддинга
     (с «хлебными крошками» — заголовок + секция в начале).

Результат: JSONL, по одному чанку на строку: {id, text, embed_text, metadata}.

Размер чанка подобран под модель paraphrase-multilingual-MiniLM-L12-v2
(max_seq_length=128 токенов). Дефолт chunk_size=300, overlap=50 — при нём
почти все чанки укладываются в лимит модели (проверено токенайзером).

"""

import argparse
import json
import re
from pathlib import Path

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# --- пути по умолчанию ---
ROOT = Path(__file__).resolve().parents[2]
KB_DIR = ROOT / "knowledge_base"
OUT_FILE = Path(__file__).resolve().parent / "chunks.jsonl"

# Подобрано эмпирически под лимит модели в 128 токенов (paraphrase-multilingual-MiniLM-L12-v2):
# при 300/50 ~все чанки укладываются в лимит (max ~136 токенов у единичного чанка с длинными крошками).
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50     # (~16%)

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3"), ("####", "h4")]


def detect_doc_type(filename: str) -> str:
    name = filename.lower()
    if name.startswith("рабочее место"):
        return "location"
    if name.startswith("s1_") or name.startswith("s1"):
        return "episode"
    if name.startswith("страна"):
        return "world"
    return "character"


def parse_episode(filename: str) -> dict:
    """Достаёт season/episode из имени вида s1_e9_..., s1_e14, s1_e59-..."""
    m = re.search(r"s(\d+)_e(\d+)", filename, re.IGNORECASE)
    if m:
        return {"season": int(m.group(1)), "episode": int(m.group(2))}
    return {}


def clean_markdown(text: str) -> str:
    out_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # убираем горизонтальные разделители
        if re.fullmatch(r"-{3,}", stripped):
            continue
        # wiki-заголовок  в markdown заголовок
        m = re.fullmatch(r"(={2,})\s*(.+?)\s*=+", stripped)
        if m:
            level = min(len(m.group(1)), 4)  # глубже h4 не уходим
            line = "#" * level + " " + m.group(2)
            out_lines.append(line)
            continue
        # wiki-ссылки в текст
        line = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", line)
        # снимаем wiki-жирный/курсив 
        line = re.sub(r"'{2,}", "", line)
        line = line.replace("**", "")
        out_lines.append(line)
    text = "\n".join(out_lines)

    #  3+ пустых строк в одну пустую
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_section(meta: dict) -> str:
    """Путь секции для метаданных и хлебных крошек: 'h2 > h3'."""
    parts = [meta.get("h2"), meta.get("h3"), meta.get("h4")]
    return " > ".join(p for p in parts if p)


def make_embed_text(title: str, section: str, text: str) -> str:
    """Текст для эмбеддинга: имя сущности + секция + сам чанк.
    """
    crumbs = title if not section else f"{title} / {section}"
    return f"{crumbs}\n{text}"


def chunk_file(path: Path, char_splitter: RecursiveCharacterTextSplitter) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    cleaned = clean_markdown(raw)

    doc_type = detect_doc_type(path.name)

    # 1) режем по заголовкам
    header_splitter = MarkdownHeaderTextSplitter(HEADERS, strip_headers=True)
    sections = header_splitter.split_text(cleaned)

    # заголовок документа: h1 первой секции (или имя файла без расширения)
    title = ""
    for s in sections:
        if s.metadata.get("h1"):
            title = s.metadata["h1"]
            break
    if not title:
        title = path.stem

    records: list[dict] = []
    idx = 0
    for sec in sections:
        section = build_section(sec.metadata)
        body = sec.page_content.strip()
        if not body:
            continue
        # 2) режем по чанкам, если большая секция
        for piece in char_splitter.split_text(body):
            piece = piece.strip()
            if len(piece) < 2:
                continue
            meta = {
                "source": str(path.relative_to(ROOT)),
                "filename": path.name,
                "doc_type": doc_type,
                "title": title,
                "section": section,
                "chunk_index": idx,
                "n_chars": len(piece),
                "n_words": len(piece.split()),
            }
            meta.update(parse_episode(path.name) if doc_type == "episode" else {})
            records.append({
                "id": f"{path.stem}::{idx}",
                "text": piece,                                   # сырой текст для цитирования
                "embed_text": make_embed_text(title, section, piece),  # текст для эмбеддинга
                "metadata": meta,
            })
            idx += 1
    return records


def main():
    ap = argparse.ArgumentParser(description="Чанкинг knowledge_base -> JSONL")
    ap.add_argument("--kb", type=Path, default=KB_DIR)
    ap.add_argument("--out", type=Path, default=OUT_FILE)
    ap.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    ap.add_argument("--overlap", type=int, default=CHUNK_OVERLAP)
    args = ap.parse_args()

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        # \n намеренно НЕ включаем: одиночный перенос строки часто стоит внутри
        # смыслового блока, и деление по нему плодит обрывочные чанки.
        separators=["\n\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
        keep_separator=True,
        length_function=len,
    )

    files = sorted(args.kb.glob("*.md"))
    all_records: list[dict] = []
    per_type: dict[str, int] = {}
    for f in files:
        recs = chunk_file(f, char_splitter)
        all_records.extend(recs)
        t = detect_doc_type(f.name)
        per_type[t] = per_type.get(t, 0) + len(recs)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for r in all_records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # статистика
    n = len(all_records)
    chars = [r["metadata"]["n_chars"] for r in all_records]
    words = [r["metadata"]["n_words"] for r in all_records]
    over = sum(1 for c in chars if c > 600) 
    print(f"Файлов обработано : {len(files)}")
    print(f"Чанков создано    : {n}")
    print(f"По типам          : {per_type}")
    if n:
        print(f"Символов /чанк    : min={min(chars)} avg={sum(chars)//n} max={max(chars)}")
        print(f"Слов /чанк        : min={min(words)} avg={sum(words)//n} max={max(words)}")
        print(f"Чанков >600 симв. : {over} (проверить токены на этапе эмбеддинга)")
    print(f"Записано в        : {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

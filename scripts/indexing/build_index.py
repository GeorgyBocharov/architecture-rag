#!/usr/bin/env python3
"""
Построение векторного индекса в Chroma из chunks.jsonl.

Шаги:
  1. Загружаем чанки (scripts/chunking/chunks.jsonl).
  2. Загружаем модель paraphrase-multilingual-MiniLM-L12-v2.
  3. ЭМПИРИЧЕСКИ замеряем длину embed_text в токенах настоящим токенайзером
     модели и сверяем с лимитом (max_seq_length=128) — чтобы знать, есть ли обрезка.
  4. Считаем эмбеддинги по embed_text (нормализованные -> косинус).
  5. Заливаем в Chroma: embeddings (от embed_text) + documents (чистый text) + metadata.
  6. Печатаем статистику: число чанков и время генерации (для README).

Запуск (Chroma должна быть поднята в docker):
    .venv/bin/python3 scripts/indexing/build_index.py
"""

import argparse
import json
import time
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = ROOT / "scripts" / "chunking" / "chunks.jsonl"

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION = "knowledge_base"
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
ADD_BATCH = 200          # размер батча при заливке в Chroma
ENCODE_BATCH = 64        # размер батча при кодировании


def load_chunks(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def report_token_lengths(model: SentenceTransformer, texts: list[str]) -> None:
    """Замер реальной длины в токенах + предупреждение об обрезке."""
    limit = model.max_seq_length
    tok = model.tokenizer
    lens = [len(tok(t, add_special_tokens=True)["input_ids"]) for t in texts]
    over = [n for n in lens if n > limit]
    n = len(lens)
    print(f"\n=== Длина embed_text в токенах (лимит модели = {limit}) ===")
    print(f"  min={min(lens)}  avg={sum(lens)//n}  max={max(lens)}")
    print(f"  чанков сверх лимита: {len(over)} из {n} ({100*len(over)//n}%)")
    if over:
        print(f" у {len(over)} чанков обрежется ХВОСТ текста; крошки (имя+секция) "
              f"в начале сохранятся. ")
    else:
        print("все чанки укладываются в лимит.")


def main():
    ap = argparse.ArgumentParser(description="Построение индекса Chroma из chunks.jsonl")
    ap.add_argument("--chunks", type=Path, default=CHUNKS_FILE)
    ap.add_argument("--collection", default=COLLECTION)
    ap.add_argument("--host", default=CHROMA_HOST)
    ap.add_argument("--port", type=int, default=CHROMA_PORT)
    ap.add_argument("--reset", action="store_true", default=True,
                    help="пересоздать коллекцию с нуля (по умолчанию да)")
    args = ap.parse_args()

    
    recs = load_chunks(args.chunks)
    print(f"Загружено чанков: {len(recs)} из {args.chunks.relative_to(ROOT)}")

    
    print(f"Загрузка модели: {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    print(f"  размерность эмбеддинга: {dim}, max_seq_length: {model.max_seq_length}")

    embed_texts = [r["embed_text"] for r in recs]

    
    report_token_lengths(model, embed_texts)

    print(f"\nКодирование {len(embed_texts)} чанков ...")
    t0 = time.perf_counter()
    embeddings = model.encode(
        embed_texts,
        batch_size=ENCODE_BATCH,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    encode_sec = time.perf_counter() - t0
    print(f"  эмбеддинги посчитаны за {encode_sec:.1f} c "
          f"({len(recs)/encode_sec:.0f} чанков/с)")

    client = chromadb.HttpClient(host=args.host, port=args.port)
    print(f"\nChroma heartbeat: {client.heartbeat()}")
    if args.reset:
        try:
            client.delete_collection(args.collection)
            print(f"  старая коллекция '{args.collection}' удалена")
        except Exception:
            pass
    col = client.get_or_create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine"}, 
    )

    t0 = time.perf_counter()
    for i in range(0, len(recs), ADD_BATCH):
        batch = recs[i:i + ADD_BATCH]
        col.add(
            ids=[r["id"] for r in batch],
            embeddings=[embeddings[j].tolist() for j in range(i, i + len(batch))],
            documents=[r["text"] for r in batch],      
            metadatas=[r["metadata"] for r in batch],
        )
        print(f"  залито {min(i + ADD_BATCH, len(recs))}/{len(recs)}")
    add_sec = time.perf_counter() - t0

    print(f"\n=== ГОТОВО ===")
    print(f"Коллекция     : {args.collection}")
    print(f"Чанков в индексе: {col.count()}")
    print(f"Модель        : {MODEL_NAME} (dim={dim})")
    print(f"Время кодирования: {encode_sec:.1f} c | заливки: {add_sec:.1f} c "
          f"| всего: {encode_sec + add_sec:.1f} c")


if __name__ == "__main__":
    main()

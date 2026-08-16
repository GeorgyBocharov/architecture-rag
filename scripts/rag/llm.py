#!/usr/bin/env python3
"""
Обёртка над Claude Code в headless-режиме (`claude -p`) как над LLM-бэкендом.

Системный промпт заменяет дефолтный «кодинг-агент», инструменты не нужны — нам нужна чистая генерация.
"""

import subprocess
import tempfile

MODEL = "claude-haiku-4-5"

# Пустая нейтральная директория: запускаем claude вне проекта, чтобы он не
# «видел» git/файлы репозитория и не подмешивал их в ответ.
_WORKDIR = tempfile.mkdtemp(prefix="rag-llm-")


def ask(prompt: str, system: str, model: str = MODEL) -> str:
    """Отправить промпт в claude -p и вернуть текст ответа (stdout)."""
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--model", model,
            "--system-prompt", system,
            "--output-format", "text",
        ],
        capture_output=True,
        text=True,
        cwd=_WORKDIR,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude вернул код {result.returncode}: {result.stderr.strip()}")
    return result.stdout.strip()

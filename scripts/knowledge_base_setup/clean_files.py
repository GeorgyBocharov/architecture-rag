#!/usr/bin/env python3
"""
Скрипт для очистки файлов от лишних элементов
"""

import re
from pathlib import Path

OUTPUT_DIR = Path("smeshariki-fandom")

# Файлы для обработки
FILES_TO_CLEAN = [
    "s1_e1_Скамейка.md",
    "s1_e10_забытая_история.md",
    "s1_e11_рояль.md",
    "s1_e2_Принц.md",
    "s1_e3_Куда_уходит_старый_год.md",
    "s1_e4_Солнце.md",
    "s1_e5_храп.md",
    "s1_e59-ОРЗ.md",
    "s1_e6_няня.md",
    "s1_e7_подарок_судьбы.md",
    "s1_e8_кто_первый.md",
    "s1_e9_некультурный.md",
    "страна смешариков.md",
    "смешарики-base.md",
    "Домик_Бараша.md",
    "Домик_Ёжика.md",
    "Домик_Кар-Карыча.md",
    "Домик_Копатыча.md",
    "Домик_Кроша.md",
    "Домик_Лосяша.md",
    "Домик_Нюши.md",
    "Домик_Пина.md",
]


def clean_file(file_path: Path):
    """Очистка файла"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Разделяем на строки
    lines = content.split('\n')
    
    # Находим заголовок H1
    title_line = None
    start_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('# '):
            title_line = line
            start_idx = i + 1
            break
    
    # Если заголовка нет, пробуем найти название из имени файла
    if not title_line:
        filename = file_path.stem
        # Для эпизодов
        if filename.startswith('s1_e'):
            parts = filename.split('_', 2)
            if len(parts) >= 3:
                title = parts[2].replace('_', ' ').capitalize()
            else:
                title = filename.replace('_', ' ').capitalize()
        else:
            title = filename.replace('_', ' ').capitalize()
        title_line = f"# {title}"
        start_idx = 0
    
    # Берем контент после заголовка и источника
    content_lines = lines[start_idx:]
    
    # Пропускаем строки с источником и разделителем
    while content_lines and (
        content_lines[0].strip() == '' or
        content_lines[0].strip() == '---' or
        '**Источник:**' in content_lines[0]
    ):
        content_lines.pop(0)
    
    # Пропускаем пустые строки в начале
    while content_lines and content_lines[0].strip() == '':
        content_lines.pop(0)
    
    # Собираем текст
    text = '\n'.join(content_lines)
    
    # Преобразуем '''жирный текст''' в **жирный текст**
    text = re.sub(r"'''([^']+)'''", r'**\1**', text)
    
    # Удаляем thumb|... из строк
    text = re.sub(r'^thumb\|.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'thumb\|[^|\n]+', '', text)
    
    # Удаляем оставшиеся разделители в начале
    text = text.lstrip('\n')
    text = re.sub(r'^---+\n+', '', text)
    
    # Добавляем заголовок в начало
    final_text = f"{title_line}\n\n{text}"
    
    # Записываем обратно
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(final_text)
    
    print(f"✓ {file_path.name}")


def main():
    print("Очистка файлов...")
    for filename in FILES_TO_CLEAN:
        input_path = OUTPUT_DIR / filename
        if input_path.exists():
            clean_file(input_path)
        else:
            print(f"✗ Не найден: {input_path}")
    
    print(f"\nГотово! Обработано файлов: {len(FILES_TO_CLEAN)}")


if __name__ == '__main__':
    main()

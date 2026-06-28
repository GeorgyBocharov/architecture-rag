#!/usr/bin/env python3
"""
Скрипт для конвертации файлов в smeshariki-fandom
с очисткой от вики-разметки и навигационных таблиц
"""

import re
from pathlib import Path

OUTPUT_DIR = Path("smeshariki-fandom")

# Файлы для конвертации (эпизоды)
EPISODE_FILES = [
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
]

# Файлы для конвертации (локации и базы)
LOCATION_FILES = [
    "страна смешариков.md",
    "смешарики-base.md",
]

HOUSE_FILES = [
    "Домик_Бараша.md",
    "Домик_Ёжика.md",
    "Домик_Кар-Карыча.md",
    "Домик_Копатыча.md",
    "Домик_Кроша.md",
    "Домик_Лосяша.md",
    "Домик_Нюши.md",
    "Домик_Пина.md",
]


def clean_wiki_markup(text: str) -> str:
    """Очистка вики-разметки"""
    # Удаляем карточку персонажа {{Персонаж ... }}
    text = re.sub(r'\{\{Персонаж.*?\}\}\n', '', text, flags=re.DOTALL)
    
    # Удаляем шаблоны {{Эпизод ... }}
    text = re.sub(r'\{\{Эпизод.*?\}\}\n', '', text, flags=re.DOTALL)
    
    # Удаляем шаблоны {{Место ... }}
    text = re.sub(r'\{\{Место.*?\}\}\n', '', text, flags=re.DOTALL)
    
    # Удаляем шаблоны {{Табло серий ... }}
    text = re.sub(r'\{\{Табло серий.*?\}\}\n', '', text, flags=re.DOTALL)
    
    # Удаляем шаблоны {{Значения}}
    text = re.sub(r'\{\{Значения\}\}\n?', '', text)
    
    # Удаляем шаблоны {{Цитата ... }}
    text = re.sub(r'\{\{Цитата\|(.*?)\}\}', r'"\1"', text, flags=re.DOTALL)
    
    # Удаляем шаблоны {{Основная статья|...}}
    text = re.sub(r'\{\{Основная статья\|.*?\}\}', '', text)
    
    # Удаляем шаблоны {{Список мест ... }}
    text = re.sub(r'\{\{Список мест.*?\}\}\n', '', text, flags=re.DOTALL)
    
    # Удаляем шаблоны {{Map:...}}
    text = re.sub(r'\{\{Map:[^}]+\}\}', '', text)
    
    # Удаляем шаблоны {{Подсказка|...}}
    text = re.sub(r'\{\{Подсказка\|[^}]+\}\}', '', text)
    
    # Удаляем шаблоны {{Brclear}}
    text = re.sub(r'\{\{Brclear\}\}', '', text)
    
    # Удаляем шаблоны {{Примечания}}
    text = re.sub(r'\{\{Примечания\}\}', '', text)
    
    # Удаляем шаблоны {{Основной сериал}}
    text = re.sub(r'\{\{Основной сериал\}\}', '', text)
    
    # Удаляем шаблоны {{Места}}
    text = re.sub(r'\{\{Места\}\}', '', text)
    
    # Удаляем шаблоны {{...}}
    text = re.sub(r'\{\{[^}]+\}\}', '', text)
    
    # Удаляем <ref>...</ref>
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    
    # Удаляем <gallery>...</gallery>
    text = re.sub(r'<gallery.*?>.*?</gallery>', '', text, flags=re.DOTALL)
    
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем [[...|...]] -> оставляем только текст после |
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', text)
    # Удаляем [[...]] -> оставляем текст
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
    
    # Удаляем навигационные таблицы
    text = re.sub(r'развернуть\s*п\s*·\s*р.*', '', text)
    
    # Удаляем секции "Галерея", "Примечания", "См. также", "Издания"
    text = re.sub(r'==+ Галерея ==+.*', '', text, flags=re.DOTALL)
    text = re.sub(r'==+ Примечания ==+.*', '', text, flags=re.DOTALL)
    text = re.sub(r'==+ См\. также ==+.*', '', text, flags=re.DOTALL)
    text = re.sub(r'==+ Издания.*?==+.*', '', text, flags=re.DOTALL)
    
    # Удаляем таблицы с навигацией
    nav_keywords = [
        'Дома', 'Здания', 'Природные', 'Спортивные', 'Леса', 'Водоёмы',
        'Острова', 'Космос', 'Страны', 'Населённые', 'Эпохи', 'Вселенные',
        'Шаролёт', 'Фильм', 'Мегаполис', 'Основная локация', 'Серии',
        'Песни', 'Вещи', 'Места', 'п · р', 'Категория:'
    ]
    lines = text.split('\n')
    filtered_lines = []
    skip_until_next_heading = False
    
    for line in lines:
        # Проверяем, является ли строка навигационной
        is_nav = any(kw in line for kw in nav_keywords)
        
        # Пропускаем категории
        if line.strip().startswith('[[Категория:'):
            continue
        
        # Пропускаем интервики ссылки
        if line.strip().startswith('[[') and ':' in line and 'en:' in line:
            continue
        
        if is_nav and re.match(r'^#+', line):
            # Это заголовок навигационной секции
            skip_until_next_heading = True
            continue
        
        if skip_until_next_heading:
            if re.match(r'^#+', line) and not is_nav:
                skip_until_next_heading = False
            else:
                continue
        
        if not is_nav or len(line) < 50:
            filtered_lines.append(line)
    
    text = '\n'.join(filtered_lines)
    
    # Удаляем пустые строки
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Удаляем File:/Изображения
    text = re.sub(r'\[\[Файл:[^\]]+\]\]', '', text)
    text = re.sub(r'\[\[Image:[^\]]+\]\]', '', text)
    text = re.sub(r'\[\[File:[^\]]+\]\]', '', text)
    
    # Удаляем thumb из заголовков
    text = re.sub(r'\|thumb.*?$', '', text, flags=re.MULTILINE)
    
    # Очищаем заголовки
    text = re.sub(r'^==+\s*(Одежда и вещи)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Индивидуальность и черты)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Характер)\s*==+', r'### \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Знания и навыки)\s*==+', r'### \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Предпочтения)\s*==+', r'### \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Страхи.*?|Страхи, травмы и болезни)\s*==+', r'### \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Отношения)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Интересные факты)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Биография)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Описание)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Появления)\s*==+', r'## \1', text, flags=re.DOTALL)
    text = re.sub(r'^==+\s*(Сюжет)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Персонажи)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Места)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Цитаты)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Издания серии)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Ляпы)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(История создания)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Основные персонажи)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Проекты франшизы)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Продукция)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Сайт «Смешариков»)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Достижения и награды)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Карта страны)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Описание)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(История)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Физико-географическая характеристика)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Устройство страны)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Достопримечательности)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Снаружи)\s*==+', r'## \1', text, flags=re.MULTILINE)
    text = re.sub(r'^==+\s*(Внутри)\s*==+', r'## \1', text, flags=re.MULTILINE)
    
    # Удаляем оставшиеся шаблоны цитат
    text = re.sub(r'\{\{Цитата\|.*?\}\}', '', text, flags=re.DOTALL)
    
    # Удаляем таблицы wiki (простые)
    text = re.sub(r'\{\|.*?\|\}', '', text, flags=re.DOTALL)
    text = re.sub(r'^\|-.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^!\s*.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\|.*$', '', text, flags=re.MULTILINE)
    
    return text.strip()


def convert_episode(input_path: Path, output_path: Path):
    """Конвертация файла эпизода"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Извлекаем название эпизода из имени файла
    # Формат: s1_e1_Скамейка.md -> Скамейка
    filename = input_path.stem
    parts = filename.split('_', 2)
    if len(parts) >= 3:
        episode_title = parts[2].replace('_', ' ').capitalize()
    else:
        episode_title = filename.replace('_', ' ').capitalize()
    
    # Очищаем контент
    cleaned = clean_wiki_markup(content)
    
    # Форматируем в markdown
    output = f"# {episode_title}\n\n"
    output += f"\n\n"
    output += "---\n\n"
    output += cleaned
    
    # Сохраняем
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"✓ {input_path.name} -> {output_path.name}")


def convert_location(input_path: Path, output_path: Path):
    """Конвертация файла локации/базы"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Извлекаем название из имени файла
    filename = input_path.stem
    title = filename.replace('_', ' ').capitalize()
    
    # Очищаем контент
    cleaned = clean_wiki_markup(content)
    
    # Форматируем в markdown
    output = f"# {title}\n\n"
    output += f"\n\n"
    output += "---\n\n"
    output += cleaned
    
    # Сохраняем
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"✓ {input_path.name} -> {output_path.name}")


def convert_house(input_path: Path, output_path: Path):
    """Конвертация файла домика"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Извлекаем название из имени файла
    filename = input_path.stem
    title = filename.replace('_', ' ').capitalize()
    
    # Очищаем контент
    cleaned = clean_wiki_markup(content)
    
    # Форматируем в markdown
    output = f"# {title}\n\n"
    output += f"\n\n"
    output += "---\n\n"
    output += cleaned
    
    # Сохраняем
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"✓ {input_path.name} -> {output_path.name}")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print("Конвертация эпизодов...")
    for filename in EPISODE_FILES:
        input_path = OUTPUT_DIR / filename
        if input_path.exists():
            output_path = OUTPUT_DIR / filename
            convert_episode(input_path, output_path)
        else:
            print(f"✗ Не найден: {input_path}")
    
    print("\nКонвертация локаций и баз...")
    for filename in LOCATION_FILES:
        input_path = OUTPUT_DIR / filename
        if input_path.exists():
            output_path = OUTPUT_DIR / filename
            convert_location(input_path, output_path)
        else:
            print(f"✗ Не найден: {input_path}")
    
    print("\nКонвертация домиков...")
    for filename in HOUSE_FILES:
        input_path = OUTPUT_DIR / filename
        if input_path.exists():
            output_path = OUTPUT_DIR / filename
            convert_house(input_path, output_path)
        else:
            print(f"✗ Не найден: {input_path}")
    
    total_files = len(EPISODE_FILES) + len(LOCATION_FILES) + len(HOUSE_FILES)
    print(f"\nГотово! Обработано файлов: {total_files}")


if __name__ == '__main__':
    main()

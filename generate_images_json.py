"""
generate_images_json.py
───────────────────────
Сканирует папку с картинками и создаёт images.json для booru-сайта.

Использование:
  python generate_images_json.py

Настройки — смотри раздел CONFIG ниже.
"""

import os
import json
import re
from datetime import datetime, timezone

# ── CONFIG ────────────────────────────────────────────────────────────────────

# Папка с картинками (относительно этого скрипта)
IMAGE_FOLDER = "images"

# Куда сохранить результат
OUTPUT_FILE = "images.json"

# Поддерживаемые форматы
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}

# Автоматически превращать имя файла в теги?
# Например: "cute_cat_2024.jpg" → ["cute", "cat", "2024"]
TAGS_FROM_FILENAME = True

# Символы-разделители в имени файла (для авто-тегов)
# Например: "cute-cat 2024" → разбивается по "-" и " "
TAG_SEPARATORS = r"[_\-\s\.]+"

# Исключить из тегов: числа, одиночные буквы, стандартные суффиксы
FILTER_WEAK_TAGS = True

# ── SCRIPT ────────────────────────────────────────────────────────────────────

def filename_to_tags(filename: str) -> list[str]:
    """Превращает имя файла (без расширения) в список тегов."""
    name = os.path.splitext(filename)[0]
    parts = re.split(TAG_SEPARATORS, name.lower())
    tags = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if FILTER_WEAK_TAGS:
            # пропускаем: только цифры, одну букву, типичные суффиксы
            if re.fullmatch(r"\d+", part):
                continue
            if len(part) <= 1:
                continue
            if part in {"img", "image", "pic", "photo", "copy", "final", "new", "old", "tmp"}:
                continue
        tags.append(part)
    return tags


def scan_folder(folder: str) -> list[dict]:
    """Рекурсивно сканирует папку и возвращает список записей."""
    entries = []

    if not os.path.isdir(folder):
        print(f"  [!] Папка не найдена: '{folder}'")
        print(f"      Создай папку '{folder}' и положи туда картинки.")
        return entries

    for root, dirs, files in os.walk(folder):
        # Сортируем для стабильного порядка
        dirs.sort()
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            # Путь относительно скрипта (как будет в браузере)
            rel_path = os.path.join(root, filename).replace("\\", "/")

            # Дата последнего изменения файла (ISO 8601, UTC)
            mtime = os.path.getmtime(os.path.join(root, filename))
            date_str = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            tags = filename_to_tags(filename) if TAGS_FROM_FILENAME else []

            entries.append({
                "file": rel_path,
                "date": date_str,
                "tags": tags
            })

    return entries


def main():
    print("=" * 50)
    print("  booru · generate_images_json.py")
    print("=" * 50)
    print(f"\n  Сканирую папку: '{IMAGE_FOLDER}' ...")

    entries = scan_folder(IMAGE_FOLDER)

    if not entries:
        print("\n  Картинки не найдены. Проверь папку и расширения файлов.")
        return

    print(f"  Найдено файлов: {len(entries)}")

    # Статистика по форматам
    from collections import Counter
    exts = Counter(os.path.splitext(e["file"])[1].lower() for e in entries)
    for ext, count in exts.most_common():
        print(f"    {ext:8s} → {count} шт.")

    # Сохраняем
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"\n  ✓ Сохранено в '{OUTPUT_FILE}'")
    print(f"  Каждая запись содержит поле 'date' (дата изменения файла).")
    print(f"\n  Следующий шаг:")
    print(f"  Открой '{OUTPUT_FILE}' в любом текстовом редакторе")
    print(f"  и заполни теги для каждой картинки вручную.")
    print(f"\n  Формат одной записи:")
    print(f'    {{"file": "images/pic.jpg", "date": "2024-06-01T12:00:00Z", "tags": ["tag1", "tag2"]}}')
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()

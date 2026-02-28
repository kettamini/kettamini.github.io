"""
generate_images_json.py
───────────────────────
Сканирует папку с картинками, генерирует thumbnails и создаёт images.json.

Зависимости:
  pip install Pillow

Использование:
  python generate_images_json.py

Настройки — смотри раздел CONFIG ниже.
"""

import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("[!] Pillow не установлен. Запусти: pip install Pillow")
    exit(1)

# ── CONFIG ────────────────────────────────────────────────────────────────────

# Папка с оригиналами
IMAGE_FOLDER = "images"

# Папка для thumbnails (создастся автоматически)
THUMB_FOLDER = "thumbs"

# Размер thumbnail: максимальная сторона в пикселях
# 480px — хорошо выглядит в сетке на 2K, быстро грузится
THUMB_MAX_SIZE = 480

# Качество JPEG для thumbnails (1–95)
THUMB_QUALITY = 82

# Все thumbnails сохранять как JPEG (меньше весят)?
# False — сохранять в том же формате что оригинал
THUMB_FORCE_JPEG = True

# Пересоздавать thumbnail если он уже существует?
# False — пропускать существующие (быстрее при добавлении новых файлов)
THUMB_OVERWRITE = False

# Куда сохранить результат
OUTPUT_FILE = "images.json"

# Поддерживаемые форматы
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}

# Автоматически превращать имя файла в теги?
TAGS_FROM_FILENAME = True

# Символы-разделители в имени файла
TAG_SEPARATORS = r"[_\-\s\.]+"

# Фильтровать мусорные теги
FILTER_WEAK_TAGS = True

# ── FUNCTIONS ─────────────────────────────────────────────────────────────────

def filename_to_tags(filename: str) -> list[str]:
    name = os.path.splitext(filename)[0]
    parts = re.split(TAG_SEPARATORS, name.lower())
    tags = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if FILTER_WEAK_TAGS:
            if re.fullmatch(r"\d+", part):
                continue
            if len(part) <= 1:
                continue
            if part in {"img", "image", "pic", "photo", "copy", "final", "new", "old", "tmp"}:
                continue
        tags.append(part)
    return tags


def make_thumbnail(src_path: str, thumb_path: str) -> bool:
    """
    Создаёт thumbnail. Возвращает True если создан, False если пропущен.
    """
    if not THUMB_OVERWRITE and os.path.exists(thumb_path):
        return False

    try:
        with Image.open(src_path) as img:
            # Сохраняем EXIF-ориентацию (важно для фото с телефона)
            img = ImageOps.exif_transpose(img)

            # Конвертируем в RGB если сохраняем в JPEG
            save_as_jpeg = THUMB_FORCE_JPEG or Path(src_path).suffix.lower() in {".jpg", ".jpeg"}
            if save_as_jpeg and img.mode in ("RGBA", "P", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                img = background
            elif save_as_jpeg and img.mode != "RGB":
                img = img.convert("RGB")

            # Ресайз с сохранением пропорций
            img.thumbnail((THUMB_MAX_SIZE, THUMB_MAX_SIZE), Image.LANCZOS)

            # Сохраняем
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            if save_as_jpeg:
                img.save(thumb_path, "JPEG", quality=THUMB_QUALITY, optimize=True)
            else:
                img.save(thumb_path, optimize=True)

        return True

    except Exception as e:
        print(f"\n    [!] Ошибка при обработке {src_path}: {e}")
        return False


def scan_and_generate(folder: str) -> list[dict]:
    entries = []
    created = 0
    skipped = 0
    errors  = 0

    if not os.path.isdir(folder):
        print(f"  [!] Папка не найдена: '{folder}'")
        return entries

    # Собираем все файлы
    all_files = []
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                all_files.append((root, filename))

    total = len(all_files)
    print(f"  Найдено файлов: {total}")
    print(f"  Генерирую thumbnails ({THUMB_MAX_SIZE}px) ...\n")

    for i, (root, filename) in enumerate(all_files, 1):
        src_path = os.path.join(root, filename)
        rel_path = src_path.replace("\\", "/")

        # Путь для thumbnail — зеркалим структуру папок
        name_noext = os.path.splitext(filename)[0]
        thumb_ext  = ".jpg" if THUMB_FORCE_JPEG else os.path.splitext(filename)[1].lower()
        thumb_name = name_noext + thumb_ext
        rel_subdir = os.path.relpath(root, folder)
        if rel_subdir == ".":
            thumb_path = os.path.join(THUMB_FOLDER, thumb_name)
        else:
            thumb_path = os.path.join(THUMB_FOLDER, rel_subdir, thumb_name)
        thumb_rel = thumb_path.replace("\\", "/")

        # Прогресс-бар
        bar_len = 30
        filled  = int(bar_len * i / total)
        bar     = "█" * filled + "░" * (bar_len - filled)
        print(f"  [{bar}] {i}/{total}  {filename[:38]:<38}", end="\r")

        result = make_thumbnail(src_path, thumb_path)
        if result is True:
            created += 1
        elif result is False:
            skipped += 1
        else:
            errors += 1

        # Дата изменения оригинала
        mtime    = os.path.getmtime(src_path)
        date_str = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        tags = filename_to_tags(filename) if TAGS_FROM_FILENAME else []

        entries.append({
            "file":  rel_path,
            "thumb": thumb_rel,
            "date":  date_str,
            "tags":  tags,
        })

    print()  # новая строка после прогресс-бара
    print(f"\n  Thumbnails: {created} создано  |  {skipped} пропущено  |  {errors} ошибок")
    return entries


def main():
    print("=" * 52)
    print("  booru · generate_images_json.py")
    print("=" * 52)
    print(f"\n  Папка с оригиналами : '{IMAGE_FOLDER}'")
    print(f"  Папка thumbnails    : '{THUMB_FOLDER}'")
    print(f"  Размер thumbnail    : {THUMB_MAX_SIZE}px (макс. сторона)")
    print()

    entries = scan_and_generate(IMAGE_FOLDER)

    if not entries:
        print("\n  Картинки не найдены.")
        return

    # Статистика по форматам
    from collections import Counter
    exts = Counter(os.path.splitext(e["file"])[1].lower() for e in entries)
    print("\n  Форматы оригиналов:")
    for ext, count in exts.most_common():
        print(f"    {ext:8s} → {count} шт.")

    # Сохраняем JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"\n  ✓ Сохранено: '{OUTPUT_FILE}' ({len(entries)} записей)")
    print(f"\n  Не забудь залить на GitHub:")
    print(f"    git add images.json {THUMB_FOLDER}/")
    print(f"    git commit -m \"update images\"")
    print(f"    git push")
    print("\n" + "=" * 52)


if __name__ == "__main__":
    main()
    input("\nНажми Enter для выхода...")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка карманного справочника по системному анализу.

Использование:
    python3 build.py                   — собрать pocket-book.html
    python3 build.py --sync-toc        — синхронизировать глобальный TOC во всех главах
                                          по эталону из index.html
    python3 build.py --check-toc-sync  — проверить, что TOC во всех главах
                                          синхронизирован с index.html (без изменений)
    python3 build.py --check           — проверить HTML на баланс тегов и наличие маркеров,
                                          наличие обязательных блоков в предметных главах
                                          (chapter-learn, chapter-summary, chapter-sources),
                                          а также вывести справочный отчёт о ссылках на ещё
                                          не написанные главы (не блокирует сборку)

Никаких внешних зависимостей. Python 3.10+.
"""

import re
import sys
from pathlib import Path

# ────────────────────────────────────────────────────────────
# Пути и константы
# ────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent
STYLES = ROOT / "styles.css"
INDEX = ROOT / "index.html"
CHAPTERS_DIR = ROOT / "chapters"
OUTPUT = ROOT / "pocket-book.html"

INDEX_MARKER = ("<!-- INDEX-CONTENT-START -->", "<!-- INDEX-CONTENT-END -->")
CHAPTER_MARKER = ("<!-- CHAPTER-CONTENT-START -->", "<!-- CHAPTER-CONTENT-END -->")
TOC_GLOBAL_MARKER = ("<!-- TOC-GLOBAL-INCLUDE -->", "<!-- /TOC-GLOBAL-INCLUDE -->")
TOC_LOCAL_MARKER = ("<!-- TOC-LOCAL-INCLUDE -->", "<!-- /TOC-LOCAL-INCLUDE -->")

BALANCED_TAGS = ["section", "div", "article", "aside", "main", "header",
                 "ol", "ul", "table", "tr", "td", "th",
                 "h1", "h2", "h3", "h4"]


# ────────────────────────────────────────────────────────────
# Утилиты
# ────────────────────────────────────────────────────────────

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_between(text: str, start_marker: str, end_marker: str) -> str | None:
    pattern = re.compile(
        re.escape(start_marker) + r"(.*?)" + re.escape(end_marker),
        re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def get_chapter_files() -> list[Path]:
    return sorted(CHAPTERS_DIR.glob("[0-9][0-9]-*.html"))


# ────────────────────────────────────────────────────────────
# Валидация
# ────────────────────────────────────────────────────────────

def check_tag_balance(html: str, label: str) -> list[str]:
    problems = []
    for tag in BALANCED_TAGS:
        opens = len(re.findall(rf'<{tag}[\s>]', html))
        closes = len(re.findall(rf'</{tag}>', html))
        if opens != closes:
            problems.append(f"  {label} → <{tag}>: открыто {opens}, закрыто {closes}")
    return problems


def check_required_markers(html: str, label: str, markers: list[tuple[str, str]]) -> list[str]:
    problems = []
    for start, end in markers:
        if start not in html:
            problems.append(f"  {label} → отсутствует маркер: {start}")
        if end not in html:
            problems.append(f"  {label} → отсутствует маркер: {end}")
    return problems


# Обязательные блоки предметной главы (всех, кроме вводной 00).
# Класс — единственный надёжный признак: проверяем по class="..." с учётом
# того, что в значении класса могут быть и другие классы.
REQUIRED_CHAPTER_BLOCKS = [
    ("chapter-learn",   "обязательный блок «Что вы узнаете»"),
    ("chapter-summary", "обязательный блок «Резюме главы»"),
    ("chapter-sources", "обязательный блок «Дополнительные источники»"),
]


def has_class(html: str, class_name: str) -> bool:
    """Проверяет, встречается ли class_name среди классов хотя бы одного элемента.
    Простой и устойчивый к мультиклассам поиск: ищет class="..." и
    смотрит, есть ли class_name среди значений, разделённых пробелами."""
    pattern = re.compile(r'class="([^"]*)"')
    for m in pattern.finditer(html):
        classes = m.group(1).split()
        if class_name in classes:
            return True
    return False


# ────────────────────────────────────────────────────────────
# Отчёт о ссылках на ещё не написанные главы
# ────────────────────────────────────────────────────────────
# Главы пишутся последовательно, и в коде уже написанной главы могут
# встречаться ссылки на главы, которые ещё не существуют (например,
# из гл. 02 на § 04-XX). Это допустимо по редстандарту § 05.10:
# ссылки в пустоту не блокируют сборку, но build.py --check выдаёт
# по ним справочный отчёт, чтобы автор видел текущее состояние.

# Регулярное выражение для кросс-ссылок вида NN-name.html(#anchor)?
CROSS_LINK_RE = re.compile(r'href="(\d{2}-[a-z0-9-]+\.html)(#[a-z0-9-]+)?"')


def collect_dangling_chapter_links(chapter_files: list[Path]) -> list[str]:
    """Находит в файлах глав ссылки на главы, которых ещё нет в chapters/.
    Возвращает список строк вида '01-role.html → 04-functional-requirements.html#ch04-dor-dod'.

    Глобальный TOC исключается из проверки: он намеренно содержит ссылки на все
    20 глав, в т.ч. на ещё не написанные. Это часть архитектуры (заглушки в боковой
    панели нужны для устойчивой навигации), а не проблема.
    """
    existing = {f.name for f in chapter_files}
    dangling = []
    for f in chapter_files:
        text = read_text(f)
        # Вырезаем содержимое TOC-GLOBAL из проверяемого текста
        toc_content = extract_between(text, *TOC_GLOBAL_MARKER)
        if toc_content:
            text_to_check = text.replace(toc_content, '')
        else:
            text_to_check = text
        for target_file, anchor in CROSS_LINK_RE.findall(text_to_check):
            if target_file == f.name:
                # внутриглавная ссылка через имя файла — отдельный случай,
                # не считаем dangling, но отмечаем как стилистическое отклонение
                continue
            if target_file not in existing:
                full = target_file + (anchor or '')
                dangling.append(f"  {f.name} → {full}")
    return sorted(set(dangling))


def check_required_chapter_blocks(html: str, label: str) -> list[str]:
    """Проверка наличия обязательных блоков предметной главы.
    Для вводной главы 00 не применяется (её структура упрощена,
    см. редстандарт § 04, «Исключение: вводная глава 00»)."""
    problems = []
    for class_name, description in REQUIRED_CHAPTER_BLOCKS:
        if not has_class(html, class_name):
            problems.append(
                f"  {label} → отсутствует {description} "
                f"(не найден элемент с class=\"{class_name}\")"
            )
    return problems


def is_intro_chapter(filename: str) -> bool:
    """Вводная глава 00 — единственная без обязательных блоков обёртки."""
    return bool(re.match(r"00-", filename))


def run_checks() -> int:
    all_problems = []

    if not INDEX.exists():
        all_problems.append(f"Не найден {INDEX}")
    else:
        text = read_text(INDEX)
        all_problems.extend(check_tag_balance(text, INDEX.name))
        all_problems.extend(check_required_markers(
            text, INDEX.name, [INDEX_MARKER, TOC_GLOBAL_MARKER]
        ))

    if not STYLES.exists():
        all_problems.append(f"Не найден {STYLES}")

    files = get_chapter_files()
    if not files:
        print("⚠ Внимание: в chapters/ нет файлов глав")
    for f in files:
        text = read_text(f)
        all_problems.extend(check_tag_balance(text, f.name))
        all_problems.extend(check_required_markers(
            text, f.name,
            [CHAPTER_MARKER, TOC_GLOBAL_MARKER, TOC_LOCAL_MARKER]
        ))
        # Для предметных глав — проверка обязательных блоков обёртки.
        if not is_intro_chapter(f.name):
            all_problems.extend(check_required_chapter_blocks(text, f.name))

    # Справочный отчёт о ссылках на ещё не написанные главы.
    # НЕ блокирует сборку: главы пишутся последовательно, такие
    # ссылки допустимы (см. редстандарт § 05.10).
    dangling = collect_dangling_chapter_links(files)
    if dangling:
        print(f"ℹ Ссылки на ещё не написанные главы ({len(dangling)} шт., не блокирует):")
        for d in dangling:
            print(d)

    if all_problems:
        print("❌ Проблемы:")
        for p in all_problems:
            print(p)
        return 1
    print(f"✓ Проверка пройдена ({1 + len(files)} файлов)")
    return 0


# ────────────────────────────────────────────────────────────
# Синхронизация глобального TOC
# ────────────────────────────────────────────────────────────

def get_toc_from_index() -> str:
    index_text = read_text(INDEX)
    toc = extract_between(index_text, *TOC_GLOBAL_MARKER)
    if toc is None:
        sys.exit(f"В {INDEX.name} нет маркеров {TOC_GLOBAL_MARKER[0]}")
    return toc


def adapt_toc_for_chapter(toc_html: str, current_chapter_filename: str) -> str:
    """
    Адаптирует TOC из index.html (с путями chapters/...) под расположение
    в файле главы (где пути относительные NN-name.html).
    Дополнительно помечает текущую главу class="is-current".
    """
    adapted = toc_html.replace('href="chapters/', 'href="')
    # Ссылки на корневые файлы (glossary.html и т.п.) из chapters/ ведут на уровень выше
    adapted = adapted.replace('href="glossary.html"', 'href="../glossary.html"')
    # То же для файлов в meta/ (редакционный стандарт и др.):
    # из chapters/ путь начинается с ../meta/
    adapted = adapted.replace('href="meta/', 'href="../meta/')
    adapted = re.sub(r'\s*class="is-current"', '', adapted)
    adapted = adapted.replace(
        f'href="{current_chapter_filename}"',
        f'href="{current_chapter_filename}" class="is-current"',
        1,
    )
    return adapted


def sync_toc(check_only: bool = False) -> int:
    toc = get_toc_from_index()

    # Валидация эталонного TOC перед распространением
    toc_problems = check_tag_balance(toc, "index.html → TOC-GLOBAL")
    if toc_problems:
        print("❌ Эталонный TOC в index.html содержит ошибки. Не распространяю.")
        for p in toc_problems:
            print(p)
        return 1

    files = get_chapter_files()
    if not files:
        print("⚠ Нет файлов глав для синхронизации")
        return 0

    pattern = re.compile(
        re.escape(TOC_GLOBAL_MARKER[0]) + r".*?" + re.escape(TOC_GLOBAL_MARKER[1]),
        re.DOTALL,
    )

    out_of_sync = []
    updated = 0
    for f in files:
        text = read_text(f)
        if TOC_GLOBAL_MARKER[0] not in text:
            print(f"  ⚠ {f.name}: нет маркера TOC-GLOBAL — пропускаю")
            continue

        adapted_toc = adapt_toc_for_chapter(toc, f.name)
        new_block = f"{TOC_GLOBAL_MARKER[0]}\n{adapted_toc}\n{TOC_GLOBAL_MARKER[1]}"
        new_text = pattern.sub(new_block, text, count=1)

        if new_text != text:
            if check_only:
                out_of_sync.append(f.name)
                print(f"  ✗ {f.name} (требует синхронизации)")
            else:
                write_text(f, new_text)
                updated += 1
                print(f"  ✓ {f.name}")
        else:
            print(f"  · {f.name} (без изменений)")

    if check_only:
        if out_of_sync:
            print(f"\n❌ TOC рассинхронизирован в {len(out_of_sync)} файлах из {len(files)}.")
            print("   Запустите локально: python3 build.py --sync-toc")
            return 1
        print(f"\n✓ TOC синхронизирован во всех {len(files)} файлах")
        return 0

    print(f"\n✓ Синхронизировано: {updated} из {len(files)}")
    return 0


# ────────────────────────────────────────────────────────────
# Преобразование ссылок и обёртка
# ────────────────────────────────────────────────────────────

def transform_chapter_links(html: str, chapter_filenames: list[str]) -> str:
    html = re.sub(r'\s*class="is-current"', '', html)
    for fname in chapter_filenames:
        m = re.match(r"(\d{2})-", fname)
        if not m:
            continue
        num = m.group(1)
        anchor = f"#ch-{num}"
        for prefix in ("../chapters/", "chapters/", ""):
            html = html.replace(f'href="{prefix}{fname}"', f'href="{anchor}"')
    # Ссылки из глав на meta/ записаны относительно chapters/ (../meta/...).
    # В собранной книге pocket-book.html лежит в корне, поэтому ../meta/
    # указывает выше корня сайта. Адаптируем под корневое расположение.
    html = html.replace('href="../meta/', 'href="meta/')
    # То же для глоссария: ссылка из chapters/ записана как ../glossary.html,
    # в собранной книге это должно стать просто glossary.html.
    html = html.replace('href="../glossary.html', 'href="glossary.html')
    return html


def wrap_chapter_with_anchor(chapter_html: str, num: str) -> str:
    return re.sub(
        r'<article class="chapter"',
        f'<article class="chapter" id="ch-{num}"',
        chapter_html,
        count=1,
    )


# ────────────────────────────────────────────────────────────
# Извлечение локального TOC главы и сборка хост-контейнера
# ────────────────────────────────────────────────────────────

def extract_toc_local(html: str) -> str | None:
    """Извлекает aside.toc-local из текста главы — содержимое между маркерами
    TOC-LOCAL-INCLUDE / /TOC-LOCAL-INCLUDE."""
    return extract_between(html, *TOC_LOCAL_MARKER)


def attach_chapter_to_toc_local(toc_local_html: str, chapter_num: str) -> str:
    """Помечает aside.toc-local идентификатором главы через data-chapter,
    чтобы JS в собранной книге мог переключать активный блок."""
    return re.sub(
        r'<aside class="toc-local"',
        f'<aside class="toc-local" data-chapter="{chapter_num}"',
        toc_local_html,
        count=1,
    )


# ────────────────────────────────────────────────────────────
# Парсинг частей из index.html
# ────────────────────────────────────────────────────────────

# Регулярки для двух возможных источников разметки частей:
# 1. outline-part (раздел «Содержание» в index.html) — приоритетный источник.
# 2. toc-part (TOC-GLOBAL) — фоллбэк, если outline отсутствует.

# Структура outline-part:
#   <div class="outline-part">
#     <div class="outline-part-title">… <strong>Название</strong> …</div>
#     <ul class="outline-chapters">
#       <li>… <a href="chapters/NN-slug.html">…</a> …</li>
#       …
#     </ul>
#   </div>
#
# Внутри outline-part могут быть вложенные div'ы (sub-chapters и т.п.),
# поэтому простой ленивый regex не годится — нужен баланс открывающих и
# закрывающих <div>. Парсим через ручной проход.

OUTLINE_PART_OPEN_RE = re.compile(r'<div\s+class="outline-part"\s*>')
DIV_OPEN_RE = re.compile(r'<div\b', re.IGNORECASE)
DIV_CLOSE_RE = re.compile(r'</div\s*>', re.IGNORECASE)

OUTLINE_PART_TITLE_RE = re.compile(
    r'<div\s+class="outline-part-title"[^>]*>(.*?)</div>',
    re.DOTALL,
)
OUTLINE_PART_CHAPTER_RE = re.compile(
    r'href="(?:\.\./)?chapters/(\d{2})-[^"]+\.html"'
)

# Структура toc-part (фоллбэк):
#   <div class="toc-part">Введение</div>
#   <ol …>
#     <li><a href="chapters/NN-slug.html">…</a></li>
#     …
#   </ol>

TOC_PART_BLOCK_RE = re.compile(
    r'<div\s+class="toc-part">([^<]*)</div>\s*<ol[^>]*>(.*?)</ol>',
    re.DOTALL,
)
TOC_PART_CHAPTER_RE = re.compile(
    r'href="(?:\.\./)?chapters/(\d{2})-[^"]+\.html"'
)


def find_balanced_div_block(text: str, start: int) -> int | None:
    """Считая, что в позиции start стоит символ сразу после открывающего
    тега <div ...>, возвращает индекс символа сразу после соответствующего
    закрывающего </div>. Если баланс не сходится — None.

    Стартовая глубина = 1, потому что вызывающий код уже прошёл
    открывающий тег — мы внутри одной открытой группы."""
    pos = start
    depth = 1
    length = len(text)
    while pos < length:
        m_open = DIV_OPEN_RE.search(text, pos)
        m_close = DIV_CLOSE_RE.search(text, pos)
        if not m_close:
            return None
        if m_open and m_open.start() < m_close.start():
            depth += 1
            pos = m_open.end()
        else:
            depth -= 1
            pos = m_close.end()
            if depth == 0:
                return pos
    return None


def strip_html_tags(html: str) -> str:
    """Аккуратно удаляет HTML-теги и нормализует пробелы.
    Не претендует на полноту парсера: для названий частей достаточно."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# Римские числа для названий частей в титульной вставке.
# Книга вмещается в I–XX, дальше расширим при необходимости.
ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
        'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX']


def split_part_title(raw: str) -> tuple[str, str]:
    """Разбирает строку названия части на префикс (например, «I») и собственно
    название. Принимает строки вида «I. Профессия и процессы», «Часть I · ...»,
    «Введение», «Приложение». Возвращает (roman_or_empty, name).

    Разделители между римским номером и названием — любая комбинация из
    точек, пробелов и точек-разделителей «·» (один или больше подряд).

    Примеры:
        "I. Профессия и процессы"  → ("I",   "Профессия и процессы")
        "Часть III · Моделирование" → ("III", "Моделирование")
        "Часть III"                → ("III", "")
        "Введение"                 → ("",    "Введение")
    """
    s = raw.strip()

    # «I. Название» или «I Название» или «I · Название» — допускаем
    # несколько символов-разделителей подряд.
    m = re.match(r'^([IVX]+)[.\s·]+(.+)$', s)
    if m:
        return m.group(1), m.group(2).strip()

    # «Часть I» / «Часть I. Название» / «Часть I · Название»
    m = re.match(r'^Часть\s+([IVX]+)(?:[.\s·]+(.+))?$', s, re.IGNORECASE)
    if m:
        roman = m.group(1)
        name = m.group(2).strip() if m.group(2) else ''
        return roman, name

    # Просто римское число
    m = re.match(r'^([IVX]+)$', s)
    if m:
        return m.group(1), ''

    # Без номера — служебная часть («Введение», «Приложение»)
    return '', s


def parse_parts_from_outline(index_html: str) -> list[dict]:
    """Возвращает список частей из раздела «Содержание» index.html.
    Каждый элемент: {'roman': str, 'name': str, 'chapters': [str, ...]}.
    Главы — двузначные номера, в порядке появления в части.
    Пустой список — если разметка outline-part не найдена.

    Парсинг устойчив к вложенным div'ам внутри outline-part: используется
    баланс открывающих и закрывающих тегов <div>, а не regex поверх
    вложенных структур."""
    parts = []
    pos = 0
    while True:
        m = OUTLINE_PART_OPEN_RE.search(index_html, pos)
        if not m:
            break
        # m.start() — начало открывающего <div ...>
        # m.end()   — символ сразу после открывающего тега
        end = find_balanced_div_block(index_html, m.end())
        if end is None:
            # Не удалось найти закрытие — обрываем
            break
        block = index_html[m.end():end]  # содержимое внутри outline-part
        # Сдвигаем позицию за закрывающий </div>
        pos = end

        title_m = OUTLINE_PART_TITLE_RE.search(block)
        if not title_m:
            continue
        raw_title = strip_html_tags(title_m.group(1))
        roman, name = split_part_title(raw_title)
        chapter_nums = OUTLINE_PART_CHAPTER_RE.findall(block)
        if chapter_nums:
            parts.append({'roman': roman, 'name': name, 'chapters': chapter_nums})
    return parts


def parse_parts_from_toc(index_html: str) -> list[dict]:
    """Фоллбэк: парсит части из TOC-GLOBAL (toc-part + ol).
    Применяется, если outline-part отсутствует или не дал результата."""
    toc = extract_between(index_html, *TOC_GLOBAL_MARKER)
    if toc is None:
        return []
    parts = []
    for m in TOC_PART_BLOCK_RE.finditer(toc):
        raw_title = m.group(1).strip()
        block = m.group(2)
        roman, name = split_part_title(raw_title)
        chapter_nums = TOC_PART_CHAPTER_RE.findall(block)
        if chapter_nums:
            parts.append({'roman': roman, 'name': name, 'chapters': chapter_nums})
    return parts


def parse_parts(index_html: str) -> list[dict]:
    """Возвращает список частей. Приоритет — outline-part; если не нашли —
    фоллбэк на toc-part. Из результата исключаются служебные части без
    римского номера (например, «Введение», «Приложение») — для них
    титульной вставки не делаем."""
    parts = parse_parts_from_outline(index_html)
    if not parts:
        parts = parse_parts_from_toc(index_html)
    # Оставляем только пронумерованные части.
    return [p for p in parts if p['roman']]


def render_part_title(part: dict) -> str:
    """Формирует HTML титульной вставки части."""
    roman = part['roman']
    name = part['name']
    name_html = f'<span class="name">{name}</span>' if name else ''
    return (
        f'<section class="part-title" aria-label="Часть {roman}">\n'
        f'  <span class="eyebrow">Часть {roman}</span>\n'
        f'  <span class="roman">{roman}</span>\n'
        f'  {name_html}\n'
        f'</section>'
    )


def build_chapter_to_part_map(parts: list[dict]) -> dict[str, dict]:
    """Сопоставляет каждому номеру главы её часть. Для главы, открывающей
    часть, она будет первой в parts[i]['chapters'][0]."""
    mapping = {}
    for part in parts:
        for ch_num in part['chapters']:
            mapping[ch_num] = part
    return mapping


# ────────────────────────────────────────────────────────────
# Основная сборка
# ────────────────────────────────────────────────────────────

def build() -> int:
    if not STYLES.exists():
        sys.exit(f"Не найден {STYLES}")
    css = read_text(STYLES)

    if not INDEX.exists():
        sys.exit(f"Не найден {INDEX}")
    index_html = read_text(INDEX)

    index_content = extract_between(index_html, *INDEX_MARKER)
    if index_content is None:
        sys.exit("В index.html не найдены маркеры INDEX-CONTENT")

    toc_global = extract_between(index_html, *TOC_GLOBAL_MARKER)
    if toc_global is None:
        sys.exit("В index.html не найдены маркеры TOC-GLOBAL-INCLUDE")

    # Разбираем части книги. Используется для титульных вставок и для
    # понимания, какая глава первая в своей части.
    parts = parse_parts(index_html)
    chapter_to_part = build_chapter_to_part_map(parts)
    if not parts:
        print("⚠ В index.html не нашёл размеченных частей (outline-part / toc-part)."
              " Титульные вставки не будут добавлены.")

    chapter_files = get_chapter_files()
    chapter_filenames = [f.name for f in chapter_files]
    if not chapter_files:
        print("⚠ В chapters/ нет файлов глав. Собирается только index.")

    chapters_html_parts = []
    toc_local_parts = []
    inserted_part_romans: set[str] = set()

    for f in chapter_files:
        text = read_text(f)
        content = extract_between(text, *CHAPTER_MARKER)
        if content is None:
            print(f"  ⚠ В {f.name} нет CHAPTER-CONTENT — пропускаю")
            continue

        num_match = re.match(r"(\d{2})-", f.name)
        if not num_match:
            print(f"  ⚠ Не могу извлечь номер из {f.name} — пропускаю")
            continue
        num = num_match.group(1)

        # Если глава открывает часть — вставляем перед ней титульную вставку.
        part = chapter_to_part.get(num)
        if part and part['roman'] and part['roman'] not in inserted_part_romans:
            chapters_html_parts.append(render_part_title(part))
            inserted_part_romans.add(part['roman'])

        content = wrap_chapter_with_anchor(content, num)
        chapters_html_parts.append(content)

        # Собираем toc-local главы — он окажется в правой колонке книги.
        toc_local = extract_toc_local(text)
        if toc_local:
            tagged = attach_chapter_to_toc_local(toc_local, num)
            toc_local_parts.append(tagged)
        else:
            print(f"  ⚠ В {f.name} нет TOC-LOCAL — правая колонка для этой главы будет пустой")

        print(f"  ✓ {f.name}")

    chapters_html = "\n\n".join(chapters_html_parts)
    full_main_content = index_content + "\n\n" + chapters_html
    full_main_content = transform_chapter_links(full_main_content, chapter_filenames)
    toc_global_transformed = transform_chapter_links(toc_global, chapter_filenames)

    # Хост-контейнер для toc-local. Один на всю книгу, внутри — по блоку
    # на главу. JS включает активный по текущей главе. Используем <div>,
    # чтобы не вкладывать <aside> в <aside> (это валидно, но шумно).
    if toc_local_parts:
        toc_local_host = (
            '<div class="toc-local-host">\n'
            + "\n".join(toc_local_parts)
            + '\n</div>'
        )
    else:
        toc_local_host = ''

    result = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Системный анализ: карманный справочник</title>
<style>
{css}
</style>
</head>
<body id="top">

<div class="layout">

{toc_global_transformed}

<main>

{full_main_content}

</main>

{toc_local_host}

</div>

<a href="#top" class="back-to-top" aria-label="Наверх">↑</a>

<script>
// Подсветка текущей главы в TOC и переключение правой колонки
// (локального оглавления) на главу, в которой сейчас читатель.
(function() {{
  const chapters = document.querySelectorAll('article.chapter[id^="ch-"]');
  if (!chapters.length) return;

  // Карта: anchor → ссылка в глобальном TOC
  const tocGlobalLinks = new Map();
  document.querySelectorAll('.toc-global a[href^="#ch-"]').forEach(a => {{
    const anchor = a.getAttribute('href').slice(1);
    tocGlobalLinks.set(anchor, a);
  }});

  // Карта: chapter_num → блок toc-local в хосте
  const tocLocalBlocks = new Map();
  document.querySelectorAll('.toc-local-host .toc-local[data-chapter]').forEach(block => {{
    tocLocalBlocks.set(block.dataset.chapter, block);
  }});

  let currentChapterAnchor = null;

  function setCurrentChapter(anchor) {{
    if (anchor === currentChapterAnchor) return;
    // глобальный TOC
    if (currentChapterAnchor && tocGlobalLinks.has(currentChapterAnchor)) {{
      tocGlobalLinks.get(currentChapterAnchor).classList.remove('is-current');
    }}
    if (anchor && tocGlobalLinks.has(anchor)) {{
      tocGlobalLinks.get(anchor).classList.add('is-current');
    }}
    // переключение активного toc-local в хосте
    const num = anchor ? anchor.replace('ch-', '') : null;
    tocLocalBlocks.forEach((block, key) => {{
      block.classList.toggle('is-active', key === num);
    }});
    currentChapterAnchor = anchor;
  }}

  const chapterObserver = new IntersectionObserver(entries => {{
    const visible = entries
      .filter(e => e.isIntersecting)
      .map(e => e.target);
    if (!visible.length) return;
    visible.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
    const top = visible[0];
    if (top.id) setCurrentChapter(top.id);
  }}, {{
    rootMargin: '-20% 0px -60% 0px',
    threshold: 0
  }});
  chapters.forEach(ch => chapterObserver.observe(ch));

  // Подсветка текущей темы в активном toc-local.
  // Целевые элементы — это section'ы с id, на которые есть ссылки в toc-local.
  // Собираем все целевые id из всех toc-local блоков.
  const localLinks = new Map(); // section_id → элемент-ссылка
  document.querySelectorAll('.toc-local-host .toc-local a[href^="#"]').forEach(a => {{
    const id = a.getAttribute('href').slice(1);
    if (id) localLinks.set(id, a);
  }});

  // Стандалонный toc-local (в отдельных файлах глав, без хоста) — тоже учтём.
  document.querySelectorAll('aside.toc-local:not(.toc-local-host *) a[href^="#"]').forEach(a => {{
    const id = a.getAttribute('href').slice(1);
    if (id && !localLinks.has(id)) localLinks.set(id, a);
  }});

  let currentSection = null;
  function setCurrentSection(id) {{
    if (id === currentSection) return;
    if (currentSection && localLinks.has(currentSection)) {{
      localLinks.get(currentSection).classList.remove('is-current');
    }}
    if (id && localLinks.has(id)) {{
      localLinks.get(id).classList.add('is-current');
    }}
    currentSection = id;
  }}

  if (localLinks.size) {{
    const sectionTargets = [];
    localLinks.forEach((_link, id) => {{
      const el = document.getElementById(id);
      if (el) sectionTargets.push(el);
    }});
    const sectionObserver = new IntersectionObserver(entries => {{
      const visible = entries
        .filter(e => e.isIntersecting)
        .map(e => e.target);
      if (!visible.length) return;
      visible.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
      const top = visible[0];
      if (top.id) setCurrentSection(top.id);
    }}, {{
      rootMargin: '-15% 0px -70% 0px',
      threshold: 0
    }});
    sectionTargets.forEach(s => sectionObserver.observe(s));
  }}
}})();
</script>

</body>
</html>
"""

    write_text(OUTPUT, result)
    print(f"\n✓ Готово: {OUTPUT.name}")
    print(f"  Размер: {OUTPUT.stat().st_size // 1024} КБ")
    print(f"  Глав в сборке: {sum(1 for p in chapters_html_parts if '<article class=\"chapter\"' in p)}")
    if inserted_part_romans:
        print(f"  Титульных вставок частей: {len(inserted_part_romans)}")
    return 0


# ────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(build())
    cmd = args[0]
    if cmd in ("--sync-toc", "sync-toc"):
        sys.exit(sync_toc())
    if cmd in ("--check-toc-sync", "check-toc-sync"):
        sys.exit(sync_toc(check_only=True))
    if cmd in ("--check", "check"):
        sys.exit(run_checks())
    if cmd in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0)
    sys.exit(f"Неизвестная команда: {cmd}. Используйте --help.")


if __name__ == "__main__":
    main()

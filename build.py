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
    python3 build.py --check           — проверить HTML на баланс тегов и наличие маркеров

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

    chapter_files = get_chapter_files()
    chapter_filenames = [f.name for f in chapter_files]
    if not chapter_files:
        print("⚠ В chapters/ нет файлов глав. Собирается только index.")

    chapters_html_parts = []
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

        content = wrap_chapter_with_anchor(content, num)
        chapters_html_parts.append(content)
        print(f"  ✓ {f.name}")

    chapters_html = "\n\n".join(chapters_html_parts)
    full_main_content = index_content + "\n\n" + chapters_html
    full_main_content = transform_chapter_links(full_main_content, chapter_filenames)
    toc_global_transformed = transform_chapter_links(toc_global, chapter_filenames)

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
<body>

<div class="layout">

{toc_global_transformed}

<main>

{full_main_content}

</main>

</div>

<a href="#top" class="back-to-top" aria-label="Наверх">↑</a>

<script>
// Подсветка текущей главы в TOC при прокрутке.
// Использует IntersectionObserver — следит, какая <article class="chapter">
// сейчас в зоне видимости, и помечает соответствующую ссылку TOC.
(function() {{
  const chapters = document.querySelectorAll('article.chapter[id^="ch-"]');
  if (!chapters.length) return;

  const tocLinks = new Map();
  document.querySelectorAll('.toc-global a[href^="#ch-"]').forEach(a => {{
    const anchor = a.getAttribute('href').slice(1);
    tocLinks.set(anchor, a);
  }});
  if (!tocLinks.size) return;

  let currentAnchor = null;
  function setCurrent(anchor) {{
    if (anchor === currentAnchor) return;
    if (currentAnchor && tocLinks.has(currentAnchor)) {{
      tocLinks.get(currentAnchor).classList.remove('is-current');
    }}
    if (anchor && tocLinks.has(anchor)) {{
      tocLinks.get(anchor).classList.add('is-current');
    }}
    currentAnchor = anchor;
  }}

  const observer = new IntersectionObserver(entries => {{
    const visible = entries
      .filter(e => e.isIntersecting)
      .map(e => e.target);
    if (!visible.length) return;
    visible.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
    const top = visible[0];
    if (top.id) setCurrent(top.id);
  }}, {{
    rootMargin: '-20% 0px -60% 0px',
    threshold: 0
  }});

  chapters.forEach(ch => observer.observe(ch));
}})();
</script>

</body>
</html>
"""

    write_text(OUTPUT, result)
    print(f"\n✓ Готово: {OUTPUT.name}")
    print(f"  Размер: {OUTPUT.stat().st_size // 1024} КБ")
    print(f"  Глав в сборке: {len(chapters_html_parts)}")
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

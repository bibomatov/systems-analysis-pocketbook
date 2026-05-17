# Системный анализ: карманный справочник

Открытый русскоязычный справочник по системному анализу. Создан для развития профессии в России — для двух близких, но различимых читателей: junior-аналитика с опытом около года, который стремится стать middle, и middle, который систематизирует знания и закрывает пробелы в системной картине профессии.

Восемь частей, двадцать глав.

## Читать книгу

- **Онлайн:** [bibomatov.github.io/systems-analysis-pocketbook](https://bibomatov.github.io/systems-analysis-pocketbook/)
- **Редакционный стандарт:** [bibomatov.github.io/systems-analysis-pocketbook/meta/editorial-standard.html](https://bibomatov.github.io/systems-analysis-pocketbook/meta/editorial-standard.html)
- **Локально:** открыть `index.html` или собранный `pocket-book.html` в браузере

## Структура репозитория

```
pocket-book-sa/
├── styles.css                  # Единые стили для книги и meta-документов
├── index.html                  # Главная: hero, миссия, оглавление (эталон TOC)
├── chapters/                   # Главы — один файл на главу
│   ├── 00-intro.html           # Введение
│   ├── 01-role.html
│   ├── 02-sdlc.html
│   └── ...                     # всего 20 глав
├── meta/                       # Документы о книге, НЕ являются её частью
│   ├── editorial-standard.html # Редакционный стандарт
│   └── project-instructions.md # Инструкции для AI-ассистента
├── assets/svg/                 # SVG-исходники (34 готовых + новые при написании глав)
├── .github/workflows/          # GitHub Actions: автосборка и публикация
├── build.py                    # Скрипт сборки и валидации
├── glossary.html               # Глоссарий, растёт параллельно с главами
├── pocket-book.html            # Финальный собранный файл (в .gitignore)
├── README.md
├── CONTRIBUTING.md
├── LICENSE                     # CC BY 4.0
└── .gitignore
```

## Разделение «книга» и «документы о книге»

- **Файлы книги:** `index.html`, `chapters/*.html`, `glossary.html`, `styles.css`. Эти файлы попадают в собранный `pocket-book.html` и публикуются на сайте.
- **Файлы о книге** (`meta/`): редстандарт, инструкции, рабочие документы. Они **не входят** в собранную книгу — это инструменты для авторов и редакторов.

## Как редактировать главы

Главы — самостоятельные HTML-файлы в `chapters/`. Структура каждой:

```html
<!DOCTYPE html>
<html>
<head><link rel="stylesheet" href="../styles.css"></head>
<body>
  <div class="layout">
    <!-- TOC-GLOBAL-INCLUDE -->
    <aside class="toc-global">...</aside>
    <!-- /TOC-GLOBAL-INCLUDE -->

    <main>
      <!-- CHAPTER-CONTENT-START -->
      <article class="chapter" data-chapter="01">
        <header class="chapter-header">...</header>
        <section id="ch01-topic-1">...</section>
        ...
      </article>
      <!-- CHAPTER-CONTENT-END -->
    </main>

    <!-- TOC-LOCAL-INCLUDE -->
    <aside class="toc-local">...</aside>
    <!-- /TOC-LOCAL-INCLUDE -->
  </div>
</body>
</html>
```

**Маркеры комментариев** — служебные. Не удалять, не переименовывать: скрипт сборки извлекает по ним контент.

При редактировании содержания трогаем **только** блок между `CHAPTER-CONTENT-START` и `CHAPTER-CONTENT-END`. Глобальное оглавление синхронизируется автоматически — см. ниже.

## Скрипт сборки

```bash
python3 build.py              # Собрать pocket-book.html
python3 build.py --check      # Проверить HTML на баланс тегов и маркеры
python3 build.py --sync-toc   # Синхронизировать глобальный TOC во всех главах
```

Нужен Python 3.10+ без сторонних зависимостей.

### Когда нужен `--sync-toc`

Глобальный TOC живёт в `index.html` как единственный источник правды. При добавлении новой главы, переименовании главы или изменении порядка достаточно:
1. Поправить TOC в `index.html`
2. Запустить `python3 build.py --sync-toc`
3. Скрипт обновит блок `TOC-GLOBAL-INCLUDE` во всех файлах `chapters/*.html`

### Когда нужен `--check`

Перед коммитом, чтобы не отправить в репо HTML с непарными тегами или без обязательных маркеров. CI запускает `--check` автоматически перед сборкой — это страхует от выкладывания сломанной версии.

## Автосборка через GitHub Actions

Изменения попадают в `main` через pull request — прямой push в `main` закрыт защитой ветки. При каждом merge PR в `main` запускается workflow `.github/workflows/build-and-deploy.yml`:
1. `python3 build.py --check` — валидация
2. `python3 build.py` — сборка `pocket-book.html`
3. Подготовка артефактов для Pages (книга + meta-документы + стили)
4. Деплой на GitHub Pages

Тот же workflow в режиме проверки запускается на каждом PR — это страхует `main` от попадания сломанной сборки.

## Настройка GitHub Pages (одноразово)

1. **Settings → Pages**
2. **Source:** GitHub Actions
3. Дождаться workflow (~1 минута после первого push)
4. Книга доступна по адресу `https://bibomatov.github.io/systems-analysis-pocketbook/`
5. Редстандарт — `https://bibomatov.github.io/systems-analysis-pocketbook/meta/editorial-standard.html`

## Соглашение по ID и якорям

Чтобы избежать конфликтов идентификаторов между главами:

| Сущность | Формат | Пример |
|---|---|---|
| Файл главы | `chapters/NN-slug.html` | `chapters/04-functional-requirements.html` |
| ID главы (article) | `ch-NN` | `id="ch-04"` |
| ID темы (section) | `ch{NN}-{slug}` | `id="ch04-user-stories"` |
| ID подраздела | `ch{NN}-sub-{slug}` | `id="ch04-sub-formalization"` |
| ID статьи глоссария | `gloss-{term}` | `id="gloss-idempotency"` |

Slug — короткий, латиницей, через дефис, без подчёркиваний.

## Дизайн-система

Все стили — в `styles.css`. Файл используется и книгой, и meta-документами.

- **Фон:** тёплый off-white `#f7f6f3`
- **Текст:** тёмно-серый `#1a1917`
- **Шрифты:** IBM Plex Sans (основной), IBM Plex Serif (заголовки), IBM Plex Mono (код)
- **Семантические акценты:** четыре цвета — определение, рекомендация, антипаттерн, важно

Подробное описание принципов и компонентов — в [`meta/editorial-standard.html`](meta/editorial-standard.html).

## Авторы

- Руслан Бибоматов — автор и редактор
- AI-ассистент используется автором для технической поддержки в написании и ревью

## Лицензия

Книга распространяется свободно. Копирование, использование в обучении, цитирование с указанием источника — разрешены.

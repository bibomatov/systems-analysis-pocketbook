# Шрифты IBM Plex

Файлы шрифтов хранятся локально в этой папке — это снимает зависимость от Google Fonts
и позволяет читать книгу оффлайн.

## Что положить сюда

Нужны 7 файлов в формате `.woff2` со следующими именами:

```
IBMPlexSans-Regular.woff2
IBMPlexSans-Medium.woff2
IBMPlexSans-SemiBold.woff2
IBMPlexSerif-Regular.woff2
IBMPlexSerif-Italic.woff2
IBMPlexMono-Regular.woff2
IBMPlexMono-Medium.woff2
```

Это минимально достаточный набор начертаний: только те, что реально используются
в `styles.css`. Остальные веса и стили не нужны.

## Откуда брать

Официальный репозиторий IBM Plex: https://github.com/IBM/plex

Прямые пути к нужным файлам (ветка `master`):

- `IBM-Plex-Sans/fonts/complete/woff2/IBMPlexSans-Regular.woff2`
- `IBM-Plex-Sans/fonts/complete/woff2/IBMPlexSans-Medium.woff2`
- `IBM-Plex-Sans/fonts/complete/woff2/IBMPlexSans-SemiBold.woff2`
- `IBM-Plex-Serif/fonts/complete/woff2/IBMPlexSerif-Regular.woff2`
- `IBM-Plex-Serif/fonts/complete/woff2/IBMPlexSerif-Italic.woff2`
- `IBM-Plex-Mono/fonts/complete/woff2/IBMPlexMono-Regular.woff2`
- `IBM-Plex-Mono/fonts/complete/woff2/IBMPlexMono-Medium.woff2`

Общий вес — около 250 КБ.

## Лицензия

IBM Plex распространяется под SIL Open Font License 1.1. Свободно для коммерческого
и некоммерческого использования, включая встраивание и распространение в составе
проектов. Текст лицензии — в репозитории IBM/plex.

## Если шрифтов нет

Книга загрузится с системными запасными шрифтами (`sans-serif`, `Georgia`, `monospace`).
Внешний вид будет грубее, но читаемость сохранится. CI не проверяет наличие шрифтов —
сборка пройдёт без них.

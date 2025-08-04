# B2B-Center Parser

Асинхронный парсер тендеров с сайта B2B-Center.

## Установка

```bash
pip install -r requirements.txt
```

## Использование

```bash
# CLI
python main.py --max 100 --output tenders.db

# API
python api.py
curl "http://localhost:8000/tenders?max_tenders=10"
```

## Параметры

- `--max` - количество тендеров (по умолчанию: 100)
- `--output` - файл для сохранения
- `--format` - формат (json/sqlite)

## Форматы

- JSON - `tenders.json`
- SQLite - `tenders.db`

## Особенности

- **Асинхронность** - загружает 5 страниц одновременно
- **Высокая скорость** - в 5 раз быстрее обычного парсера
- **Обработка ошибок** - продолжает работу при сбоях 
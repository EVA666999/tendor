"""
CLI парсер для загрузки тендеров с сайта B2B-Center.
"""

import argparse
import asyncio
import json
import sqlite3
import sys
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup


@dataclass
class Tender:
    """Модель данных тендера."""
    title: str
    company: str
    date_created: str
    date_deadline: str
    url: str
    category: Optional[str] = None
    description: Optional[str] = None


class B2BCenterParser:
    """Асинхронный парсер для сайта B2B-Center."""

    def __init__(self):
        self.base_url = "https://www.b2b-center.ru/market"
        self.headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36')
        }

    async def get_tenders(self, limit: int = 100) -> List[Tender]:
        """Асинхронно загружает тендеры с сайта."""
        tenders = []
        page = 1
        max_concurrent = 5

        async with aiohttp.ClientSession(headers=self.headers) as session:
            while len(tenders) < limit:
                pages_range = f"{page}-{page + max_concurrent - 1}"
                print(f"Загружаю страницы {pages_range}...")

                tasks = []
                for i in range(max_concurrent):
                    if len(tenders) >= limit:
                        break
                    current_page = page + i
                    task = self._fetch_page(session, current_page)
                    tasks.append(task)

                if not tasks:
                    break

                results = await asyncio.gather(*tasks, return_exceptions=True)

                page_has_data = False
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        print(f"Ошибка на странице {page + i}: {result}")
                        continue

                    if result:
                        page_has_data = True
                        for tender in result:
                            if len(tenders) < limit:
                                tenders.append(tender)
                            else:
                                break

                if not page_has_data:
                    print("Достигнут конец списка тендеров")
                    break

                page += max_concurrent

        return tenders

    async def _fetch_page(self, session: aiohttp.ClientSession,
                          page: int) -> Optional[List[Tender]]:
        """Загружает одну страницу с тендерами."""
        try:
            url = (self.base_url if page == 1
                   else f"{self.base_url}?page={page}")

            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    print(f"HTTP {response.status} для страницы {page}")
                    return None

                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                tender_rows = soup.find_all('tr')
                page_tenders = []

                for row in tender_rows:
                    tender = self._parse_tender_row(row)
                    if tender:
                        page_tenders.append(tender)

                print(f"На странице {page} найдено {len(page_tenders)} тендеров")
                return page_tenders

        except Exception as e:
            print(f"Ошибка при загрузке страницы {page}: {type(e).__name__}: {e}")
            return None

    def _parse_tender_row(self, row) -> Optional[Tender]:
        """Парсит строку таблицы с тендером."""
        try:
            cells = row.find_all('td')
            if len(cells) < 4:
                return None

            first_cell = cells[0]

            category_elem = first_cell.find('small')
            category = (category_elem.get_text(strip=True)
                        if category_elem else None)

            title_elem = first_cell.find('a', class_='search-results-title')
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            url = ("https://www.b2b-center.ru" + title_elem['href']
                   if title_elem.get('href') else "")

            desc_elem = first_cell.find('div', class_='search-results-title-desc')
            description = desc_elem.get_text(strip=True) if desc_elem else None

            company_elem = cells[1].find('a')
            company = (company_elem.get_text(strip=True)
                        if company_elem else "Не указана")

            date_created = cells[2].get_text(strip=True)
            date_deadline = cells[3].get_text(strip=True)

            return Tender(
                title=title,
                company=company,
                date_created=date_created,
                date_deadline=date_deadline,
                url=url,
                category=category,
                description=description
            )

        except Exception:
            return None

    def save_to_json(self, tenders: List[Tender],
                     filename: str = "tenders.json"):
        """Сохраняет тендеры в JSON файл."""
        import os

        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"Удален старый файл {filename}")
            except Exception as e:
                print(f"Ошибка при удалении файла: {e}")

        data = []
        for tender in tenders:
            data.append({
                'title': tender.title,
                'company': tender.company,
                'date_created': tender.date_created,
                'date_deadline': tender.date_deadline,
                'url': tender.url,
                'category': tender.category,
                'description': tender.description
            })

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Сохранено {len(tenders)} тендеров в файл {filename}")

    def save_to_sqlite(self, tenders: List[Tender],
                       filename: str = "tenders.db"):
        """Сохраняет тендеры в SQLite базу данных."""
        import os

        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"Удалена старая база данных {filename}")
            except Exception as e:
                print(f"Ошибка при удалении базы данных: {e}")

        conn = sqlite3.connect(filename)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                date_created TEXT NOT NULL,
                date_deadline TEXT NOT NULL,
                category TEXT,
                url TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        for tender in tenders:
            cursor.execute('''
                INSERT INTO tenders (title, company, date_created,
                                    date_deadline, category, url, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                tender.title,
                tender.company,
                tender.date_created,
                tender.date_deadline,
                tender.category,
                tender.url,
                tender.description
            ))

        conn.commit()
        conn.close()

        print(f"Сохранено {len(tenders)} тендеров в SQLite базу данных "
              f"{filename}")


def main():
    """Основная функция CLI."""
    parser = argparse.ArgumentParser(
        description='Парсер тендеров с сайта B2B-Center'
    )

    parser.add_argument('--max', type=int, default=100,
                        help='Максимальное количество тендеров (по умолчанию: 100)')
    parser.add_argument('--output', type=str, default='tenders.json',
                        help='Файл для сохранения результатов (по умолчанию: tenders.json)')
    parser.add_argument('--format', choices=['json', 'sqlite'], default='json',
                        help='Формат выходного файла (по умолчанию: json)')

    args = parser.parse_args()

    if args.output.endswith('.db'):
        args.format = 'sqlite'
    elif args.output.endswith('.json'):
        args.format = 'json'

    print(f"Загружаю {args.max} тендеров в формате {args.format}...")
    print(f"Файл: {args.output}")

    asyncio.run(run_parser(args))


async def run_parser(args):
    """Запускает парсер с заданными параметрами."""
    parser = B2BCenterParser()

    try:
        tenders = await parser.get_tenders(limit=args.max)

        if args.format == 'sqlite':
            parser.save_to_sqlite(tenders, args.output)
        else:
            parser.save_to_json(tenders, args.output)

        print(f"Успешно загружено {len(tenders)} тендеров")

    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
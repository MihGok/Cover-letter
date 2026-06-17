"""
hh_fetcher.py
─────────────
Адаптер для получения данных вакансий с HH.ru.
Парсит HTML страницы вместо API (который блокирован VPN).
"""

import re
import logging
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Константы ─────────────────────────────────────────────────────────────

_HH_BASE = "https://hh.ru"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# ── Публичный API ──────────────────────────────────────────────────────────

async def fetch_vacancy_from_url(url: str) -> str:
    """
    Получить текст вакансии по URL HH.ru (парсит HTML).

    Поддерживаемые форматы URL:
      https://hh.ru/vacancy/12345678
      https://hh.ru/vacancy/12345678?query=...

    Returns:
        Форматированный plain text вакансии.

    Raises:
        ValueError: если не удалось извлечь vacancy_id или распарсить содержимое.
        httpx.HTTPError: при ошибке запроса.
    """
    vacancy_id = _extract_vacancy_id(url)
    if not vacancy_id:
        raise ValueError(
            f"Не удалось извлечь ID вакансии из URL: {url!r}\n"
            f"Ожидаемый формат: https://hh.ru/vacancy/12345678"
        )

    page_url = f"{_HH_BASE}/vacancy/{vacancy_id}"
    logger.info("Fetching vacancy page | url=%s", page_url)
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(page_url, headers=_HEADERS)
        resp.raise_for_status()
        html = resp.text

    result = _parse_vacancy_html(html)
    logger.info("Vacancy parsed | vacancy_id=%s | length=%d", vacancy_id, len(result))
    return result


def clean_manual_text(text: str) -> str:
    """
    Нормализовать текст, введённый вручную.
    Убирает лишние пробелы, нормализует переносы строк.
    """
    lines = [line.strip() for line in text.splitlines()]
    result, blank_count = [], 0
    for line in lines:
        if not line:
            blank_count += 1
            if blank_count <= 2:
                result.append("")
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result).strip()


# ── Вспомогательные ───────────────────────────────────────────────────────

def _extract_vacancy_id(url: str) -> str | None:
    """Извлечь числовой ID вакансии из URL HH.ru."""
    match = re.search(r'/vacancy/(\d+)', url)
    return match.group(1) if match else None


def _strip_html(html: str) -> str:
    """Убрать HTML-теги, сохранив структуру текста."""
    soup = BeautifulSoup(html, "html.parser")
    for li in soup.find_all("li"):
        li.insert_before("• ")
        li.append("\n")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for div in soup.find_all(["div", "p"]):
        div.append("\n")
    text = soup.get_text(separator="\n")
    # Убираем множественные пустые строки
    lines = [line.rstrip() for line in text.split("\n")]
    lines = [l for l in lines if l.strip()]
    return "\n".join(lines)


def _parse_vacancy_html(html: str) -> str:
    """Парсить HTML страницу вакансии и вернуть полный текст."""
    soup = BeautifulSoup(html, "html.parser")
    parts: list[str] = []

    # Попытка 1: найти заголовок по data-qa
    title_elem = soup.find("h1", {"data-qa": "vacancy-title"})
    if not title_elem:
        # Попытка 2: просто первый h1
        title_elem = soup.find("h1")
    
    if title_elem:
        title = title_elem.get_text(strip=True)
        if title:
            parts.append(f"=== {title} ===")
            parts.append("")

    # Описание вакансии — основной контент
    # Попытка 1: data-qa
    desc_elem = soup.find("div", {"data-qa": "vacancy-description"})
    if not desc_elem:
        # Попытка 2: поиск по классам
        desc_elem = soup.find("div", {"class": re.compile(r".*description.*", re.I)})
    if not desc_elem:
        # Попытка 3: найти самый большой div в main
        main = soup.find("main")
        if main:
            divs = main.find_all("div", recursive=True)
            divs_with_text = [(d, len(d.get_text())) for d in divs if len(d.get_text()) > 500]
            if divs_with_text:
                desc_elem = max(divs_with_text, key=lambda x: x[1])[0]

    if desc_elem:
        desc_text = _strip_html(str(desc_elem))
        if desc_text.strip():
            parts.append(desc_text)

    result = "\n".join(parts).strip()
    
    if not result or len(result) < 50:
        logger.warning("Parsed vacancy is too short or empty | length=%d", len(result))
        # Fallback: весь текст страницы
        result = _strip_html(html)
    
    return result

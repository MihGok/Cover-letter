"""
llm_gateway.py
──────────────
HTTP-клиент для обращения к локальному LLM-эндпоинту (Docker).

Эндпоинт принимает task_type="llm" и возвращает dict с ключом "result".
Этот модуль:
  - строит payload для эндпоинта
  - парсит JSON из ответа модели (с несколькими fallback-стратегиями)
  - отличает режим JSON (этапы 2–4) от plain text (этап 5 — письмо)
"""

import json
import re
import logging
import httpx
from typing import Any

from config import LLM_ENDPOINT_URL, MODEL_NAME, LLM_TIMEOUT

logger = logging.getLogger(__name__)


# ── Публичный API ──────────────────────────────────────────────────────────

async def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    schema_name: str | None = None, # Теперь это строка, например "vacancy_analysis"
) -> dict:
    """
    Отправляет запрос на ML-бэкенд для генерации структурированного JSON.
    """
    payload = {
        "task_type": "llm",
        "model_name": "Q8_0.gguf",    
        "text": user_prompt,
        "system_prompt": system_prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "schema_name": schema_name,
        "enable_thinking": False,
        "n_ctx": 16384
    }
    
    headers = {"Content-Type": "application/json"}
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(LLM_ENDPOINT_URL, json=payload, headers=headers)
            
            # Если 422 - логируем ответ, чтобы увидеть, какое поле FastAPI отклонил
            if response.status_code == 422:
                logger.error("Validation Error Details: %s", response.json())
                
            response.raise_for_status()
            response_data = response.json()
            
            # Возвращаем поле 'result', как определено в main.py[cite: 4]
            return response_data.get("result", response_data)
            
        except httpx.HTTPStatusError as exc:
            logger.error("Ошибка HTTP: %s | Response: %s", exc, exc.response.text)
            raise
        except Exception as exc:
            logger.error("Ошибка вызова call_llm_json: %s", exc)
            raise


async def call_llm_text(
    system_prompt: str,
    user_prompt:   str,
    max_tokens:    int   = 2048,
    temperature:   float = 0.45,
) -> str:
    """
    Запрос к LLM с ожиданием plain text (сопроводительное письмо).

    Returns:
        Строка — текст письма.
    """
    raw = await _call_endpoint(system_prompt, user_prompt, max_tokens, temperature)
    # Убираем возможные markdown-обёртки
    return raw.strip().strip("`").strip()


# ── Внутренние ────────────────────────────────────────────────────────────

async def _call_endpoint(
    system_prompt: str,
    user_prompt:   str,
    max_tokens:    int,
    temperature:   float,
) -> str:
    """Выполнить запрос к эндпоинту и вернуть сырую строку ответа модели."""
    payload = {
        "task_type":      "llm",
        "model_name":     MODEL_NAME,
        "text":           user_prompt,
        "system_prompt":  system_prompt,
        "max_tokens":     max_tokens,
        "temperature":    temperature,
        "top_p":          0.9,
        "n_ctx":          16384,
        "enable_thinking": False,
    }

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        resp = await client.post(f"{LLM_ENDPOINT_URL}", json=payload)
        resp.raise_for_status()

    data   = resp.json()
    result = data.get("result", {})

    # Если эндпоинт уже вернул распарсенный dict (через грамматику) — сериализуем обратно
    if isinstance(result, dict):
        return result.get("response", json.dumps(result, ensure_ascii=False))

    return str(result)


def _parse_json(text: str) -> dict:
    """
    Извлечь JSON из текста модели.

    Стратегии (от строгой к мягкой):
      1. Прямой json.loads
      2. Убрать markdown-обёртку ```json ... ```
      3. Regex-поиск первого {...} блока
    """
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Убираем ```json ... ``` или ``` ... ```
    cleaned = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Ищем JSON-объект внутри текста
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.error("Не удалось распарсить JSON из ответа LLM:\n%s", text[:500])
    raise ValueError(f"Модель вернула невалидный JSON. Первые 200 символов: {text[:200]!r}")

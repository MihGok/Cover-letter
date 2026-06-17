"""
config.py
─────────
Централизованная конфигурация приложения.

Структура на диске:
    workspace/
    ├── cover-letter-app/   ← BASE_DIR (здесь лежит этот файл)
    │   ├── backend/
    │   ├── frontend/
    │   └── letters/
    └── candidate_data/     ← CANDIDATE_DATA_DIR (соседняя папка)
        ├── candidate_profile.json
        ├── github_summary.json
        └── tech_stack.json
"""

import os
from pathlib import Path

# ── Пути ──────────────────────────────────────────────────────────────────
# backend/ → cover-letter-app/ → workspace/
_BACKEND_DIR = Path(__file__).parent.resolve()
APP_DIR      = _BACKEND_DIR.parent                  # cover-letter-app/

CANDIDATE_DATA_DIR = APP_DIR.parent / "candidate_data"   # соседняя папка
LETTERS_DIR        = APP_DIR / "letters"
DB_PATH            = _BACKEND_DIR / "tasks.db"

# Убедимся что letters/ существует (candidate_data/ создаёт пользователь)
LETTERS_DIR.mkdir(parents=True, exist_ok=True)

# ── LLM endpoint ──────────────────────────────────────────────────────────
LLM_ENDPOINT_URL: str = os.getenv("LLM_ENDPOINT_URL", "http://localhost:8000/task")
MODEL_NAME:       str = os.getenv("MODEL_NAME", "Q8_0.gguf")
LLM_TIMEOUT:    float = float(os.getenv("LLM_TIMEOUT", "600"))

# ── Сервер ────────────────────────────────────────────────────────────────
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8080"))

# ── Параметры письма ──────────────────────────────────────────────────────
COVER_LETTER_MIN_WORDS = 90
COVER_LETTER_MAX_WORDS = 250

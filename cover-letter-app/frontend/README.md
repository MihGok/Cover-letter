# Cover Letter Generator

Локальная система генерации персонализированных сопроводительных писем для HH.ru через LLM.

## Структура на диске

```
workspace/
├── cover-letter-app/        ← этот репозиторий
│   ├── backend/             ← FastAPI (порт 8080)
│   ├── frontend/            ← React + Vite (порт 5173 в dev)
│   └── letters/             ← результаты генерации (создаётся автоматически)
└── candidate_data/          ← СОСЕДНЯЯ папка с профилем кандидата
    ├── candidate_profile.json
    ├── github_summary.json
    └── tech_stack.json
```

> **Важно:** папка `candidate_data/` должна быть **рядом** с `cover-letter-app/`, а не внутри неё.  
> Примеры файлов лежат в `cover-letter-app/candidate_data/` — скопируй их в нужное место и заполни своими данными.

## Требования

- Python 3.11+
- Node.js 18+
- Запущенный LLM-эндпоинт (Docker) на `localhost:8000` с моделью `q8.gguf`

## Запуск

### 1. Backend

```bash
cd cover-letter-app/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. Frontend (dev)

```bash
cd cover-letter-app/frontend
npm install
npm run dev
# → http://localhost:5173
```

### 3. Frontend (production build)

```bash
cd cover-letter-app/frontend
npm run build
# Собранные файлы попадают в frontend/dist/
# FastAPI автоматически подхватывает dist/ и отдаёт SPA на порту 8080
```

## Переменные окружения (backend)

| Переменная         | По умолчанию            | Описание                          |
|--------------------|-------------------------|-----------------------------------|
| `LLM_ENDPOINT_URL` | `http://localhost:8000` | URL LLM-эндпоинта (Docker)        |
| `MODEL_NAME`       | `q8.gguf`               | Имя модели на эндпоинте           |
| `LLM_TIMEOUT`      | `180`                   | Таймаут запроса к LLM (секунды)   |
| `BACKEND_PORT`     | `8080`                  | Порт FastAPI                      |

## Пайплайн

```
URL / текст  →  [1] fetch   →  vacancy_raw.txt
              →  [2] analyze →  vacancy_analysis.json
              →  [3] match   →  matching.json
              →  [4] expand  →  expanded_profile.json
              →  [5] generate → cover_letter.txt  +  meta.json
```

## Ключевые файлы

| Файл                    | Назначение                                                |
|-------------------------|-----------------------------------------------------------|
| `backend/schemas.py`    | Все Pydantic-модели + JSON-схемы для LLM (один файл)     |
| `backend/prompts.py`    | Все системные промпты + строители user-промптов           |
| `backend/pipeline.py`   | Оркестратор: знает порядок этапов, делегирует детали      |
| `backend/hh_fetcher.py` | Адаптер HH.ru: URL → plain text (не оркестрация!)        |
| `backend/llm_gateway.py`| HTTP-клиент к LLM-эндпоинту                              |

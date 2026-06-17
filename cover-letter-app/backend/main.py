"""
main.py
───────
FastAPI-приложение: REST API для React-фронтенда.

Все маршруты под префиксом /api/.
В продакшене FastAPI также отдаёт собранный React (из frontend/dist/).

Запуск:
    uvicorn main:app --host 0.0.0.0 --port 8080 --reload
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db as database
from config import BACKEND_PORT, APP_DIR
from pipeline import run_pipeline, process_queue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("main")

app = FastAPI(title="Cover Letter Generator API", version="1.0.0")

# ── CORS — разрешаем Vite dev-сервер (порт 5173) ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════════════════════
#  Startup
# ════════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup() -> None:
    await database.init_db()
    logger.info("DB initialized | port=%d", BACKEND_PORT)
    
    # Попытаться запустить задачи, которые ждали перезагрузки
    await process_queue()


# ════════════════════════════════════════════════════════════════════════════
#  Pydantic-модели запросов
# ════════════════════════════════════════════════════════════════════════════

class AddTaskRequest(BaseModel):
    vacancy_url:  Optional[str] = None
    vacancy_text: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
#  API — Tasks
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/tasks")
async def get_tasks(search: Optional[str] = Query(None)) -> JSONResponse:
    """Список всех задач, опционально отфильтрованных по поиску."""
    tasks = await database.get_all_tasks(search=search)
    return JSONResponse(tasks)


@app.post("/api/tasks", status_code=201)
async def add_task(req: AddTaskRequest, background_tasks: BackgroundTasks) -> JSONResponse:
    """Добавить вакансию в очередь и попытаться её запустить."""
    url  = (req.vacancy_url  or "").strip() or None
    text = (req.vacancy_text or "").strip() or None

    if not url and not text:
        raise HTTPException(400, "Укажите vacancy_url или vacancy_text.")

    task_id = await database.create_task(vacancy_url=url, vacancy_text=text)
    
    # Попытаться запустить пайплайн для этой или следующей задачи
    background_tasks.add_task(process_queue)

    task = await database.get_task(task_id)
    return JSONResponse(task, status_code=201)


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str) -> JSONResponse:
    task = await database.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Задача {task_id!r} не найдена.")
    return JSONResponse(task)


@app.post("/api/tasks/{task_id}/regenerate")
async def regenerate_task(task_id: str, background_tasks: BackgroundTasks) -> JSONResponse:
    """Перезапустить пайплайн для существующей задачи."""
    task = await database.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Задача {task_id!r} не найдена.")
    if task.get("status") == "processing":
        raise HTTPException(409, "Задача уже выполняется.")

    await database.update_task(
        task_id,
        status       = "queued",
        stage        = "pending",
        error        = None,
        completed_at = None,
    )
    
    # Попытаться запустить пайплайн через очередь
    background_tasks.add_task(process_queue)
    
    task = await database.get_task(task_id)
    return JSONResponse(task)


@app.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str) -> None:
    """Удалить задачу из БД (файлы на диске не трогаем)."""
    task = await database.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Задача {task_id!r} не найдена.")
    await database.delete_task(task_id)


# ════════════════════════════════════════════════════════════════════════════
#  API — Letter & Intermediate files
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/tasks/{task_id}/letter")
async def get_letter(task_id: str) -> JSONResponse:
    """Получить текст готового письма."""
    task = await _get_done_task(task_id)
    path = Path(task["result_dir"]) / "cover_letter.txt"
    if not path.exists():
        raise HTTPException(404, "Файл письма не найден.")
    return JSONResponse({"text": path.read_text(encoding="utf-8")})


@app.get("/api/tasks/{task_id}/files")
async def get_files(task_id: str) -> JSONResponse:
    """
    Получить все промежуточные файлы задачи.
    Возвращает dict: {filename: content (string или dict)}
    """
    task = await _get_done_task(task_id)
    rdir = Path(task["result_dir"])

    files: dict = {}
    for fname in [
        "vacancy_raw.txt",
        "vacancy_analysis.json",
        "matching.json",
        "expanded_profile.json",
        "cover_letter.txt",
        "meta.json",
    ]:
        fpath = rdir / fname
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")
        if fname.endswith(".json"):
            try:
                files[fname] = json.loads(content)
            except json.JSONDecodeError:
                files[fname] = content
        else:
            files[fname] = content

    return JSONResponse(files)


@app.get("/api/tasks/{task_id}/files/{filename}")
async def get_single_file(task_id: str, filename: str) -> JSONResponse:
    """Получить один промежуточный файл по имени."""
    # Защита от path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Недопустимое имя файла.")

    task = await _get_done_task(task_id)
    path = Path(task["result_dir"]) / filename
    if not path.exists():
        raise HTTPException(404, f"Файл {filename!r} не найден.")

    content = path.read_text(encoding="utf-8")
    if filename.endswith(".json"):
        return JSONResponse(json.loads(content))
    return JSONResponse({"content": content})


# ════════════════════════════════════════════════════════════════════════════
#  SPA — отдаём собранный React в продакшене
# ════════════════════════════════════════════════════════════════════════════

_DIST = APP_DIR / "frontend" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """Любой non-API маршрут отдаёт index.html (React Router)."""
        return FileResponse(str(_DIST / "index.html"))


# ════════════════════════════════════════════════════════════════════════════
#  Вспомогательные
# ════════════════════════════════════════════════════════════════════════════

async def _get_done_task(task_id: str) -> dict:
    task = await database.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Задача {task_id!r} не найдена.")
    if not task.get("result_dir"):
        raise HTTPException(404, "Результаты ещё не готовы.")
    return task


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=BACKEND_PORT, reload=True)

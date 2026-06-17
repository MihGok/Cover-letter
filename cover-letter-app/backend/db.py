"""
db.py
─────
Асинхронные операции с SQLite через aiosqlite.

Таблица tasks хранит:
  - очередь и статусы обработки
  - пути к файлам результатов
  - vacancy_text для режима ручного ввода (нужен при повторной генерации)

SQLite НЕ хранит содержимое вакансий и писем — только пути к ним.
Исключение: vacancy_text для режима ручного ввода (нет URL для повторной загрузки).
"""

import uuid
import aiosqlite
from datetime import datetime
from typing import Optional
from config import DB_PATH

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id            TEXT PRIMARY KEY,
    status        TEXT NOT NULL DEFAULT 'queued',
    stage         TEXT NOT NULL DEFAULT 'pending',
    job_title     TEXT,
    company_name  TEXT,
    vacancy_url   TEXT,
    vacancy_text  TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    completed_at  TEXT,
    result_dir    TEXT,
    error         TEXT
)
"""

# ── Публичный API ──────────────────────────────────────────────────────────

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_SQL)
        await db.commit()


async def create_task(
    vacancy_url:  Optional[str] = None,
    vacancy_text: Optional[str] = None,
) -> str:
    task_id = str(uuid.uuid4())[:8]
    now     = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO tasks
               (id, status, stage, vacancy_url, vacancy_text, created_at, updated_at)
               VALUES (?, 'queued', 'pending', ?, ?, ?, ?)""",
            (task_id, vacancy_url, vacancy_text, now, now),
        )
        await db.commit()
    return task_id


async def get_task(task_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_all_tasks(search: Optional[str] = None) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if search:
            pattern = f"%{search}%"
            async with db.execute(
                """SELECT * FROM tasks
                   WHERE job_title LIKE ? OR company_name LIKE ? OR vacancy_url LIKE ?
                   ORDER BY created_at DESC""",
                (pattern, pattern, pattern),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC"
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def update_task(task_id: str, **fields) -> None:
    """Обновить произвольные поля задачи. updated_at проставляется автоматически."""
    fields["updated_at"] = datetime.now().isoformat()
    setters = ", ".join(f"{k} = ?" for k in fields)
    values  = list(fields.values()) + [task_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE tasks SET {setters} WHERE id = ?", values)
        await db.commit()


async def delete_task(task_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()

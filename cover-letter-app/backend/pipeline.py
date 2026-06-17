"""
pipeline.py
───────────
Оркестратор пайплайна обработки вакансии.

Знает ЧТО делать и в каком порядке — делегирует КАК:
  - получение данных → hh_fetcher.py (адаптер)
  - вызов модели    → llm_gateway.py (HTTP-клиент)
  - схемы/промпты   → schemas.py / prompts.py

Этапы:
  1. fetch    — получить текст вакансии (URL или ручной ввод)
  2. analyze  — извлечь структуру вакансии через LLM
  3. match    — сопоставить с профилем кандидата
  4. expand   — сформировать расширенный профиль
  5. generate — написать письмо
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import asyncio

import db
from config import LETTERS_DIR, CANDIDATE_DATA_DIR
from hh_fetcher import fetch_vacancy_from_url, clean_manual_text
from llm_gateway import call_llm_json, call_llm_text
from prompts import (
    VACANCY_ANALYSIS_SYSTEM,
    MATCHING_SYSTEM,
    EXPANDED_PROFILE_SYSTEM,
    COVER_LETTER_SYSTEM,
    build_vacancy_analysis_user,
    build_matching_user,
    build_expanded_profile_user,
    build_cover_letter_user,
)
from schemas import VacancyAnalysis, Matching, ExpandedProfile

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════
#  Ограничение параллельных задач
# ════════════════════════════════════════════════════════════════════════════

MAX_CONCURRENT_TASKS = 2
_queue_lock = asyncio.Lock()
_processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)


# ════════════════════════════════════════════════════════════════════════════
#  НАСТРОЙКИ ГИПЕРПАРАМЕТРОВ LLM ДЛЯ РАЗНЫХ ШАГОВ
# ════════════════════════════════════════════════════════════════════════════

LLM_ANALYZE_PARAMS = {
    "max_tokens": 2000,
    "temperature": 0.1,
    "schema_name": "vacancy_analysis" # Имя схемы из schemas.py
}

LLM_MATCH_PARAMS = {
    "max_tokens": 3500,
    "temperature": 0.25,
    "schema_name": "matching"
}

LLM_EXPAND_PARAMS = {
    "max_tokens": 3500,
    "temperature": 0.35,
    "schema_name": "expanded_profile"
}

LLM_GENERATE_PARAMS = {
    "max_tokens": 4500,
    "temperature": 0.75,
}


# ════════════════════════════════════════════════════════════════════════════
#  Точка входа
# ════════════════════════════════════════════════════════════════════════════

async def process_queue() -> None:
    """
    Проверить очередь и запустить следующую задачу, если есть свободные слоты.
    Вызывается в конце каждого пайплайна и при старте приложения.
    """
    async with _queue_lock:
        # Не пытаемся запустить, если всё занято
        if _processing_semaphore._value <= 0:
            logger.debug("Queue processor: all slots occupied")
            return
        
        # Найти первую задачу в статусе "queued"
        all_tasks = await db.get_all_tasks()
        queued_tasks = [t for t in all_tasks if t.get("status") == "queued"]
        
        if not queued_tasks:
            logger.debug("Queue processor: no queued tasks")
            return
        
        next_task = queued_tasks[0]
        task_id = next_task["id"]
        vacancy_url = next_task.get("vacancy_url")
        vacancy_text = next_task.get("vacancy_text")
        
        logger.info("Queue processor: starting next task | task=%s", task_id)
        
        # Запускаем пайплайн в фоне (не ждём завершения)
        asyncio.create_task(run_pipeline(task_id, vacancy_url, vacancy_text))


async def run_pipeline(
    task_id:      str,
    vacancy_url:  Optional[str],
    vacancy_text: Optional[str],
) -> None:
    """Запустить полный пайплайн для задачи task_id с ограничением параллелизма."""
    # Ждём свободный слот (максимум MAX_CONCURRENT_TASKS одновременно)
    async with _processing_semaphore:
        try:
            result_dir = await _stage_fetch(task_id, vacancy_url, vacancy_text)
            analysis   = await _stage_analyze(task_id, result_dir)
            matching   = await _stage_match(task_id, result_dir, analysis)
            expanded   = await _stage_expand(task_id, result_dir, analysis, matching)
            await _stage_generate(task_id, result_dir, analysis, matching, expanded)

            await db.update_task(
                task_id,
                status       = "done",
                stage        = "done",
                completed_at = datetime.now().isoformat(),
            )
            logger.info("Pipeline done | task=%s", task_id)

        except Exception as exc:
            logger.exception("Pipeline failed | task=%s | %s", task_id, exc)
            await db.update_task(
                task_id,
                status = "failed",
                stage  = "error",
                error  = str(exc),
            )
        
        finally:
            # После завершения текущей задачи, попытаться запустить следующую из очереди
            await process_queue()


# ════════════════════════════════════════════════════════════════════════════
#  Этапы пайплайна
# ════════════════════════════════════════════════════════════════════════════

async def _stage_fetch(
    task_id:      str,
    vacancy_url:  Optional[str],
    vacancy_text: Optional[str],
) -> Path:
    """Этап 1 — получить текст вакансии, создать папку результатов."""
    await db.update_task(task_id, status="processing", stage="fetch")

    if vacancy_url:
        logger.info("Fetching from HH.ru | task=%s | url=%s", task_id, vacancy_url)
        raw = await fetch_vacancy_from_url(vacancy_url)
    elif vacancy_text:
        logger.info("Using manual text | task=%s", task_id)
        raw = clean_manual_text(vacancy_text)
    else:
        raise ValueError("Необходимо указать URL вакансии или её текст.")

    result_dir = _make_result_dir(task_id, "vacancy")
    await db.update_task(task_id, result_dir=str(result_dir))

    (result_dir / "vacancy_raw.txt").write_text(raw, encoding="utf-8")
    logger.debug("vacancy_raw.txt saved | task=%s", task_id)
    return result_dir


async def _stage_analyze(task_id: str, result_dir: Path) -> dict:
    """Этап 2 — LLM анализирует вакансию."""
    await db.update_task(task_id, stage="analyze")

    raw = (result_dir / "vacancy_raw.txt").read_text(encoding="utf-8")
    user_prompt = build_vacancy_analysis_user(raw)

    result = await call_llm_json(
        system_prompt = VACANCY_ANALYSIS_SYSTEM,
        user_prompt   = user_prompt,
        max_tokens    = LLM_ANALYZE_PARAMS["max_tokens"],
        temperature   = LLM_ANALYZE_PARAMS["temperature"],
        schema_name   = LLM_ANALYZE_PARAMS["schema_name"],
    )

    try:
        VacancyAnalysis(**result)
    except Exception as exc:
        logger.warning("VacancyAnalysis validation warning | %s", exc)

    job_title    = result.get("job_title", "unknown")
    company_name = result.get("company_name")

    new_dir = _rename_result_dir(result_dir, task_id, job_title)
    _save_json(new_dir / "vacancy_analysis.json", result)
    
    await db.update_task(
        task_id,
        job_title    = job_title,
        company_name = company_name,
        result_dir   = str(new_dir),
        stage        = "analyze_done",
    )
    logger.info("Vacancy analyzed | task=%s | title=%s", task_id, job_title)
    return result


async def _stage_match(task_id: str, result_dir: Path, analysis: dict) -> dict:
    """Этап 3 — сопоставление кандидата с вакансией (защита от обрыва токенов)."""
    await db.update_task(task_id, stage="match")

    task    = await db.get_task(task_id)
    rdir    = Path(task["result_dir"])

    candidate_data = _load_candidate_data()
    user_prompt    = build_matching_user(analysis, candidate_data)

    result = await call_llm_json(
        system_prompt = MATCHING_SYSTEM,
        user_prompt   = user_prompt,
        max_tokens    = LLM_MATCH_PARAMS["max_tokens"],
        temperature   = LLM_MATCH_PARAMS["temperature"],
        schema_name   = LLM_MATCH_PARAMS["schema_name"],
    )

    try:
        Matching(**result)
    except Exception as exc:
        logger.warning("Matching validation warning | %s", exc)

    _save_json(rdir / "matching.json", result)
    logger.info("Matching done | task=%s | score=%.2f", task_id, result.get("match_score", 0))
    
    await db.update_task(task_id, stage="match_done")
    return result


async def _stage_expand(
    task_id:    str,
    result_dir: Path,
    analysis:   dict,
    matching:   dict,
) -> dict:
    """Этап 4 — формирование расширенного профиля."""
    await db.update_task(task_id, stage="expand")

    task = await db.get_task(task_id)
    rdir = Path(task["result_dir"])

    candidate_data = _load_candidate_data()
    user_prompt    = build_expanded_profile_user(analysis, matching, candidate_data)

    result = await call_llm_json(
        system_prompt = EXPANDED_PROFILE_SYSTEM,
        user_prompt   = user_prompt,
        max_tokens    = LLM_EXPAND_PARAMS["max_tokens"],
        temperature   = LLM_EXPAND_PARAMS["temperature"],
        schema_name   = LLM_EXPAND_PARAMS["schema_name"],
    )

    try:
        ExpandedProfile(**result)
    except Exception as exc:
        logger.warning("ExpandedProfile validation warning | %s", exc)

    _save_json(rdir / "expanded_profile.json", result)
    logger.info("Profile expanded | task=%s", task_id)
    await db.update_task(task_id, stage="expand_done")
    return result


async def _stage_generate(
    task_id:    str,
    result_dir: Path,
    analysis:   dict,
    matching:   dict,
    expanded:   dict,
) -> None:
    """Этап 5 — генерация финального письма (высокий креатив)."""
    await db.update_task(task_id, stage="generate")

    task = await db.get_task(task_id)
    rdir = Path(task["result_dir"])

    candidate_data = _load_candidate_data()
    user_prompt    = build_cover_letter_user(analysis, matching, expanded, candidate_data)

    letter = await call_llm_text(
        system_prompt = COVER_LETTER_SYSTEM,
        user_prompt   = user_prompt,
        max_tokens    = LLM_GENERATE_PARAMS["max_tokens"],
        temperature   = LLM_GENERATE_PARAMS["temperature"],
    )

    (rdir / "cover_letter.txt").write_text(letter, encoding="utf-8")

    meta = {
        "task_id":          task_id,
        "job_title":        analysis.get("job_title"),
        "company_name":     analysis.get("company_name"),
        "vacancy_url":      task.get("vacancy_url"),
        "match_score":      matching.get("match_score"),
        "word_count":       len(letter.split()),
        "generated_at":     datetime.now().isoformat(),
        "model":            "q8.gguf",
        "pipeline_version": "1.3",
    }
    _save_json(rdir / "meta.json", meta)
    logger.info("Letter generated | task=%s | words=%d", task_id, meta["word_count"])


# ════════════════════════════════════════════════════════════════════════════
#  Вспомогательные методы
# ════════════════════════════════════════════════════════════════════════════

def _load_candidate_data() -> dict:
    """Загрузить все три файла профиля кандидата."""
    data: dict = {}
    for key, fname in [
        ("candidate_profile", "candidate_profile.json"),
        ("github_summary",    "github_summary.json"),
        ("tech_stack",        "tech_stack.json"),
    ]:
        path = CANDIDATE_DATA_DIR / fname
        if path.exists():
            try:
                data[key] = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Не удалось прочитать %s: %s", fname, exc)
                data[key] = {}
        else:
            logger.warning("Файл не найден: %s", path)
            data[key] = {}
    return data


def _make_result_dir(task_id: str, slug: str) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    dir_name = f"{date_str}_{slug}_{task_id}"
    result_dir = LETTERS_DIR / dir_name
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir


def _rename_result_dir(old_dir: Path, task_id: str, job_title: str) -> Path:
    """Переименовать папку, вставив slug из названия должности."""
    import shutil
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug     = "".join(c if c.isalnum() else "_" for c in job_title.lower())[:35].strip("_")
    new_name = f"{date_str}_{slug}_{task_id}"
    new_dir  = LETTERS_DIR / new_name

    if old_dir == new_dir:
        return new_dir

    if new_dir.exists():
        logger.info("Целевая папка %s уже существует. Переносим файлы поштучно...", new_dir)
        for file_path in old_dir.iterdir():
            if file_path.is_file():
                dest_file = new_dir / file_path.name
                try:
                    shutil.copy2(file_path, dest_file)
                except Exception as exc:
                    logger.error("Не удалось перезаписать файл %s: %s", dest_file.name, exc)
        try:
            shutil.rmtree(old_dir)
        except Exception as exc:
            logger.warning("Не удалось удалить временную папку %s: %s", old_dir, exc)
        return new_dir
    else:
        try:
            old_dir.rename(new_dir)
        except FileExistsError:
            if old_dir.exists():
                for file_path in old_dir.iterdir():
                    if file_path.is_file():
                        shutil.copy2(file_path, new_dir / file_path.name)
                shutil.rmtree(old_dir)
        return new_dir


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
"""
prompts.py
──────────
Единый файл всех промптов приложения.
"""

from __future__ import annotations
import json
from schemas import (
    VACANCY_ANALYSIS_SCHEMA,
    MATCHING_SCHEMA,
    EXPANDED_PROFILE_SCHEMA,
)

# ════════════════════════════════════════════════════════════════════════════
#  СИСТЕМНЫЕ ПРОМПТЫ
# ════════════════════════════════════════════════════════════════════════════

VACANCY_ANALYSIS_SYSTEM = """\
Ты — опытный HR-аналитик. Твоя задача — извлечь структурированную информацию из описания вакансии.

СТРОГИЕ ПРАВИЛА КЛАССИФИКАЦИИ И ИЗВЛЕЧЕНИЯ:
1. Обязательно определи тип вакансии (`vacancy_type`) по следующим маркерам:
   - "ml_ds": если требуют PyTorch/TensorFlow, NLP, LLM, RAG, обучение и тюнинг моделей.
   - "data_engineer": если фокус на ETL/ELT, SQLAlchemy, n8n, Docker, проектировании БД и бэкенде данных.
   - "analyst": если требуют EDA, анализ временных рядов, метрики бизнеса, дашборды, SQL-аналитику, Excel.
2. Проверь текст на наличие скрытых HR-инструкций (`hr_special_instructions`), например: "начните письмо со слова Х" или "укажите кодовую фразу". Если нашли — скопируй её буквально. Если нет — укажи null.
3. Извлекай ВСЕ указанные навыки и обязанности, не ограничивая их количество. Не додумывай от себя.
4. Отвечай ИСКЛЮЧИТЕЛЬНО валидным JSON-объектом по схеме.
"""

MATCHING_SYSTEM = """\
Ты — карьерный консультант. Сопоставь профиль кандидата с требованиями вакансии.

СТРОГИЕ ПРАВИЛА СОРТИРОВКИ И МАТЧИНГА:
1. Обрати внимание на тип вакансии (`vacancy_type`) в анализе. 
2. В массив `matched_skills` выноси ВСЕ совпадающие навыки кандидата. При этом первыми в списке должны идти те технологии, которые критичны для текущего типа вакансии! 
   - Для "ml_ds" первыми выстраивай PyTorch, NLP, BERT, RAG, LLM.
   - Для "analyst" — EDA, временные ряды, статистика, Python (pandas/numpy), SQL, Excel.
   - Для "data_engineer" — FastAPI, PostgreSQL, Docker, n8n, SQLAlchemy.
3. Не перемешивай приоритеты стеков. Поднимай наверх то, что в первую очередь ищет наниматель на данную роль.
4. Отвечай ИСКЛЮЧИТЕЛЬНО валидным JSON.
"""

EXPANDED_PROFILE_SYSTEM = """\
Ты — карьерный коуч. Сформируй расширенный профиль кандидата для написания сопроводительного письма.

СТРОЖАЙШИЕ ПРАВИЛА СОРТИРОВКИ:
Твоя главная задача — распределить элементы массива `confirmed_strengths` (подтвержденные сильные стороны) по уровню их релевантности к типу вакансии (`vacancy_type`). Выведи все доступные пункты, но отсортируй их так, чтобы профильные достижения шли в самом начале.

Зависимость сортировки от `vacancy_type`:
1. Если vacancy_type == "ml_ds": Наверх списка выноси достижения в сфере Machine Learning (обучение моделей, NLP, fine-tuning BERT, разработка EduRAG, speech-to-text). Инфраструктуру и бэкенд сдвигай ниже.
2. Если vacancy_type == "analyst": Наверх списка выноси аналитические и математические навыки (проведение EDA, анализ временных рядов, высшая математика, статистика, построение SQL-витрин, автоматизация отчетности). Опыт обучения тяжелых нейросетей сдвигай вниз.
3. Если vacancy_type == "data_engineer": Наверх списка выноси бэкенд и ETL-достижения (разработка пайплайнов в n8n, контейнеризация в Docker, проектирование баз данных PostgreSQL/Qdrant/MinIO, FastAPI, SQLAlchemy).

Ничего не придумывай. Сортируй только реальные факты из профиля кандидата. Отвечай ИСКЛЮЧИТЕЛЬНО валидным JSON.
"""

COVER_LETTER_SYSTEM = """\
Ты — Михаил Голиков, квалифицированный IT-специалист с глубоким математическим подходом к данным. Напиши сильное, technical-driven сопроводительное письмо.

ВЫХОДНОЙ ФОРМАТ:
Выводи ИСКЛЮЧИТЕЛЬНО готовый текст письма от первого лица. Никаких системных заголовков, markdown-разметки кода (```), вводных фраз модели или комментариев быть не должно. Только чистый текст.

ПРАВИЛА И СТРУКТУРА ПИСЬМА (СТРОГО 3 АБЗАЦА):

1. АБЗАЦ 1: КРЮЧОК И ВХОД (1-2 предложения)
   - Внимательно изучи блок "СПЕЦИАЛЬНЫЕ ИНСТРУКЦИИ ОТ HR". Если там передано конкретное условие (кодовое слово, фраза), выполни его БУКВАЛЬНО в самой первой строке. Если там написано "Нет специальных требований", начни стандартно: свяжи свой профильный инженерный фокус с вектором задач компании. Название должности и компании бери строго из предоставленных блоков данных вакансии.
   - Пример начала без спец. требований: "Решение задач предиктивного моделирования и работы со сложными текстовыми массивами в компании SCHWARZ — направление, полностью соответствующее моему инженерному фокусу."
   - Избегай избитых фраз вроде "Отличное совпадение!", "Добрый день!" или "Прошу рассмотреть мою кандидатуру".

2. АБЗАЦ 2: ТВЕРДЫЕ ФАКТЫ И СТЕК (Плотное изложение без воды)
   - Опиши реальные технические задачи кандидата, опираясь на предоставленный список опыта, стек и проекты. Используй предоставленные данные по максимуму.
   - Если тип вакансии "ml_ds" — делай упор на PyTorch, NLP, fine-tuning моделей семейства BERT/RoBERTa и RAG-системы.
   - Если тип вакансии "analyst" — пиши про EDA, математическую статистику, анализ временных рядов, сбор и обработку данных с помощью Python, SQL и Excel. Исключи из текста упоминания обучения нейросетей, PyTorch или Docker.
   - Если тип вакансии "data_engineer" — пиши про ETL-пайплайны, n8n, FastAPI, SQLAlchemy и проектирование баз данных.
   - Будь технически точен: MinIO — это объектное хранилище (S3), Qdrant — векторная БД. Не смешивай их терминологию.

3. АБЗАЦ 3: ПРИЗЫВ К ДЕЙСТВИЮ (1-2 предложения)
   - Профессиональное предложение обсудить текущие вызовы команды, стек или архитектурные задачи на техническом созвоне или встрече.
   - В самом конце строго: "С уважением, Михаил Голиков."

СТИЛЬ: Живой, сдержанный, уверенный язык инженера. Объём: до 800-1100 знаков.
"""

def build_matching_user(
    analysis:       dict,
    candidate_data: dict,
) -> str:
    schema_str   = json.dumps(MATCHING_SCHEMA, ensure_ascii=False, indent=2)
    analysis_str = json.dumps(analysis, ensure_ascii=False, indent=2)
    profile_str  = json.dumps(candidate_data.get("candidate_profile", {}), ensure_ascii=False, indent=2)
    github_str   = json.dumps(candidate_data.get("github_summary", {}),    ensure_ascii=False, indent=2)
    tech_str     = json.dumps(candidate_data.get("tech_stack", []),         ensure_ascii=False, indent=2)

    return f"""\
Сопоставь профиль кандидата с требованиями вакансии. Учитывай определенный тип вакансии (`vacancy_type`) и сортируй совпадающие навыки так, чтобы профильные технологии для этой роли оказались первыми в списке `matched_skills`. Собери все совпадения без урезания списков.

## Схема ответа:
{schema_str}

## Анализ вакансии (включая тип роли):
{analysis_str}

## Профиль кандидата:
{profile_str}

## Технические детали проектов:
{github_str}

## Технологический стек:
{tech_str}
"""

def build_vacancy_analysis_user(raw_text: str) -> str:
    schema_str = json.dumps(VACANCY_ANALYSIS_SCHEMA, ensure_ascii=False, indent=2)
    return f"""\
Проанализируй вакансию и верни JSON строго по схеме ниже. Обязательно определи `vacancy_type` и вытащи `hr_special_instructions` при их наличии. Извлекай ВСЕ навыки и требования без ограничений по количеству.

## Схема ответа:
{schema_str}

## Текст вакансии:
{raw_text}
"""

def build_expanded_profile_user(
    analysis:       dict,
    matching:       dict,
    candidate_data: dict,
) -> str:
    schema_str   = json.dumps(EXPANDED_PROFILE_SCHEMA, ensure_ascii=False, indent=2)
    analysis_str = json.dumps(analysis,  ensure_ascii=False, indent=2)
    matching_str = json.dumps(matching,  ensure_ascii=False, indent=2)
    profile_str  = json.dumps(candidate_data.get("candidate_profile", {}), ensure_ascii=False, indent=2)

    return f"""\
Сформируй расширенный профиль кандидата. 
КРИТИЧЕСКОЕ ТРЕБОВАНИЕ: Внеси ВСЕ подтвержденные сильные стороны в массив `confirmed_strengths` без ограничений по количеству пунктов, но отсортируй их строго в соответствии с типом вакансии (`vacancy_type`), указанным в анализе. Самые важные для этой конкретной роли навыки должны идти в начале списка.

## Схема ответа:
{schema_str}

## Анализ вакансии (включая тип роли):
{analysis_str}

## Результаты сопоставления:
{matching_str}

## Полный профиль кандидата:
{profile_str}
"""


def build_cover_letter_user(
    analysis:       dict,
    matching:       dict,
    expanded:       dict,
    candidate_data: dict,
) -> str:
    profile = candidate_data.get("candidate_profile", {})

    # ── 1. Данные вакансии и маршрутизация ───────────────────────────────
    job_title       = analysis.get("job_title", "Специалист")
    company         = analysis.get("company_name") or "вашей компании"
    v_type          = analysis.get("vacancy_type", "ml_ds")
    hr_instructions = analysis.get("hr_special_instructions") or "Нет специальных требований"
    
    required  = ", ".join(analysis.get("required_skills", []))
    duties    = "\n".join(f"• {r}" for r in analysis.get("key_responsibilities", []))

    # ── 2. Опыт (Передаем весь массив без ограничений по длине) ─────────
    confirmed_points = []
    for s in expanded.get("confirmed_strengths", []):
        if isinstance(s, dict) and "point" in s:
            confirmed_points.append(f"• {s['point']}")
        elif isinstance(s, str):
            confirmed_points.append(f"• {s}")
    confirmed_str = "\n".join(confirmed_points)

    # ── 3. Формирование стека навыков (без ограничений) ──────────────────
    matched_skills = []
    if isinstance(matching.get("matched_skills"), list):
        for m in matching["matched_skills"]:
            skill_name = m["skill"] if isinstance(m, dict) and "skill" in m else str(m)
            matched_skills.append(skill_name)
            
    # Динамическое дополнение базы под конкретную роль
    if v_type == "analyst":
        for analytic_tool in ["Python", "SQL", "Excel", "Power BI"]:
            if analytic_tool not in matched_skills and analytic_tool in str(candidate_data):
                matched_skills.append(analytic_tool)
    elif v_type in ["ml_ds", "data_engineer"]:
        for eng_tool in ["Python", "SQL"]:
            if eng_tool not in matched_skills and eng_tool in str(candidate_data):
                matched_skills.append(eng_tool)

    matched_skills_str = ", ".join(matched_skills)

    # ── 4. Проекты кандидата (передаем полный список без урезания) ───────
    profile_projects_by_name = {}
    for proj in profile.get("projects", []):
        name = proj.get("name", "")
        profile_projects_by_name[name.lower()] = proj
        short = name.split("—")[0].split("(")[0].strip().lower()
        profile_projects_by_name[short] = proj

    projects_lines: list[str] = []
    matched_projs = matching.get("matched_projects", []) if isinstance(matching.get("matched_projects"), list) else []
    
    for mp in matched_projs:
        mp_name = mp.get("project", "") if isinstance(mp, dict) else str(mp)
        
        # Защита от перекрестных доменных утечек для аналитиков
        if v_type == "analyst" and any(w in mp_name.lower() for w in ["edurag", "whisper"]):
            continue

        proj_desc = ""
        for key, proj in profile_projects_by_name.items():
            if mp_name.lower() in key or key in mp_name.lower():
                proj_desc = proj.get("description", "")[:300]
                break

        if proj_desc:
            projects_lines.append(f"• Проект {mp_name}: {proj_desc}")
        else:
            projects_lines.append(f"• Проект {mp_name}")

    projects_str = "\n".join(projects_lines) if projects_lines else "Релевантные технические задачи"
    candidate_name = profile.get("name", "Михаил Голиков")

    return f"""\
Напиши сопроводительное письмо на основе следующих ТВЕРДЫХ параметров.

## СПЕЦИАЛЬНЫЕ ИНСТРУКЦИИ ОТ HR:
{hr_instructions}

## СТРАТЕГИЧЕСКИЙ КОНТЕКСТ:
Тип вакансии: {v_type}

## АУТЕНТИЧНЫЕ ДАННЫЕ КАНДИДАТА:
Имя: {candidate_name}

## ДАННЫЕ ВАКАНСИИ:
Должность: {job_title}
Компания: {company}
Обязанности на позиции:
{duties}
Требуемый стек и навыки: {required}

## РЕАЛЬНЫЙ ТЕХНИЧЕСКИЙ ОПЫТ КАНДИДАТА:
{confirmed_str}
Владение инструментами (стек): {matched_skills_str}

## ТЕХНИЧЕСКАЯ СУТЬ ПРОЕКТОВ:
{projects_str}
"""
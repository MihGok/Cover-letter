"""
schemas.py
──────────
Единый файл всех схем приложения.

Разделы:
  1. PYDANTIC MODELS  — валидация выходов LLM в pipeline
  2. LLM JSON SCHEMAS — dict-схемы, встраиваемые в промпты
                        чтобы модель знала ожидаемую структуру

Почему всё в одном файле:
  - Pydantic-модель и соответствующая ей JSON-схема живут рядом
  - При изменении структуры этапа достаточно поправить одно место
  - Нет риска расхождения между валидатором и схемой в промпте
"""

from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

Schema = dict[str, Any]

# ════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — PYDANTIC MODELS
#  Используются для валидации dict'ов, которые вернул LLM
# ════════════════════════════════════════════════════════════════════════════

# ── Этап 2: Анализ вакансии ───────────────────────────────────────────────

class VacancyAnalysis(BaseModel):
    job_title:             str
    company_name:          Optional[str]       = None
    location:              Optional[str]       = None
    experience_required:   Optional[str]       = None
    required_skills:       list[str]           = Field(default_factory=list)
    preferred_skills:      list[str]           = Field(default_factory=list)
    tech_stack:            list[str]           = Field(default_factory=list)
    seniority_signals:     list[str]           = Field(default_factory=list)
    key_responsibilities:  list[str]           = Field(default_factory=list)


# ── Этап 3: Сопоставление с профилем ─────────────────────────────────────

class SkillMatch(BaseModel):
    skill:       str
    evidence:    str                             = ""
    claim_type:  Literal["confirmed", "inferred"] = "confirmed"


class ProjectMatch(BaseModel):
    project:    str
    relevance:  str = ""


class Matching(BaseModel):
    matched_skills:     list[SkillMatch]   = Field(default_factory=list)
    unmatched_required: list[str]          = Field(default_factory=list)
    matched_projects:   list[ProjectMatch] = Field(default_factory=list)
    match_score:        float              = 0.0    # 0.0–1.0
    strong_points:      list[str]         = Field(default_factory=list)
    gaps:               list[str]         = Field(default_factory=list)
    recommended_focus:  list[str]         = Field(default_factory=list)


# ── Этап 4: Расширенный профиль ───────────────────────────────────────────

class ConfirmedStrength(BaseModel):
    point:    str
    evidence: str = ""


class SafeInference(BaseModel):
    point:  str
    basis:  str = ""


class ExpandedProfile(BaseModel):
    confirmed_strengths:  list[ConfirmedStrength] = Field(default_factory=list)
    safe_inferences:      list[SafeInference]     = Field(default_factory=list)
    potential_advantages: list[str]               = Field(default_factory=list)
    key_selling_points:   list[str]               = Field(default_factory=list)


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — LLM JSON SCHEMAS
#  Встраиваются в промпты. Модель видит структуру и генерирует JSON по ней.
#  Не используют GBNF-грамматику эндпоинта (чужие схемы туда не добавить),
#  поэтому соблюдение структуры обеспечивается промптом + парсингом.
# ════════════════════════════════════════════════════════════════════════════

VACANCY_ANALYSIS_SCHEMA: Schema = {
    "type": "object",
    "properties": {
        "job_title":            {"type": "string",  "description": "Название должности"},
        "company_name":         {"type": "string",  "description": "Название компании (null если не указано)"},
        "location":             {"type": "string",  "description": "Город / формат (null если не указано)"},
        "experience_required":  {"type": "string",  "description": "Требуемый опыт (null если не указано)"},
        "required_skills":      {"type": "array",   "items": {"type": "string"}, "description": "Обязательные требования"},
        "preferred_skills":     {"type": "array",   "items": {"type": "string"}, "description": "Желательные требования"},
        "tech_stack":           {"type": "array",   "items": {"type": "string"}, "description": "Конкретные технологии"},
        "seniority_signals":    {"type": "array",   "items": {"type": "string"}, "description": "Признаки уровня позиции"},
        "key_responsibilities": {"type": "array",   "items": {"type": "string"}, "description": "Ключевые обязанности"},
    },
    "required": ["job_title", "required_skills", "key_responsibilities"],
}

MATCHING_SCHEMA: Schema = {
    "type": "object",
    "properties": {
        "matched_skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill":      {"type": "string"},
                    "evidence":   {"type": "string", "description": "Где в профиле это подтверждено"},
                    "claim_type": {"type": "string", "enum": ["confirmed", "inferred"]},
                },
                "required": ["skill", "evidence", "claim_type"],
            },
        },
        "unmatched_required": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Обязательные требования вакансии, которых нет в профиле",
        },
        "matched_projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "project":   {"type": "string"},
                    "relevance": {"type": "string"},
                },
                "required": ["project", "relevance"],
            },
        },
        "match_score":     {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "strong_points":   {"type": "array", "items": {"type": "string"}},
        "gaps":            {"type": "array", "items": {"type": "string"}},
        "recommended_focus": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["matched_skills", "match_score", "strong_points"],
}

EXPANDED_PROFILE_SCHEMA: Schema = {
    "type": "object",
    "properties": {
        "confirmed_strengths": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "point":    {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["point", "evidence"],
            },
            "description": "Только факты прямо из профиля",
        },
        "safe_inferences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "point": {"type": "string"},
                    "basis": {"type": "string"},
                },
                "required": ["point", "basis"],
            },
            "description": "Логические выводы из фактов профиля (не выдумки)",
        },
        "potential_advantages": {
            "type": "array",
            "items": {"type": "string"},
        },
        "key_selling_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Главные аргументы для письма в порядке приоритета",
        },
    },
    "required": ["confirmed_strengths", "key_selling_points"],
}

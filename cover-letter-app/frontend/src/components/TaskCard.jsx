import { useState } from "react";

// ── Конфиг статусов ────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  queued:     { label: "В очереди",   color: "text-gray-400  bg-gray-800     border-gray-700" },
  processing: { label: "Обработка",   color: "text-indigo-300 bg-indigo-950  border-indigo-700" },
  done:       { label: "Готово",      color: "text-emerald-300 bg-emerald-950 border-emerald-700" },
  failed:     { label: "Ошибка",      color: "text-red-300    bg-red-950      border-red-700" },
};

const STAGE_LABELS = {
  pending:      "Ожидание...",
  fetch:        "Получение вакансии",
  analyze:      "Анализ вакансии",
  analyze_done: "Анализ завершён",
  match:        "Сопоставление с профилем",
  expand:       "Расширение профиля",
  generate:     "Генерация письма",
  done:         "Завершено",
  error:        "Ошибка",
};

// ── Компонент ─────────────────────────────────────────────────────────────

export default function TaskCard({
  task,
  onRegenerate,
  onDelete,
  onViewLetter,
  onViewFiles,
  onCopyLetter,
}) {
  const [copied, setCopied] = useState(false);

  const cfg     = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.queued;
  const isDone  = task.status === "done";
  const isProc  = task.status === "processing";
  const isFail  = task.status === "failed";

  const handleCopy = async () => {
    await onCopyLetter();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const date = task.created_at
    ? new Date(task.created_at).toLocaleString("ru-RU", {
        day:    "2-digit",
        month:  "2-digit",
        hour:   "2-digit",
        minute: "2-digit",
      })
    : "";

  return (
    <div className={`bg-gray-900 border rounded-xl px-5 py-4 transition-colors
      ${isFail ? "border-red-900/60" : "border-gray-800 hover:border-gray-700"}`}>

      <div className="flex items-start justify-between gap-4">
        {/* Левая часть: заголовок + метаданные */}
        <div className="min-w-0 flex-1">
          {/* Должность + компания */}
          <p className="text-sm font-medium text-gray-100 truncate">
            {task.job_title ?? (
              <span className="text-gray-600 italic">
                {isProc ? "Определяется..." : "Вакансия без названия"}
              </span>
            )}
          </p>
          {task.company_name && (
            <p className="text-xs text-gray-500 mt-0.5 truncate">{task.company_name}</p>
          )}

          {/* Метаданные: дата / URL / ID */}
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <span className="text-xs text-gray-600">{date}</span>
            <span className="text-xs text-gray-700">#{task.id}</span>
            {task.vacancy_url && (
              <a
                href={task.vacancy_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-indigo-400 hover:text-indigo-300 truncate max-w-[240px]"
              >
                {task.vacancy_url}
              </a>
            )}
          </div>

          {/* Прогресс для processing */}
          {isProc && (
            <div className="mt-2 flex items-center gap-2">
              <ProgressDot />
              <span className="text-xs text-indigo-400">
                {STAGE_LABELS[task.stage] ?? task.stage ?? "Обработка..."}
              </span>
            </div>
          )}

          {/* Ошибка */}
          {isFail && task.error && (
            <p className="mt-2 text-xs text-red-400 bg-red-950/30 rounded-lg px-3 py-2 line-clamp-2">
              {task.error}
            </p>
          )}
        </div>

        {/* Правая часть: бейдж + кнопки */}
        <div className="flex flex-col items-end gap-3 shrink-0">
          {/* Status badge */}
          <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${cfg.color}`}>
            {cfg.label}
          </span>

          {/* Action buttons */}
          <div className="flex items-center gap-1.5">
            {isDone && (
              <>
                <ActionBtn
                  label={copied ? "Скопировано ✓" : "Копировать"}
                  onClick={handleCopy}
                  accent={copied}
                />
                <ActionBtn label="Просмотреть" onClick={onViewLetter} />
                <ActionBtn label="JSON" onClick={onViewFiles} muted />
              </>
            )}
            {(isDone || isFail) && (
              <ActionBtn label="Повторить" onClick={onRegenerate} muted />
            )}
            <ActionBtn label="✕" onClick={onDelete} muted danger title="Удалить задачу" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Вспомогательные ───────────────────────────────────────────────────────

function ActionBtn({ label, onClick, muted = false, accent = false, danger = false, title }) {
  const base = "text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors focus:outline-none";
  const style = danger
    ? "text-red-400 border-red-900 hover:bg-red-950/60"
    : accent
    ? "text-emerald-300 border-emerald-800 bg-emerald-950/40"
    : muted
    ? "text-gray-500 border-gray-800 hover:text-gray-300 hover:border-gray-700"
    : "text-indigo-300 border-indigo-800 hover:bg-indigo-950/60";

  return (
    <button onClick={onClick} title={title} className={`${base} ${style}`}>
      {label}
    </button>
  );
}

function ProgressDot() {
  return (
    <span className="relative flex h-2 w-2">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500" />
    </span>
  );
}

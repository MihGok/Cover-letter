import { useState, useEffect } from "react";

const FILE_META = {
  "vacancy_raw.txt":        { label: "Вакансия (исходный текст)", icon: "📄" },
  "vacancy_analysis.json":  { label: "Анализ вакансии (этап 2)",  icon: "🔍" },
  "matching.json":          { label: "Сопоставление (этап 3)",    icon: "🔗" },
  "expanded_profile.json":  { label: "Расширенный профиль (этап 4)", icon: "🧩" },
  "cover_letter.txt":       { label: "Финальное письмо (этап 5)", icon: "✉️" },
  "meta.json":              { label: "Мета-данные",               icon: "ℹ️" },
};

export default function FilesDrawer({ files, onClose }) {
  const [active, setActive] = useState(() => {
    // Открываем первый доступный файл
    const order = Object.keys(FILE_META);
    return order.find((k) => k in files) ?? Object.keys(files)[0] ?? null;
  });

  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const content = active ? files[active] : null;
  const displayContent =
    content !== null && typeof content === "object"
      ? JSON.stringify(content, null, 2)
      : content ?? "";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-4xl
                      shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h3 className="text-sm font-semibold text-gray-100">Промежуточные файлы</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-sm px-2 py-1.5
                       rounded-lg border border-gray-800 hover:border-gray-700 transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="flex flex-1 min-h-0">
          {/* Sidebar — список файлов */}
          <div className="w-56 border-r border-gray-800 py-2 shrink-0 overflow-y-auto">
            {Object.entries(FILE_META).map(([fname, meta]) => {
              if (!(fname in files)) return null;
              return (
                <button
                  key={fname}
                  onClick={() => setActive(fname)}
                  className={`w-full text-left px-4 py-2.5 transition-colors flex items-start gap-2 ${
                    active === fname
                      ? "bg-indigo-950/60 text-indigo-200"
                      : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/40"
                  }`}
                >
                  <span className="mt-0.5 text-base leading-none">{meta.icon}</span>
                  <span className="text-xs leading-snug">{meta.label}</span>
                </button>
              );
            })}
          </div>

          {/* Контент файла */}
          <div className="flex-1 overflow-auto p-5 min-w-0">
            {active && (
              <div className="bg-gray-950/60 rounded-xl p-4 border border-gray-800 h-full">
                <pre className="text-xs text-gray-300 leading-relaxed overflow-auto">
                  {displayContent}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

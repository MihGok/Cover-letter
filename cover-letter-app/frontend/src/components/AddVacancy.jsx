import { useState } from "react";

export default function AddVacancy({ onAdd }) {
  const [url,       setUrl]       = useState("");
  const [text,      setText]      = useState("");
  const [loading,   setLoading]   = useState(false);
  const [activeTab, setActiveTab] = useState("url"); // "url" | "text"

  const handlePaste = (e, type) => {
    // Явная обработка вставки через Ctrl+V и контекстное меню
    e.preventDefault();
    const pastedText = e.clipboardData?.getData("text") || "";
    if (type === "url") {
      setUrl(pastedText);
    } else {
      setText(pastedText);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimUrl  = url.trim();
    const trimText = text.trim();
    if (!trimUrl && !trimText) return;

    setLoading(true);
    try {
      await onAdd({
        vacancy_url:  activeTab === "url"  ? trimUrl  : null,
        vacancy_text: activeTab === "text" ? trimText : null,
      });
      // Сбрасываем только активное поле
      if (activeTab === "url")  setUrl("");
      else                      setText("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-sm font-medium text-gray-300 mb-4">Новая вакансия</h2>

      {/* Вкладки */}
      <div className="flex gap-1 mb-5 bg-gray-800/60 rounded-lg p-1 w-fit">
        {[
          { id: "url",  label: "URL HH.ru" },
          { id: "text", label: "Текст вручную" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {activeTab === "url" ? (
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">
              Ссылка на вакансию
            </label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onPaste={(e) => handlePaste(e, "url")}
              placeholder="https://hh.ru/vacancy/12345678"
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5
                         text-sm text-gray-100 placeholder-gray-600
                         focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
            />
          </div>
        ) : (
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">
              Текст вакансии (скопируйте из браузера)
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              onPaste={(e) => handlePaste(e, "text")}
              placeholder="Вставьте текст вакансии..."
              required
              rows={7}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5
                         text-sm text-gray-100 placeholder-gray-600 resize-y
                         focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
            />
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading || (activeTab === "url" ? !url.trim() : !text.trim())}
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500
                       disabled:opacity-40 disabled:cursor-not-allowed
                       text-white text-sm font-medium px-5 py-2 rounded-lg
                       transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            {loading ? (
              <>
                <Spinner />
                Добавляю...
              </>
            ) : (
              "Добавить в очередь →"
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

import { useState, useEffect } from "react";

export default function LetterModal({ text, onCopy, onClose }) {
  const [copied, setCopied] = useState(false);
  const wordCount = text ? text.split(/\s+/).filter(Boolean).length : 0;

  // Закрытие по Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const handleCopy = async () => {
    await onCopy();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl
                      shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div>
            <h3 className="text-sm font-semibold text-gray-100">Сопроводительное письмо</h3>
            <p className={`text-xs mt-0.5 ${
              wordCount < 110 || wordCount > 170 ? "text-amber-400" : "text-gray-500"
            }`}>
              {wordCount} слов
              {wordCount < 110 && " — меньше нормы (110–170)"}
              {wordCount > 170 && " — больше нормы (110–170)"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className={`text-sm px-4 py-1.5 rounded-lg border font-medium transition-colors ${
                copied
                  ? "text-emerald-300 border-emerald-700 bg-emerald-950/50"
                  : "text-indigo-300 border-indigo-700 hover:bg-indigo-950/50"
              }`}
            >
              {copied ? "Скопировано ✓" : "Копировать"}
            </button>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-300 text-sm px-2 py-1.5
                         rounded-lg border border-gray-800 hover:border-gray-700 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Текст письма */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          <div className="bg-gray-950/60 rounded-xl p-5 border border-gray-800">
            <pre className="text-sm text-gray-200 leading-relaxed font-sans">
              {text}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}

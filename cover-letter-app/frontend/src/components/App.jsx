import { useState, useEffect, useCallback } from "react";
import { getTasks, addTask, regenerateTask, deleteTask, getLetter, getAllFiles } from "./api.js";

// Убрали папку /components/ из путей, так как файлы лежат рядом с App.jsx
import AddVacancy from "./AddVacancy.jsx";
import TaskList from "./TaskList.jsx";
import LetterModal from "./LetterModal.jsx";
import FilesDrawer from "./FilesDrawer.jsx";

const POLL_INTERVAL = 3000;

export default function App() {
  const [tasks,  setTasks]  = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [search,  setSearch]  = useState("");
  const [modal,   setModal]   = useState(null);

  // ── Загрузка задач ───────────────────────────────────────────────────────
  const fetchTasks = useCallback(async (query = "") => {
    try {
      const data = await getTasks(query);
      setTasks(data);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []); // стабильная ссылка — не пересоздаётся

  // Эффект 1: начальная загрузка + перезагрузка при смене поиска
  useEffect(() => {
    fetchTasks(search);
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps

  // Эффект 2: умный поллинг — только пока есть активные задачи
  //
  // Почему [hasActiveTasks, search], а не [tasks]:
  //   - tasks меняется каждые POLL_INTERVAL мс → интервал пересоздавался бы
  //     каждый раз, накапливая экземпляры и сбрасывая таймер
  //   - hasActiveTasks — производный boolean; меняется только при реальном
  //     переходе queued/processing → done/failed
  //   - search нужен чтобы новый интервал читал актуальное значение запроса
  //
  // Гарантия остановки:
  //   когда последняя задача переходит в done/failed → hasActiveTasks = false
  //   → эффект перезапускается → return (ранний выход, без clearInterval нужен
  //   потому что предыдущая версия эффекта уже вернула cleanup-функцию)
  const hasActiveTasks = tasks.some(
    t => t.status === "processing" || t.status === "queued"
  );

  useEffect(() => {
    if (!hasActiveTasks) return; // нет активных → нет интервала, нет утечки

    const id = setInterval(() => fetchTasks(search), POLL_INTERVAL);
    return () => clearInterval(id); // ВСЕГДА чистим при перезапуске эффекта
  }, [hasActiveTasks, search]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Действия ─────────────────────────────────────────────────────────────
  const handleAdd = async (formData) => {
    setError(null);
    try {
      const task = await addTask(formData);
      setTasks(prev => [task, ...prev]);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleRegenerate = async (taskId) => {
    try {
      const updated = await regenerateTask(taskId);
      setTasks(prev => prev.map(t => t.id === taskId ? updated : t));
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDelete = async (taskId) => {
    if (!confirm("Удалить задачу из истории?")) return;
    try {
      await deleteTask(taskId);
      setTasks(prev => prev.filter(t => t.id !== taskId));
    } catch (e) {
      setError(e.message);
    }
  };

  const handleViewLetter = async (taskId) => {
    try {
      const { text } = await getLetter(taskId);
      setModal({ type: "letter", taskId, data: text });
    } catch (e) {
      setError(e.message);
    }
  };

  const handleViewFiles = async (taskId) => {
    try {
      const files = await getAllFiles(taskId);
      setModal({ type: "files", taskId, data: files });
    } catch (e) {
      setError(e.message);
    }
  };

  const handleCopyLetter = async (taskId) => {
    try {
      const { text } = await getLetter(taskId);
      await navigator.clipboard.writeText(text);
    } catch (e) {
      setError("Не удалось скопировать: " + e.message);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-950">
      <header className="border-b border-gray-800 bg-gray-900/60 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">Cover Letter Generator</h1>
            <p className="text-xs text-gray-500 mt-0.5">
              Локальная генерация через LLM
              {hasActiveTasks && (
                <span className="ml-2 text-indigo-400 animate-pulse">● обработка...</span>
              )}
            </p>
          </div>
          <input
            type="text"
            placeholder="Поиск по вакансиям..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-60 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5
                       text-sm text-gray-200 placeholder-gray-500
                       focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {error && (
          <div className="bg-red-950/60 border border-red-700 rounded-lg px-4 py-3 text-sm text-red-300 flex justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 ml-4">✕</button>
          </div>
        )}

        <AddVacancy onAdd={handleAdd} />

        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-medium text-gray-300">
              История задач
              {tasks.length > 0 && (
                <span className="ml-2 text-xs text-gray-600 font-normal">{tasks.length} шт.</span>
              )}
            </h2>
          </div>

          {loading ? (
            <div className="text-center py-16 text-gray-600 text-sm">Загрузка...</div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-16 text-gray-600 text-sm">
              {search ? "Ничего не найдено" : "Добавьте первую вакансию выше"}
            </div>
          ) : (
            <TaskList
              tasks={tasks}
              onRegenerate={handleRegenerate}
              onDelete={handleDelete}
              onViewLetter={handleViewLetter}
              onViewFiles={handleViewFiles}
              onCopyLetter={handleCopyLetter}
            />
          )}
        </section>
      </main>

      {modal?.type === "letter" && (
        <LetterModal
          text={modal.data}
          onCopy={() => navigator.clipboard.writeText(modal.data)}
          onClose={() => setModal(null)}
        />
      )}

      {modal?.type === "files" && (
        <FilesDrawer files={modal.data} onClose={() => setModal(null)} />
      )}
    </div>
  );
}

import TaskCard from "./TaskCard.jsx";

export default function TaskList({ tasks, onRegenerate, onDelete, onViewLetter, onViewFiles, onCopyLetter }) {
  return (
    <div className="space-y-3">
      {tasks.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          onRegenerate={() => onRegenerate(task.id)}
          onDelete={() => onDelete(task.id)}
          onViewLetter={() => onViewLetter(task.id)}
          onViewFiles={() => onViewFiles(task.id)}
          onCopyLetter={() => onCopyLetter(task.id)}
        />
      ))}
    </div>
  );
}

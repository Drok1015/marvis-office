type TaskLogProps = {
  lines: string[];
};

export function TaskLog({ lines }: TaskLogProps) {
  return (
    <section className="task-log">
      <h3>任务日志</h3>
      <ul>
        {lines.length === 0 ? <li>等待任务...</li> : null}
        {lines.map((line, index) => (
          <li key={`${line}-${index}`}>{line}</li>
        ))}
      </ul>
    </section>
  );
}

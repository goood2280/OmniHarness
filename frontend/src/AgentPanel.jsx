export default function AgentPanel({ agent, onClose }) {
  if (!agent) return null;
  const state = agent.state || 'idle';
  return (
    <div className="panel">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      <div className="panel-head">
        <span className="panel-emoji">{agent.emoji}</span>
        <div>
          <h2>{agent.name}</h2>
          <div className="meta">
            <span className={`pill pill-${agent.model}`}>{agent.model}</span>
            <span className={`chip chip-state-${state}`}>
              {state === 'working' ? '⚡ working' : state === 'waiting' ? '⏳ waiting' : '💤 idle'}
            </span>
            <span className="chip">{agent.team}</span>
            <span className="chip">{agent.species}</span>
          </div>
        </div>
      </div>

      <p className="desc">{agent.description}</p>

      <h3>TOOLS</h3>
      <ul className="tools">
        {(agent.tools || []).map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>

      <details>
        <summary>System Prompt</summary>
        <pre>{agent.body}</pre>
      </details>
    </div>
  );
}

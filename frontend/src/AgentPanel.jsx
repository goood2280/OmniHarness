import { t } from './i18n';

export default function AgentPanel({ agent, onClose, lang }) {
  if (!agent) return null;
  const state = agent.state || 'idle';
  const stateLabel =
    state === 'working' ? '⚡ ' + t('hud.work', lang).toLowerCase()
    : state === 'waiting' ? '⏳ ' + t('hud.wait', lang).toLowerCase()
    : '💤 ' + t('hud.idle', lang).toLowerCase();

  return (
    <div className="panel">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      <div className="panel-head">
        <span className="panel-emoji">{agent.emoji}</span>
        <div>
          <h2>{agent.name}</h2>
          <div className="meta">
            <span className={`pill pill-${agent.model}`}>{agent.model}</span>
            <span className={`chip chip-state-${state}`}>{stateLabel}</span>
            <span className="chip">{t(`team.${agent.team}`, lang)}</span>
            <span className="chip">{agent.species}</span>
          </div>
        </div>
      </div>

      <p className="desc">{agent.description}</p>

      <h3>{t('panel.tools', lang)}</h3>
      <ul className="tools">
        {(agent.tools || []).map((tool) => (
          <li key={tool}>{tool}</li>
        ))}
      </ul>

      <details>
        <summary>{t('panel.system_prompt', lang)}</summary>
        <pre>{agent.body}</pre>
      </details>
    </div>
  );
}

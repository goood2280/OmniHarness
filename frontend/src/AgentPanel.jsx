import Sprite, { POSE } from './Sprite';
import { t } from './i18n';

// Pose to use in the panel headshot — the standing portrait reads
// best in a small box; falls back to the work pose when the agent is
// actively running so the panel "feels" alive.
function panelPose(state, model) {
  if (state === 'working') return model === 'opus' ? POSE.WORK_OPUS : POSE.WORK_SONNET;
  if (state === 'waiting') return POSE.WAIT;
  return POSE.WAVING;
}

export default function AgentPanel({ agent, onClose, lang }) {
  if (!agent) return null;
  const state = agent.state || 'idle';
  const stateLabel =
    state === 'working' ? '⚡ ' + t('hud.work', lang).toLowerCase()
    : state === 'waiting' ? '⏳ ' + t('hud.wait', lang).toLowerCase()
    : '💤 ' + t('hud.idle', lang).toLowerCase();
  const displayName = t(`agent.${agent.name}`, lang) || agent.name;

  return (
    <div className="panel">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      <div className="panel-head">
        <div className="panel-portrait">
          <Sprite agent={agent} pose={panelPose(state, agent.model)} size={140} />
        </div>
        <div className="panel-head-text">
          <h2>{displayName}</h2>
          <div className="panel-subname">{agent.name}</div>
          <div className="meta">
            <span className={`pill pill-${agent.model}`}>{agent.model}</span>
            <span className={`chip chip-state-${state}`}>{stateLabel}</span>
            <span className="chip">{t(`team.${agent.team}`, lang)}</span>
            <span className="chip">{agent.species}</span>
          </div>
        </div>
      </div>

      {agent.description && <p className="desc">{agent.description}</p>}

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

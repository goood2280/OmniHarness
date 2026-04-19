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

// Reconstruct the on-disk `.claude/agents/<name>.md` view from the
// server-provided fields. Read-only — edits go through the orchestrator
// per the company's change-control rule.
function buildMdView(agent) {
  const lines = ['---'];
  lines.push(`name: ${agent.name}`);
  if (agent.description) lines.push(`description: ${agent.description}`);
  if (agent.model) lines.push(`model: ${agent.model}`);
  if (agent.team) lines.push(`team: ${agent.team}`);
  if (agent.tools?.length) lines.push(`tools: ${agent.tools.join(', ')}`);
  lines.push('---');
  lines.push('');
  lines.push((agent.body || '').trimEnd());
  return lines.join('\n');
}

export default function AgentPanel({ agent, onClose, lang, mode = 'custom' }) {
  if (!agent) return null;
  const state = agent.state || 'idle';
  const stateLabel =
    state === 'working' ? '⚡ ' + t('hud.work', lang).toLowerCase()
    : state === 'waiting' ? '⏳ ' + t('hud.wait', lang).toLowerCase()
    : '💤 ' + t('hud.idle', lang).toLowerCase();
  const displayName = t(`agent.${agent.name}`, lang) || agent.name;
  const isOrchestrator = agent.name === 'orchestrator';
  const isGeneral = mode === 'general';
  const mdView = buildMdView(agent);
  const mdPath = `.claude/agents/${agent.name}.md`;

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
            {!isGeneral && agent.team && <span className="chip">{t(`team.${agent.team}`, lang)}</span>}
            {!isGeneral && agent.species && <span className="chip">{agent.species}</span>}
          </div>
        </div>
      </div>

      {/* General mode is about observing one Claude instance; config
          files and role descriptions aren't meaningful there. Show only
          the live model + running state. */}
      {isGeneral ? null : (
        <>
          {agent.description && (
            <>
              <h3>{lang === 'ko' ? '설명' : 'Description'}</h3>
              <p className="desc">{agent.description}</p>
            </>
          )}

          <h3>{t('panel.tools', lang)}</h3>
          <ul className="tools">
            {(agent.tools || []).map((tool) => (
              <li key={tool}>{tool}</li>
            ))}
            {!agent.tools?.length && (
              <li className="tools-empty">{lang === 'ko' ? '(등록된 도구 없음)' : '(none)'}</li>
            )}
          </ul>

          <div className="md-block">
            <div className="md-block-head">
              <h3>{lang === 'ko' ? '설정 파일' : 'Config file'}</h3>
              <code className="md-path">{mdPath}</code>
            </div>
            <div className="md-edit-notice">
              {isOrchestrator
                ? (lang === 'ko'
                    ? '🔑 이 파일은 오케스트레이터 자신의 설정입니다. 수정은 사용자가 직접 합니다.'
                    : '🔑 This is the orchestrator\'s own config. Only the user edits it directly.')
                : (lang === 'ko'
                    ? '🔒 읽기 전용 — 수정은 오케스트레이터만 가능합니다. 인사팀(hr)은 이 에이전트의 추가·삭제를 제안할 수 있지만, 오케스트레이터와 해당 팀 리드의 만장일치 승인이 필요하며, 의견이 갈리면 오케스트레이터가 최종 결정합니다.'
                    : '🔒 Read-only — only the orchestrator edits this file. HR can propose adding or retiring this agent, but needs unanimous approval from the orchestrator and the team lead. Tie-breaker: orchestrator.')}
            </div>
            <pre className="md-content">{mdView}</pre>
          </div>
        </>
      )}
    </div>
  );
}

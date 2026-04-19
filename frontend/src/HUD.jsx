import { t, LANG_OPTIONS } from './i18n';

export default function HUD({
  agentCount,
  opus,
  sonnet,
  haiku,
  working,
  waiting,
  idle,
  cost,
  lang,
  onLangChange,
  onGuideOpen,
  onKeysOpen,
  mode = 'custom',
  onModeChange,
  onSwitchProject,
  hasActiveProject,
  auditStatus,
}) {
  const auditDone = auditStatus?.completed_coordinators;
  const auditEvery = auditStatus?.audit_every;
  const auditChip =
    typeof auditDone === 'number' && typeof auditEvery === 'number' && auditEvery > 0
      ? `${t('audit.hud_chip', lang)} ${auditDone % auditEvery}/${auditEvery}`
      : null;
  return (
    <div className="hud">
      <div className="hud-left">
        {hasActiveProject && onSwitchProject && (
          <button className="switch-project-btn" onClick={onSwitchProject} title={t('hud.switch_project', lang)}>
            ⇆ {t('hud.switch_project', lang)}
          </button>
        )}
        {mode === 'custom' && (
          <>
            <span className="sep">|</span>
            <span>{t('hud.agents', lang)}: {agentCount}</span>
            <span className="state state-working">⚡ {t('hud.work', lang)} {working}</span>
            <span className="state state-idle">💤 {t('hud.wait', lang)} {waiting + idle}</span>
            {auditChip && (
              <span className="state state-audit" title={auditChip}>{auditChip}</span>
            )}
          </>
        )}
      </div>
      <div className="hud-center">
        <span className="cost">
          💰 {t('hud.cost', lang)} <span className="cost-num">${(cost || 0).toFixed(4)}</span>
        </span>
      </div>
      <div className="hud-right">
        {mode === 'custom' && (
          <>
            <span className="pill pill-opus">OPUS {opus}</span>
            <span className="pill pill-sonnet">SONNET {sonnet}</span>
            <span className="pill pill-haiku">HAIKU {haiku || 0}</span>
          </>
        )}
        <button className="guide-btn" onClick={onGuideOpen} title="Claude Code CLI / Bedrock 설정">
          ☁ {t('guide.button', lang)}
        </button>
        {onKeysOpen && (
          <button
            className="guide-btn keys-btn"
            onClick={onKeysOpen}
            title={t('keys.title', lang)}
            data-testid="hud-keys-btn"
          >
            🔑 {t('keys.button', lang)}
          </button>
        )}
        <div className="lang-switch" role="group" aria-label={t('hud.lang', lang)}>
          {LANG_OPTIONS.map((opt) => (
            <button
              key={opt.code}
              className={'lang-btn' + (lang === opt.code ? ' active' : '')}
              onClick={() => onLangChange && onLangChange(opt.code)}
            >
              {opt.code.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

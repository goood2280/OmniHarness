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
}) {
  return (
    <div className="hud">
      <div className="hud-left">
        <span>{t('hud.agents', lang)}: {agentCount}</span>
        <span className="sep">|</span>
        <span className="state state-working">⚡ {t('hud.work', lang)} {working}</span>
        <span className="state state-waiting">⏳ {t('hud.wait', lang)} {waiting}</span>
        <span className="state state-idle">💤 {t('hud.idle', lang)} {idle}</span>
      </div>
      <div className="hud-center">
        <span className="cost">
          💰 {t('hud.cost', lang)} <span className="cost-num">${(cost || 0).toFixed(4)}</span>
        </span>
      </div>
      <div className="hud-right">
        <span className="pill pill-opus">OPUS {opus}</span>
        <span className="pill pill-sonnet">SONNET {sonnet}</span>
        <span className="pill pill-haiku">HAIKU {haiku || 0}</span>
        <button className="guide-btn" onClick={onGuideOpen} title="Bedrock 환경 설정 가이드">
          ☁ {t('guide.button', lang)}
        </button>
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

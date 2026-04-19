// ModeSelect.jsx — first-visit popup. Two big choices:
//  - General : session-level trace viewer for how Claude Code uses
//              subagents/tools/skills while answering a query.
//  - Custom  : pick or create a project, set its team, then open the
//              office floor-plan.

import { t } from './i18n';

export default function ModeSelect({ onChoose, lang }) {
  return (
    <div className="mode-select-overlay">
      <div className="mode-select-card">
        <h1>OmniHarness</h1>
        <p className="mode-select-sub">{t('mode.hello', lang)}</p>

        <div className="mode-select-grid">
          <button className="mode-tile" onClick={() => onChoose('general')}>
            <div className="mode-tile-icon">🧭</div>
            <h2>{t('mode.general', lang)}</h2>
            <p>{t('mode.general_desc', lang)}</p>
            <span className="mode-tile-hint">{t('mode.general_hint', lang)}</span>
          </button>

          <button className="mode-tile" onClick={() => onChoose('custom')}>
            <div className="mode-tile-icon">🏢</div>
            <h2>{t('mode.custom', lang)}</h2>
            <p>{t('mode.custom_desc', lang)}</p>
            <span className="mode-tile-hint">{t('mode.custom_hint', lang)}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

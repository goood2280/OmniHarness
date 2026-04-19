// MissionBanner.jsx — compact strip at the top showing the active mission.
// Clicking opens the onboarding wizard to re-edit (the wizard handles save).

import { t } from './i18n';

export default function MissionBanner({ mission, onEdit, lang }) {
  if (!mission || mission.placeholder || !mission.team_confirmed) return null;

  return (
    <div className="mission-banner" onClick={onEdit} title={t('mission.edit_tooltip', lang)}>
      <div className="mission-label">{t('mission.label', lang)}</div>
      <div className="mission-content">
        {mission.company && (
          <>
            <span className="mission-chip mission-chip-company">🏢 {mission.company}</span>
            <span className="mission-sep">/</span>
          </>
        )}
        <span className="mission-chip">{mission.industry || '—'}</span>
        {mission.philosophy && <span className="mission-sep">·</span>}
        {mission.philosophy && <span className="mission-philo">{mission.philosophy}</span>}
        <span className="mission-sep">→</span>
        <span className="mission-goal">{mission.goal || '—'}</span>
      </div>
      <button className="mission-edit-btn" onClick={(e) => { e.stopPropagation(); onEdit(); }}>
        ✎
      </button>
    </div>
  );
}

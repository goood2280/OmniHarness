import { useEffect, useState } from 'react';
import { t } from './i18n';

export default function MissionBanner({ mission, onSave, lang }) {
  const needsInit = !mission || mission.placeholder;
  const [editing, setEditing] = useState(needsInit);
  const [form, setForm] = useState(
    mission || { company: '', industry: '', philosophy: '', goal: '' }
  );

  useEffect(() => {
    if (mission) setForm(mission);
    if (mission && mission.placeholder) setEditing(true);
  }, [mission]);

  const submit = async () => {
    const body = {
      company: (form.company || '').trim(),
      industry: (form.industry || '').trim(),
      philosophy: (form.philosophy || '').trim(),
      goal: (form.goal || '').trim(),
    };
    // company + industry + goal all required
    if (!body.company || !body.industry || !body.goal) return;
    const r = await fetch('/api/mission', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (r.ok) {
      const saved = await r.json();
      onSave(saved);
      setEditing(false);
    }
  };

  if (needsInit || editing) {
    return (
      <div className={needsInit ? 'mission-overlay' : 'mission-edit'}>
        <div className="mission-card">
          <h2>{t('mission.modal_title', lang)}</h2>
          <p className="mission-hint">{t('mission.hint', lang)}</p>

          <label>
            <span>{t('mission.company', lang)} <em>*</em></span>
            <input
              value={form.company || ''}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
              placeholder={t('mission.company_ph', lang)}
            />
          </label>

          <label>
            <span>{t('mission.industry', lang)} <em>*</em></span>
            <input
              value={form.industry || ''}
              onChange={(e) => setForm({ ...form, industry: e.target.value })}
              placeholder={t('mission.industry_ph', lang)}
            />
          </label>

          <label>
            <span>{t('mission.philosophy', lang)}</span>
            <input
              value={form.philosophy || ''}
              onChange={(e) => setForm({ ...form, philosophy: e.target.value })}
              placeholder={t('mission.philosophy_ph', lang)}
            />
          </label>

          <label>
            <span>{t('mission.goal', lang)} <em>*</em></span>
            <input
              value={form.goal || ''}
              onChange={(e) => setForm({ ...form, goal: e.target.value })}
              placeholder={t('mission.goal_ph', lang)}
            />
          </label>

          <div className="mission-actions">
            {!needsInit && (
              <button className="btn-ghost" onClick={() => setEditing(false)}>
                {t('mission.cancel', lang)}
              </button>
            )}
            <button className="btn-primary" onClick={submit}>
              {t('mission.save', lang)}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mission-banner" onClick={() => setEditing(true)} title={t('mission.edit_tooltip', lang)}>
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
      <button className="mission-edit-btn" onClick={(e) => { e.stopPropagation(); setEditing(true); }}>
        ✎
      </button>
    </div>
  );
}

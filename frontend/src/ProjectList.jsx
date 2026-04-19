// ProjectList.jsx — shown in custom mode when no project is active.
// Lists existing projects and lets the user pick one or create a new one.

import { useEffect, useState } from 'react';
import { t, LANG_OPTIONS } from './i18n';

export default function ProjectList({ onOpen, onBack, lang, setLang }) {
  const [projects, setProjects] = useState([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ company: '', industry: '', philosophy: '', goal: '' });
  const [busy, setBusy] = useState(false);

  const load = () =>
    fetch('/api/projects')
      .then((r) => r.json())
      .then((d) => setProjects(d.projects || []));

  useEffect(() => { load(); }, []);

  const open = async (slug) => {
    setBusy(true);
    try {
      const r = await fetch(`/api/projects/${slug}/activate`, { method: 'POST' });
      if (r.ok) onOpen(slug);
    } finally {
      setBusy(false);
    }
  };

  const create = async () => {
    if (!form.company.trim() || !form.industry.trim() || !form.goal.trim()) return;
    setBusy(true);
    try {
      const r = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (r.ok) {
        const saved = await r.json();
        onOpen(saved.slug);
      }
    } finally {
      setBusy(false);
    }
  };

  const del = async (slug, company) => {
    if (!confirm(t('plist.confirm_delete', lang).replace('{name}', company || slug))) return;
    setBusy(true);
    try {
      await fetch(`/api/projects/${slug}`, { method: 'DELETE' });
      load();
    } finally {
      setBusy(false);
    }
  };

  if (creating) {
    const valid = form.company.trim() && form.industry.trim() && form.goal.trim();
    return (
      <div className="plist-overlay">
        <div className="plist-card">
          <div className="plist-topbar">
            <button className="plist-back" onClick={() => setCreating(false)}>← {t('plist.back_to_list', lang)}</button>
            <LangPicker lang={lang} setLang={setLang} />
          </div>
          <h2>{t('plist.new_title', lang)}</h2>
          <p className="plist-sub">{t('plist.new_sub', lang)}</p>

          <label>
            <span>{t('mission.company', lang)} <em>*</em></span>
            <input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} placeholder={t('mission.company_ph', lang)} />
          </label>
          <label>
            <span>{t('mission.industry', lang)} <em>*</em></span>
            <input value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} placeholder={t('mission.industry_ph', lang)} />
          </label>
          <label>
            <span>{t('mission.philosophy', lang)}</span>
            <input value={form.philosophy} onChange={(e) => setForm({ ...form, philosophy: e.target.value })} placeholder={t('mission.philosophy_ph', lang)} />
          </label>
          <label>
            <span>{t('mission.goal', lang)} <em>*</em></span>
            <input value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} placeholder={t('mission.goal_ph', lang)} />
          </label>

          <div className="plist-actions">
            <button className="btn-ghost" onClick={() => setCreating(false)}>{t('wiz.back', lang)}</button>
            <button className="btn-primary" disabled={!valid || busy} onClick={create}>
              {busy ? t('wiz.saving', lang) : t('plist.create', lang)}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="plist-overlay">
      <div className="plist-card plist-card-wide">
        <div className="plist-topbar">
          <div />
          <LangPicker lang={lang} setLang={setLang} />
        </div>
        <h2>{t('plist.title', lang)}</h2>
        <p className="plist-sub">{t('plist.sub', lang)}</p>

        <div className="plist-grid">
          <button className="plist-new-tile" onClick={() => setCreating(true)}>
            <span className="plist-new-icon">＋</span>
            <span>{t('plist.new_title', lang)}</span>
          </button>
          {projects.map((p) => (
            <div key={p.slug} className="plist-tile">
              <button className="plist-tile-main" onClick={() => open(p.slug)} disabled={busy}>
                <div className="plist-tile-name">{p.company || p.slug}</div>
                <div className="plist-tile-industry">{p.industry || '—'}</div>
                <div className="plist-tile-goal">{p.goal || ''}</div>
                <div className="plist-tile-meta">
                  <span className={`plist-tile-status ${p.team_confirmed ? 'ready' : 'pending'}`}>
                    {p.team_confirmed ? t('plist.status.ready', lang) : t('plist.status.setup', lang)}
                  </span>
                  {p.team_confirmed && (
                    <span className="plist-tile-counts">
                      dev {p.dev_count} · dom {p.domain_count}
                    </span>
                  )}
                </div>
              </button>
              <button className="plist-tile-delete" onClick={() => del(p.slug, p.company)} title={t('plist.delete', lang)}>✕</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Small inline language picker used on both the list view and the
// create-project form. Reuses the global `.lang-switch` styling from
// the HUD so there's only one visual convention for this control.
function LangPicker({ lang, setLang }) {
  if (!setLang) return null;
  return (
    <div className="lang-switch plist-lang-switch" role="group" aria-label="Language">
      {LANG_OPTIONS.map((opt) => (
        <button
          key={opt.code}
          className={'lang-btn' + (lang === opt.code ? ' active' : '')}
          onClick={() => setLang(opt.code)}
          title={opt.label}
        >
          {opt.code.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

// Evolution.jsx → renamed "Audit" (감사). Shows audit proposals from
// the auditor agent: new_agent, feature, refactor, retire_agent,
// split_agent, parallelize. The user just accepts or rejects; the
// orchestrator acts on the decision.
// (Knowledge base lives in its own top-level tab now — see Knowledge.jsx.)

import { useEffect, useState } from 'react';
import { t } from './i18n';

// Audit-origin proposal kinds — show 🔎 badge on the card.
const AUDIT_KINDS = new Set(['split_agent', 'retire_agent', 'parallelize']);

export default function Evolution({ items, onReload, lang }) {
  const pending = (items || []).filter((e) => e.status === 'proposed');
  const decided = (items || []).filter((e) => e.status !== 'proposed');

  return (
    <div className="evolution">
      <div className="evo-header">
        <h3>{t('evo.title', lang)}</h3>
        <p className="evo-hint">{t('evo.hint', lang)}</p>
      </div>

      <AuditStatusCard onReload={onReload} lang={lang} />

      {!pending.length && !decided.length && (
        <div className="empty"><p>{t('evo.empty', lang)}</p></div>
      )}
      {pending.map((e) => <EvolutionCard key={e.id} e={e} onReload={onReload} lang={lang} />)}
      {decided.length > 0 && <h4 className="evo-decided-head">—</h4>}
      {decided.map((e) => <EvolutionCard key={e.id} e={e} onReload={onReload} lang={lang} />)}
    </div>
  );
}

function AuditStatusCard({ onReload, lang }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = async () => {
    try {
      const r = await fetch('/api/audit/status');
      if (r.ok) {
        const d = await r.json();
        setStatus(d);
      } else {
        setStatus(null);
      }
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const iv = setInterval(load, 5000);
    return () => clearInterval(iv);
  }, []);

  const runAudit = async () => {
    setRunning(true);
    try {
      await fetch('/api/audit/run', { method: 'POST' });
      // Refresh audit status + evolution list.
      await load();
      onReload && onReload();
    } finally {
      setRunning(false);
    }
  };

  const done = status?.completed_coordinators ?? 0;
  const every = status?.audit_every ?? 5;
  const next = status?.next_audit_at_nth ?? (done + (every - (done % every || every)));
  const progressTxt = t('audit.progress', lang)
    .replace('{done}', String(done))
    .replace('{every}', String(every))
    .replace('{next}', String(next));

  return (
    <div className="audit-status-card" data-testid="audit-status-card">
      <div className="audit-status-head">
        <span className="audit-status-title">{t('audit.section_title', lang)}</span>
        <button
          className="btn-primary audit-run-btn"
          onClick={runAudit}
          disabled={running || loading}
        >
          {running ? t('audit.running', lang) : t('audit.run_now', lang)}
        </button>
      </div>
      <div className="audit-status-body">
        {loading ? (
          <span className="audit-status-line muted">{t('audit.loading', lang)}</span>
        ) : status ? (
          <span className="audit-status-line">{progressTxt}</span>
        ) : (
          <span className="audit-status-line muted">{t('audit.unknown', lang)}</span>
        )}
      </div>
    </div>
  );
}

function EvolutionCard({ e, onReload, lang }) {
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  const decide = async (decision) => {
    setBusy(true);
    try {
      const r = await fetch(`/api/evolution/${e.id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, note: note.trim() }),
      });
      if (r.ok) onReload && onReload();
    } finally {
      setBusy(false);
    }
  };

  const kindLabel = t(`evo.kind.${e.kind}`, lang);
  const decided = e.status !== 'proposed';
  const isAuditOrigin = AUDIT_KINDS.has(e.kind);

  return (
    <div className={`evo-card evo-${e.status}${isAuditOrigin ? ' evo-audit-origin' : ''}`}>
      <div className="evo-head">
        {isAuditOrigin && (
          <span
            className="evo-audit-badge"
            title={t('audit.origin_badge', lang)}
          >
            {t('audit.origin_badge', lang)}
          </span>
        )}
        <span className={`evo-kind-chip evo-kind-${e.kind}`}>{kindLabel}</span>
        <span className="evo-agent">by {e.agent}</span>
        <span className="evo-time">{(e.created || '').slice(5, 16).replace('T', ' ')}</span>
      </div>
      <h4 className="evo-title">{e.title}</h4>
      <div className="evo-rationale">
        <span className="evo-rationale-label">💡 {t('evo.rationale', lang)}:</span>
        {e.rationale}
      </div>
      {e.payload && Object.keys(e.payload).length > 0 && (
        <pre className="evo-payload">{JSON.stringify(e.payload, null, 2)}</pre>
      )}
      {!decided ? (
        <div className="evo-decide">
          <input
            className="evo-note-input"
            placeholder={lang === 'ko' ? '결정 메모 (선택)' : 'Decision note (optional)'}
            value={note}
            onChange={(ev) => setNote(ev.target.value)}
          />
          <button className="btn-primary" disabled={busy} onClick={() => decide('accepted')}>
            ✓ {t('evo.accept', lang)}
          </button>
          <button className="btn-ghost" disabled={busy} onClick={() => decide('rejected')}>
            ✕ {t('evo.reject', lang)}
          </button>
        </div>
      ) : (
        <div className="evo-verdict">
          <span className={`evo-verdict-chip evo-verdict-${e.status}`}>
            {e.status === 'accepted' ? t('evo.accepted', lang) : t('evo.rejected', lang)}
          </span>
          {e.decision_note && <span className="evo-verdict-note"> — {e.decision_note}</span>}
        </div>
      )}
    </div>
  );
}

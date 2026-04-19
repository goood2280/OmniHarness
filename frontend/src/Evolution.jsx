// Evolution.jsx → renamed "Audit" (감사). Shows audit proposals from
// the auditor agent: new_agent, feature, refactor, retire_agent. The
// user just accepts or rejects; the orchestrator acts on the decision.
// (Knowledge base lives in its own top-level tab now — see Knowledge.jsx.)

import { useState } from 'react';
import { t } from './i18n';

export default function Evolution({ items, onReload, lang }) {
  const pending = (items || []).filter((e) => e.status === 'proposed');
  const decided = (items || []).filter((e) => e.status !== 'proposed');

  return (
    <div className="evolution">
      <div className="evo-header">
        <h3>{t('evo.title', lang)}</h3>
        <p className="evo-hint">{t('evo.hint', lang)}</p>
      </div>

      {!pending.length && !decided.length && (
        <div className="empty"><p>{t('evo.empty', lang)}</p></div>
      )}
      {pending.map((e) => <EvolutionCard key={e.id} e={e} onReload={onReload} lang={lang} />)}
      {decided.length > 0 && <h4 className="evo-decided-head">—</h4>}
      {decided.map((e) => <EvolutionCard key={e.id} e={e} onReload={onReload} lang={lang} />)}
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

  return (
    <div className={`evo-card evo-${e.status}`}>
      <div className="evo-head">
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

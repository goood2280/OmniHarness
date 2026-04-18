import { useState, useMemo } from 'react';
import { t } from './i18n';

// Map backend status → UI filter bucket.
const BUCKET = {
  new: 'waiting',
  planning: 'waiting',
  in_progress: 'working',
  'in-progress': 'working',
  done: 'done',
  cancelled: 'cancelled',
};

const FILTERS = [
  { id: 'all',       key: 'req.filter.all' },
  { id: 'waiting',   key: 'req.filter.waiting' },
  { id: 'working',   key: 'req.filter.working' },
  { id: 'done',      key: 'req.filter.done' },
  { id: 'cancelled', key: 'req.filter.cancelled' },
];

export default function RequirementInput({ lang, items, onReload }) {
  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filter, setFilter] = useState('all');
  const [open, setOpen] = useState(null);    // id currently shown in detail modal
  const [cancelling, setCancelling] = useState(null);

  const canSubmit = text.trim().length > 0 && !submitting;

  const submit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      const r = await fetch('/api/requirements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() }),
      });
      if (r.ok) { setText(''); onReload && onReload(); }
    } catch { /* silent */ }
    finally { setSubmitting(false); }
  };

  const cancelItem = async (id) => {
    if (!window.confirm(t('req.confirm_cancel', lang))) return;
    setCancelling(id);
    try {
      await fetch(`/api/requirements/${id}/cancel`, { method: 'POST' });
      onReload && onReload();
      setOpen(null);
    } finally { setCancelling(null); }
  };

  // Bucket counts for filter pills
  const counts = useMemo(() => {
    const c = { all: items.length, waiting: 0, working: 0, done: 0, cancelled: 0 };
    for (const it of items) {
      const b = BUCKET[it.status] || 'waiting';
      c[b] = (c[b] || 0) + 1;
    }
    return c;
  }, [items]);

  const filtered = useMemo(() => {
    if (filter === 'all') return items;
    return items.filter((it) => (BUCKET[it.status] || 'waiting') === filter);
  }, [items, filter]);

  const openItem = items.find((it) => it.id === open) || null;

  return (
    <div className="req-card">
      <div className="req-head">
        <h3>🎯 {t('req.title', lang)}</h3>
        <p className="muted">{t('req.hint', lang)}</p>
      </div>

      <div className="req-form">
        <textarea
          placeholder={t('req.placeholder', lang)}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button className="btn-primary" disabled={!canSubmit} onClick={submit}>
          {submitting ? t('req.sending', lang) : t('req.send', lang)}
        </button>
      </div>

      <div className="req-filters" role="tablist">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            role="tab"
            aria-selected={filter === f.id}
            className={'req-filter' + (filter === f.id ? ' active' : '')}
            onClick={() => setFilter(f.id)}
          >
            {t(f.key, lang)}
            <span className="req-filter-count">{counts[f.id] || 0}</span>
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="muted" style={{ padding: '16px 4px' }}>{t('req.empty', lang)}</p>
      ) : (
        <ul className="req-list">
          {filtered.map((it) => {
            const bucket = BUCKET[it.status] || 'waiting';
            return (
              <li
                key={it.id}
                className={`req-item req-bucket-${bucket}`}
                onClick={() => setOpen(it.id)}
              >
                <span className={`req-bucket-dot req-bucket-dot-${bucket}`} />
                <span className="req-text">{(it.text || '').slice(0, 160)}</span>
                <span className={`req-chip req-chip-${it.status}`}>
                  {t(`req.status.${it.status}`, lang)}
                </span>
                {bucket === 'waiting' && (
                  <button
                    className="req-cancel"
                    onClick={(e) => { e.stopPropagation(); cancelItem(it.id); }}
                    disabled={cancelling === it.id}
                  >
                    {cancelling === it.id ? t('req.cancelling', lang) : '✕ ' + t('req.cancel', lang)}
                  </button>
                )}
                <span className="req-time">
                  {it.created ? it.created.slice(11, 19) : ''}
                </span>
              </li>
            );
          })}
        </ul>
      )}

      {openItem && (
        <div className="req-detail-overlay" onClick={() => setOpen(null)}>
          <div className="req-detail-card" onClick={(e) => e.stopPropagation()}>
            <button className="req-detail-close" onClick={() => setOpen(null)}>×</button>
            <div className="req-detail-head">
              <span className={`req-chip req-chip-${openItem.status}`}>
                {t(`req.status.${openItem.status}`, lang)}
              </span>
              <span className="muted" style={{ marginLeft: 'auto' }}>
                {openItem.created?.slice(0, 19).replace('T', ' ')}
              </span>
            </div>
            <p className="req-detail-text">{openItem.text}</p>
            <div className="req-detail-meta">
              <span className="chip">assignee: {openItem.assigned_to || 'orchestrator'}</span>
              <span className="chip">from: {openItem.from || 'user'}</span>
              <span className="chip">id: {openItem.id}</span>
            </div>
            {(BUCKET[openItem.status] || 'waiting') === 'waiting' && (
              <div className="req-detail-actions">
                <button
                  className="btn-danger"
                  onClick={() => cancelItem(openItem.id)}
                  disabled={cancelling === openItem.id}
                >
                  {cancelling === openItem.id ? t('req.cancelling', lang) : '✕ ' + t('req.cancel', lang)}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

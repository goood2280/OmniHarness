import { useEffect, useMemo, useState } from 'react';
import { t } from './i18n';

// Minimal markdown-ish renderer for orchestrator-authored report bodies.
// After the 2026-04-19 slim, the separate reporter agent is gone and
// the orchestrator writes these summaries itself.
function renderMd(md) {
  if (!md) return null;
  const lines = md.split(/\r?\n/);
  const out = [];
  let i = 0;
  const inline = (s) => {
    let safe = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    safe = safe.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    safe = safe.replace(/`([^`]+)`/g, '<code>$1</code>');
    return safe;
  };
  while (i < lines.length) {
    const line = lines[i];
    if (/^\s*$/.test(line)) { i++; continue; }
    if (/^##\s+/.test(line)) {
      out.push(<h4 key={i} className="md-h">{line.replace(/^##\s+/, '')}</h4>);
      i++; continue;
    }
    if (/^#\s+/.test(line)) {
      out.push(<h3 key={i} className="md-h1">{line.replace(/^#\s+/, '')}</h3>);
      i++; continue;
    }
    if (/^>\s?/.test(line)) {
      out.push(
        <blockquote key={i} className="md-quote"
          dangerouslySetInnerHTML={{ __html: inline(line.replace(/^>\s?/, '')) }} />
      );
      i++; continue;
    }
    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s+/, ''));
        i++;
      }
      out.push(
        <ul key={`ul-${i}`} className="md-ul">
          {items.map((it, k) => (
            <li key={k} dangerouslySetInnerHTML={{ __html: inline(it) }} />
          ))}
        </ul>
      );
      continue;
    }
    const buf = [];
    while (i < lines.length && !/^\s*$/.test(lines[i]) && !/^(#|>|[-*]\s)/.test(lines[i])) {
      buf.push(lines[i]);
      i++;
    }
    out.push(
      <p key={`p-${i}`} className="md-p"
        dangerouslySetInnerHTML={{ __html: inline(buf.join(' ')) }} />
    );
  }
  return out;
}

// Short "2 hours ago" style — pragmatic, ko/en.
function relativeTime(iso, lang) {
  if (!iso) return '';
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return iso.slice(11, 19);
  const diff = Math.max(0, Date.now() - then);
  const s = Math.floor(diff / 1000);
  const isKo = lang !== 'en';
  if (s < 60) return isKo ? '방금 전' : 'just now';
  const m = Math.floor(s / 60);
  if (m < 60) return isKo ? `${m}분 전` : `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return isKo ? `${h}시간 전` : `${h}h ago`;
  const d = Math.floor(h / 24);
  return isKo ? `${d}일 전` : `${d}d ago`;
}

// First non-empty non-heading line → one-sentence summary preview.
function preview(md) {
  if (!md) return '';
  const lines = md.split(/\r?\n/);
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (/^#/.test(line)) continue;
    if (/^>/.test(line)) continue;
    return line.replace(/^[-*]\s+/, '').replace(/\*\*(.+?)\*\*/g, '$1').slice(0, 140);
  }
  return '';
}

export default function Reports({ items, onReload, lang }) {
  const [selected, setSelected] = useState(null);
  const [bodies, setBodies] = useState({}); // id → body JSON, so list previews work too

  useEffect(() => {
    if (!selected && items.length) setSelected(items[0].id);
  }, [items, selected]);

  // Fetch body for currently-selected report AND lazily for preview lines of the list.
  useEffect(() => {
    if (!selected || bodies[selected]) return;
    fetch(`/api/reports/${selected}`).then((r) => r.json()).then((b) => {
      setBodies((prev) => ({ ...prev, [selected]: b }));
    });
  }, [selected, bodies]);

  // Also prefetch body for the TOP 5 so the list previews appear.
  useEffect(() => {
    const needed = items.slice(0, 5).filter((r) => !bodies[r.id]);
    needed.forEach((r) => {
      fetch(`/api/reports/${r.id}`).then((rr) => rr.json())
        .then((b) => setBodies((prev) => ({ ...prev, [r.id]: b })));
    });
  }, [items]); // eslint-disable-line react-hooks/exhaustive-deps

  const current = bodies[selected];
  const rendered = useMemo(() => renderMd(current && current.content_md), [current]);
  const hasStructured = !!(current && (current.summary || (current.sections || []).length > 0 || Object.keys(current.metrics || {}).length > 0));

  if (!items.length) {
    return (
      <div className="empty">
        <p>{t('rep.empty_title', lang)}</p>
        <p className="muted">{t('rep.empty_body', lang)}</p>
      </div>
    );
  }

  return (
    <div className="reports">
      <div className="report-list">
        {items.map((r) => {
          const b = bodies[r.id];
          const prev = b ? preview(b.content_md) : '';
          return (
            <div
              key={r.id}
              className={selected === r.id ? 'report-item active' : 'report-item'}
              onClick={() => setSelected(r.id)}
            >
              <div className="report-item-head">
                <span className="report-item-icon">📄</span>
                <span className="report-item-title">{r.title}</span>
              </div>
              <div className="report-item-meta">
                <span className="report-time">🕒 {relativeTime(r.created, lang)}</span>
                <span className="report-sep">·</span>
                <span className="report-author-chip">{r.author}</span>
              </div>
              {prev && <div className="report-item-preview">{prev}</div>}
            </div>
          );
        })}
      </div>
      <div className="report-body">
        {current ? (
          <>
            <div className={`report-head report-sev-${current.severity || 'info'}`}>
              <h3 className="report-big-title">{current.title}</h3>
              <div className="report-head-meta">
                <span className="chip chip-author">👤 {current.author}</span>
                <span className="chip">🕒 {relativeTime(current.created, lang)}</span>
                <span className="chip">{(current.created || '').slice(0, 19).replace('T', ' ')}</span>
                {(current.tags || []).map((tag) => (
                  <span key={tag} className="chip chip-tag">#{tag}</span>
                ))}
              </div>
            </div>

            {hasStructured ? (
              <div className="report-structured">
                {current.summary && (
                  <div className="report-summary">
                    <span className="report-summary-label">📌 {lang === 'ko' ? '요약' : 'Summary'}</span>
                    <p>{current.summary}</p>
                  </div>
                )}

                {Object.keys(current.metrics || {}).length > 0 && (
                  <div className="report-metrics">
                    {Object.entries(current.metrics).map(([k, v]) => (
                      <div key={k} className="report-metric">
                        <span className="report-metric-key">{k}</span>
                        <span className="report-metric-val">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {(current.sections || []).map((sec, i) => (
                  <section key={i} className="report-section">
                    <h4 className="report-section-heading">{sec.heading}</h4>
                    {sec.metric && (
                      <div className="report-section-metric">{sec.metric}</div>
                    )}
                    {sec.body && (
                      <div className="report-md">{renderMd(sec.body)}</div>
                    )}
                    {(sec.bullets || []).length > 0 && (
                      <ul className="md-ul">
                        {sec.bullets.map((b, j) => <li key={j}>{b}</li>)}
                      </ul>
                    )}
                  </section>
                ))}

                {/* Always include the legacy markdown body too, when present */}
                {current.content_md && (
                  <details className="report-raw-md">
                    <summary>{lang === 'ko' ? '원본 마크다운' : 'Raw markdown'}</summary>
                    <div className="report-md">{rendered}</div>
                  </details>
                )}
              </div>
            ) : (
              <div className="report-md">{rendered}</div>
            )}
          </>
        ) : (
          <div className="empty"><p className="muted">{t('rep.select_hint', lang)}</p></div>
        )}
      </div>
    </div>
  );
}

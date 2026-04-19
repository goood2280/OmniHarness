// Questions.jsx — bidirectional translation pipeline visible to the user.
//
//   Agent raw (technical)
//      → orchestrator rewrites it in plain Korean ("pending_user")
//      → user answers freely ("pending_answer_translation")
//      → orchestrator restates it back for the agent ("answered")
//
// After the 2026-04-19 slim, the mgmt-lead translator agent is gone —
// the orchestrator writes both sides of the translation directly.

import { useState } from 'react';
import { t } from './i18n';

export default function Questions({ items, onReload, lang }) {
  const active = (items || []).filter((q) => q.status !== 'answered');
  if (!active.length) {
    return (
      <div className="empty">
        <p>{t('q.empty_title', lang)}</p>
        <p className="muted">{t('q.empty_body', lang)}</p>
        <p className="muted q-empty-chat-hint">{t('q.empty_chat_hint', lang)}</p>
      </div>
    );
  }
  return (
    <div className="questions">
      <div className="q-chat-tip">{t('q.chat_tip', lang)}</div>
      {active.map((q) => (
        <QuestionCard key={q.id} q={q} onReload={onReload} lang={lang} />
      ))}
    </div>
  );
}

function QuestionCard({ q, onReload, lang }) {
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const statusLabel = {
    pending_translation: t('q.status_pending_translation', lang),
    pending_user: t('q.status_pending_user', lang),
    pending_answer_translation: t('q.status_pending_answer_translation', lang),
    answered: t('q.status_answered', lang),
  }[q.status] || q.status;

  const submit = async () => {
    if (!answer.trim()) return;
    setSubmitting(true);
    try {
      const r = await fetch(`/api/questions/${q.id}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer: answer.trim() }),
      });
      if (r.ok) {
        setAnswer('');
        onReload && onReload();
      }
    } finally {
      setSubmitting(false);
    }
  };

  const shortId = q.short_id || '';
  const placeholder = shortId
    ? t('q.answer_ph_with_id', lang).replace('{sid}', shortId)
    : t('q.answer_ph', lang);

  return (
    <div className={`q-card q-${q.status}`}>
      <div className="q-head">
        {shortId && <span className="q-short-id" title="short id">{shortId}</span>}
        <span className="q-agent">{q.agent}</span>
        <span className="q-status">{statusLabel}</span>
        <span className="q-time">{(q.created || '').slice(11, 19)}</span>
      </div>

      {/* orchestrator's user-facing rewrite */}
      {q.translated ? (
        <div className="q-translated">
          <span className="q-arrow q-arrow-in">orchestrator →</span>
          {q.translated}
        </div>
      ) : (
        <div className="q-pending-trans">{t('q.translating', lang)}</div>
      )}

      <details className="q-raw">
        <summary>{t('q.raw_summary', lang)} — {q.agent}</summary>
        <p>{q.raw}</p>
      </details>

      {q.status === 'pending_user' && (
        <div className="q-answer-form">
          <textarea
            placeholder={placeholder}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
          <button className="btn-primary" disabled={submitting || !answer.trim()} onClick={submit}>
            {submitting ? t('q.sending', lang) : t('q.send', lang)}
          </button>
        </div>
      )}

      {q.answer && (
        <div className="q-answer">
          <span className="q-answer-label">{t('q.my_answer', lang)}:</span> {q.answer}
        </div>
      )}

      {q.status === 'pending_answer_translation' && (
        <div className="q-answer-translating">
          <span className="q-arrow q-arrow-out">→ {q.agent}</span>
          {t('q.status_pending_answer_translation', lang)}
        </div>
      )}

      {q.answer_structured && (
        <div className="q-structured">
          <span className="q-arrow q-arrow-out">orchestrator → {q.agent}:</span>
          {q.answer_structured}
        </div>
      )}
    </div>
  );
}

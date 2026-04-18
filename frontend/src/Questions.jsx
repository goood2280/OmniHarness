import { useState } from 'react';
import { t } from './i18n';

export default function Questions({ items, onReload, lang }) {
  // 답변 완료된 질문은 목록에서 숨김 — "답을 보낸 질문은 더 이상 안 보이게".
  const active = items.filter((q) => q.status !== 'answered');
  if (!active.length) {
    return (
      <div className="empty">
        <p>{t('q.empty_title', lang)}</p>
        <p className="muted">{t('q.empty_body', lang)}</p>
      </div>
    );
  }
  return (
    <div className="questions">
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

  return (
    <div className={`q-card q-${q.status}`}>
      <div className="q-head">
        <span className="q-agent">{q.agent}</span>
        <span className="q-status">{statusLabel}</span>
        <span className="q-time">{(q.created || '').slice(11, 19)}</span>
      </div>

      {q.translated ? (
        <div className="q-translated">{q.translated}</div>
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
            placeholder={t('q.answer_ph', lang)}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
          <button className="btn-primary" disabled={submitting || !answer.trim()} onClick={submit}>
            {submitting ? t('q.sending', lang) : t('q.send', lang)}
          </button>
        </div>
      )}

      {q.status === 'answered' && (
        <div className="q-answer">
          <span className="q-answer-label">{t('q.my_answer', lang)}</span> {q.answer}
        </div>
      )}
    </div>
  );
}

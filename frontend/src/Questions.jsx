import { useState } from 'react';

export default function Questions({ items, onReload }) {
  if (!items.length) {
    return (
      <div className="empty">
        <p>대기 중인 질문이 없습니다.</p>
        <p className="muted">
          에이전트가 개발 중 모호한 결정을 만나면, 경영지원팀 lead가 이해하기 쉬운
          언어로 풀어서 여기에 질문이 올라옵니다. 답변하면 앱 개발에 즉시 반영됩니다.
        </p>
      </div>
    );
  }
  return (
    <div className="questions">
      {items.map((q) => (
        <QuestionCard key={q.id} q={q} onReload={onReload} />
      ))}
    </div>
  );
}

function QuestionCard({ q, onReload }) {
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const statusLabel = {
    pending_translation: '🔄 경영지원팀에서 풀어서 쓰는 중',
    pending_user: '💬 당신의 답변이 필요합니다',
    answered: '✅ 답변 완료',
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
        <span className="q-time">{q.created.slice(11, 19)}</span>
      </div>

      {q.translated ? (
        <div className="q-translated">{q.translated}</div>
      ) : (
        <div className="q-pending-trans">경영지원팀이 번역 중입니다…</div>
      )}

      <details className="q-raw">
        <summary>원문 (에이전트가 쓴 기술적 설명) — {q.agent}</summary>
        <p>{q.raw}</p>
      </details>

      {q.status === 'pending_user' && (
        <div className="q-answer-form">
          <textarea
            placeholder="답변을 적으세요. 간단해도 됩니다. (예: A, 또는 '기본값 7일로 가시죠')"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
          <button className="btn-primary" disabled={submitting || !answer.trim()} onClick={submit}>
            {submitting ? '전송 중…' : '답변 보내기'}
          </button>
        </div>
      )}

      {q.status === 'answered' && (
        <div className="q-answer">
          <span className="q-answer-label">내 답변:</span> {q.answer}
        </div>
      )}
    </div>
  );
}

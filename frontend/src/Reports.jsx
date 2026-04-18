import { useEffect, useState } from 'react';

export default function Reports({ items, onReload }) {
  const [selected, setSelected] = useState(null);
  const [body, setBody] = useState(null);

  useEffect(() => {
    if (!selected) {
      setBody(null);
      return;
    }
    fetch(`/api/reports/${selected}`)
      .then((r) => r.json())
      .then(setBody);
  }, [selected]);

  if (!items.length) {
    return (
      <div className="empty">
        <p>발행된 보고서가 없습니다.</p>
        <p className="muted">
          의미있는 변경점이 모이면 경영지원팀 보고원(reporter)이 자동으로
          보기 좋은 한국어 요약 보고서를 발행합니다.
        </p>
      </div>
    );
  }

  return (
    <div className="reports">
      <div className="report-list">
        {items.map((r) => (
          <div
            key={r.id}
            className={selected === r.id ? 'report-item active' : 'report-item'}
            onClick={() => setSelected(r.id)}
          >
            <div className="report-title">{r.title}</div>
            <div className="report-meta">
              <span>{r.author}</span>
              <span>·</span>
              <span>{r.created.slice(0, 19).replace('T', ' ')}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="report-body">
        {body ? (
          <>
            <h3>{body.title}</h3>
            <div className="report-meta">
              {body.author} · {body.created.slice(0, 19).replace('T', ' ')}
            </div>
            <pre>{body.content_md}</pre>
          </>
        ) : (
          <div className="empty"><p className="muted">왼쪽에서 보고서를 선택하세요.</p></div>
        )}
      </div>
    </div>
  );
}

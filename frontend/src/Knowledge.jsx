// Knowledge.jsx — standalone "누적 지식" tab. Used to be a sub-tab of
// Evolution; promoted to top-level so the user can see what knowledge
// the team has accumulated and audit it for anomalies.

export default function Knowledge({ items, lang }) {
  const list = items || [];
  if (!list.length) {
    return (
      <div className="empty">
        <p>{lang === 'ko' ? '아직 축적된 지식이 없습니다.' : 'No knowledge accumulated yet.'}</p>
        <p className="muted">
          {lang === 'ko'
            ? '에이전트들이 작업을 진행하면서 인사이트를 기록하면 여기에 쌓입니다. 이상이 있는지 직접 점검할 수 있어요.'
            : 'Insights captured by agents as they work accumulate here so you can spot anomalies.'}
        </p>
      </div>
    );
  }
  return (
    <div className="knowledge-list">
      {list.map((k) => (
        <div key={k.id} className="knowledge-item">
          <div className="knowledge-head">
            <span className="knowledge-agent">{k.agent}</span>
            <span className="knowledge-topic">{k.topic}</span>
            <span className="knowledge-time">{(k.created || '').slice(5, 16).replace('T', ' ')}</span>
          </div>
          <p className="knowledge-insight">{k.insight}</p>
        </div>
      ))}
    </div>
  );
}

const KIND_ICON = {
  state: '⚡',
  tool: '🔧',
  invoke: '▶',
  complete: '✓',
  question: '❓',
  report: '📊',
  'user-prompt': '🗣',
  boot: '🚀',
  demo: '🎬',
  mission: '🎯',
  error: '⚠️',
};

export default function ActivityLog({ events }) {
  if (!events.length) {
    return (
      <div className="empty">
        <p>아직 기록이 없습니다.</p>
        <p className="muted">
          FabCanvas.ai 에서 Claude Code 로 작업하시면 실시간 로그가 여기에 쌓입니다.<br/>
          상단 우측 <b>DEMO</b> 토글로 시뮬레이션을 볼 수 있습니다.
        </p>
      </div>
    );
  }
  return (
    <div className="activity">
      {events.map((e) => (
        <div key={e.id} className={`act-row act-${e.kind}`}>
          <span className="act-ts">{e.ts.slice(11, 19)}</span>
          <span className="act-icon">{KIND_ICON[e.kind] || '·'}</span>
          <span className="act-agent">{e.agent}</span>
          <span className="act-detail">{e.detail}</span>
        </div>
      ))}
    </div>
  );
}

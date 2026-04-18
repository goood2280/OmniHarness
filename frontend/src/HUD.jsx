export default function HUD({
  agentCount,
  morale,
  opus,
  sonnet,
  haiku,
  working,
  waiting,
  idle,
  demo,
  cost,
  onToggleDemo,
}) {
  return (
    <div className="hud">
      <div className="hud-left">
        <span>AGENTS: {agentCount}</span>
        <span className="sep">|</span>
        <span className="state state-working">⚡ WORK {working}</span>
        <span className="state state-waiting">⏳ WAIT {waiting}</span>
        <span className="state state-idle">💤 IDLE {idle}</span>
      </div>
      <div className="hud-center">
        <span className="cost">
          💰 <span className="cost-num">${(cost || 0).toFixed(4)}</span>
        </span>
        <span className="sep">|</span>
        <span style={{ color: '#4caf50' }}>MORALE {morale}%</span>
      </div>
      <div className="hud-right">
        <span className="pill pill-opus">OPUS {opus}</span>
        <span className="pill pill-sonnet">SONNET {sonnet}</span>
        {haiku > 0 && <span className="pill pill-haiku">HAIKU {haiku}</span>}
        <button
          className={demo ? 'demo-btn demo-on' : 'demo-btn demo-off'}
          onClick={() => onToggleDemo && onToggleDemo(!demo)}
          title={demo ? '시뮬레이션 중 — 클릭해서 끄기' : '실제 작업 대기 중 — 클릭해서 시뮬레이션'}
        >
          DEMO {demo ? 'ON' : 'OFF'}
        </button>
        <span>YEAR: 2026</span>
      </div>
    </div>
  );
}

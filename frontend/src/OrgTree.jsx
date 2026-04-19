import { useCallback, useEffect, useRef, useState } from 'react';
import { t } from './i18n';
import SharedSprite, { POSE } from './Sprite';

// ── World + layout (slimmed 2026-04-19) ────────────────────────────
// Roster = orchestrator + dev-lead + 6 reviewers. No mgmt / domain
// clusters any more — domain knowledge lives as markdown reference
// docs rendered by OfficeScene's bookshelf, not here.
const WORLD_W = 1200;
const WORLD_H = 900;
const SPRITE_W = 128;
const SPRITE_H = 128;
const NODE_W = 156;
const NODE_H = 200;
const MIN_ZOOM = 0.4;
const MAX_ZOOM = 2.0;
const ZOOM_STEP = 0.1;
const DRAG_THRESHOLD = 4;

// Positions (world px, CENTER of the node)
const NODE_POS = {
  orchestrator:        { x: 600, y: 140 },

  // DEV — single full-stack agent (no fan-out)
  'dev-lead':          { x: 240, y: 400 },

  // EVAL — 6 reviewers in a 3×2 grid on the right
  'dev-verifier':      { x: 550, y: 400 },
  'ux-reviewer':       { x: 700, y: 400 },
  'security-auditor':  { x: 850, y: 400 },
  'user-role-tester':  { x: 550, y: 640 },
  'admin-role-tester': { x: 700, y: 640 },
  'domain-researcher': { x: 850, y: 640 },
};

// Team clusters — sized to wrap the live nodes.
const CLUSTERS = [
  { id: 'dev',  x: 140, y: 310, w: 240, h: 210, accent: '#7cc7e8' },
  { id: 'eval', x: 470, y: 310, w: 480, h: 450, accent: '#ff9b9b' },
];

// Connectors: orchestrator → dev-lead + orchestrator → each reviewer
// (visually the orchestrator sits above both columns).
const CONNECTORS = [
  ['orchestrator', 'dev-lead'],
  ['orchestrator', 'dev-verifier'],
  ['orchestrator', 'ux-reviewer'],
  ['orchestrator', 'security-auditor'],
  ['orchestrator', 'user-role-tester'],
  ['orchestrator', 'admin-role-tester'],
  ['orchestrator', 'domain-researcher'],
];

// OrgTree nodes use the shared sprite-sheet renderer so the Custom
// Project view stays visually in lockstep with the General Viewer's
// HQ + subagent panels. Pose is tied to the agent's live state — same
// mapping rules Sprite uses internally — so a "working" agent in the
// org chart shows the typing pose, "waiting" shows the zZz pose, etc.
function poseForOrg(agent) {
  if (agent?.state === 'working') return agent.model === 'opus' ? POSE.WORK_OPUS : POSE.WORK_SONNET;
  if (agent?.state === 'waiting') return POSE.WAIT;
  // Idle agents in the org chart show the off-desk standing portrait
  // (waving) — that's the cleanest "headshot" pose in the sheet.
  return POSE.WAVING;
}

function Sprite({ agent }) {
  return <SharedSprite agent={agent} pose={poseForOrg(agent)} size={SPRITE_W} />;
}

function bubble(state) {
  if (state === 'working') return { cls: 'working', text: '⚡' };
  if (state === 'waiting') return { cls: 'waiting', text: 'Z' };
  return { cls: '', text: '…' };
}

export default function OrgTree({ topology, onSelect, selected, lang }) {
  const rootRef = useRef(null);
  const [zoom, setZoom] = useState(0.65);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef({ active: false, start: null, moved: 0 });

  const agents = (topology && topology.agents) || [];
  const agentByName = {};
  for (const a of agents) agentByName[a.name] = a;

  // Fit on mount
  useEffect(() => {
    if (!rootRef.current) return;
    const r = rootRef.current.getBoundingClientRect();
    const fit = Math.min(r.width / WORLD_W, r.height / WORLD_H) * 0.98;
    const z = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, fit));
    setZoom(z);
    setPan({ x: (r.width - WORLD_W * z) / 2, y: (r.height - WORLD_H * z) / 2 });
  }, []);

  const onWheel = useCallback((e) => {
    e.preventDefault();
    const r = rootRef.current.getBoundingClientRect();
    const mx = e.clientX - r.left;
    const my = e.clientY - r.top;
    setZoom((prev) => {
      const dir = e.deltaY < 0 ? 1 : -1;
      const next = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, +(prev + dir * ZOOM_STEP).toFixed(2)));
      if (next === prev) return prev;
      setPan((p) => ({
        x: mx - ((mx - p.x) * next) / prev,
        y: my - ((my - p.y) * next) / prev,
      }));
      return next;
    });
  }, []);

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [onWheel]);

  const onPointerDown = (e) => {
    if (e.button !== 0) return;
    dragRef.current = { active: true, start: { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y }, moved: 0 };
    rootRef.current.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e) => {
    if (!dragRef.current.active) return;
    const s = dragRef.current.start;
    const dx = e.clientX - s.x;
    const dy = e.clientY - s.y;
    dragRef.current.moved = Math.max(dragRef.current.moved, Math.hypot(dx, dy));
    setPan({ x: s.px + dx, y: s.py + dy });
  };
  const onPointerUp = (e) => {
    dragRef.current.active = false;
    try { rootRef.current.releasePointerCapture(e.pointerId); } catch {/* ignore */}
  };

  const resetView = useCallback(() => {
    if (!rootRef.current) return;
    const r = rootRef.current.getBoundingClientRect();
    const fit = Math.min(r.width / WORLD_W, r.height / WORLD_H) * 0.98;
    setZoom(fit);
    setPan({ x: (r.width - WORLD_W * fit) / 2, y: (r.height - WORLD_H * fit) / 2 });
  }, []);

  const onDoubleClick = (e) => {
    // Hitting an .org-node bubbles here too; ignore those to let the node's
    // own onDoubleClick handle opening the panel.
    if (e.target.closest('.org-node')) return;
    resetView();
  };

  const handleNodeClick = (agent) => (e) => {
    if (dragRef.current.moved > DRAG_THRESHOLD) return;
    e.stopPropagation();
    onSelect && onSelect(agent);
  };
  const handleNodeDoubleClick = (agent) => (e) => {
    e.stopPropagation();
    // Re-select to ensure the panel is visible (parent decides what that means).
    onSelect && onSelect(agent);
  };

  // 3 connector curves
  const paths = CONNECTORS.map(([parent, child]) => {
    const p = NODE_POS[parent];
    const c = NODE_POS[child];
    if (!p || !c) return null;
    const x1 = p.x;
    const y1 = p.y + SPRITE_H / 2 + 24;
    const x2 = c.x;
    const y2 = c.y - SPRITE_H / 2 - 30;
    const midY = (y1 + y2) / 2;
    const accent = agentByName[child]?.color || '#ffd54f';
    return {
      key: `${parent}-${child}`,
      d: `M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`,
      stroke: accent,
    };
  }).filter(Boolean);

  return (
    <div
      ref={rootRef}
      className="orgtree"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onDoubleClick={onDoubleClick}
    >
      <button className="orgtree-reset" onClick={resetView} title="맞춤">⌂</button>
      <div
        className="orgtree-world"
        style={{
          width: WORLD_W,
          height: WORLD_H,
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
        }}
      >
        {/* Team cluster boxes */}
        {CLUSTERS.map((c) => (
          <div
            key={c.id}
            className={`org-cluster cluster-${c.id}`}
            style={{ left: c.x, top: c.y, width: c.w, height: c.h, borderColor: c.accent }}
          >
            <div className="org-cluster-label" style={{ background: c.accent }}>
              {t(`team.${c.id}`, lang)} · {agents.filter((a) => a.team === c.id).length}
            </div>
          </div>
        ))}

        {/* 3 connectors */}
        <svg
          className="org-connector"
          width={WORLD_W}
          height={WORLD_H}
          style={{ position: 'absolute', left: 0, top: 0, pointerEvents: 'none' }}
        >
          {paths.map((p) => (
            <path
              key={p.key}
              d={p.d}
              fill="none"
              stroke={p.stroke}
              strokeOpacity={0.75}
              strokeWidth={3}
              strokeLinecap="round"
            />
          ))}
        </svg>

        {/* Nodes */}
        {agents.map((agent) => {
          const pos = NODE_POS[agent.name];
          if (!pos) return null;
          const state = agent.state || 'idle';
          const b = bubble(state);
          const isSelected = selected && selected.name === agent.name;
          const displayName = t(`agent.${agent.name}`, lang) || agent.name;
          return (
            <div
              key={agent.name}
              className={`org-node state-${state}${isSelected ? ' selected' : ''}`}
              style={{
                left: pos.x - NODE_W / 2,
                top: pos.y - NODE_H / 2,
                width: NODE_W,
                height: NODE_H,
              }}
              onClick={handleNodeClick(agent)}
              onDoubleClick={handleNodeDoubleClick(agent)}
              title={`${displayName} · ${agent.model}`}
            >
              {agent.name === 'orchestrator' && <div className="org-node-crown">👑</div>}
              <div className={`org-node-bubble ${b.cls}`}>{b.text}</div>
              <div className="org-node-sprite"><Sprite agent={agent} /></div>
              <div className="org-node-label">
                <span className="name">{displayName}</span>
                <span className="provider">anthropic · {agent.model}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// OfficeScene.jsx — SVG office floor-plan.
// One room per team (orchestrator HQ on top, 3 leads in a strip below,
// then mgmt · eval · dev side-by-side, then domain, then the canteen).
// Each agent sits behind a desk; monitor glows when working.
// The canteen (탕비실) holds MCPs (appliances) and Skills (recipe books).

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import Character from './Character';
import SharedSprite, { POSE } from './Sprite';
import { t } from './i18n';

// Pose & status mapping kept in lockstep with GeneralViewer so the two
// modes always show the same visual language for working / waiting / etc.
function poseForDesk(agent) {
  if (agent?.state === 'working') return agent.model === 'opus' ? POSE.WORK_OPUS : POSE.WORK_SONNET;
  if (agent?.state === 'waiting') return POSE.WAIT;
  return POSE.IDLE;
}
const DESK_STATUS_KO = {
  working: '작업중',
  waiting: '대기중 zZ',
  idle:    '쉬는중',
};
const DESK_STATUS_EN = {
  working: 'working',
  waiting: 'waiting zZ',
  idle:    'idle',
};

const MIN_ZOOM = 0.4;
const MAX_ZOOM = 2.0;
const ZOOM_STEP = 0.1;
const DRAG_THRESHOLD = 4;

// Post-2026-04-19 slim: only HQ + dev + eval + canteen rooms render.
// mgmt / leads / domain rooms were empty shells and got deleted along
// with their agents (mgmt-lead / reporter / hr / eval-lead /
// process-tagger / causal-analyst / dvc-curator / adapter-engineer).
const ROOM_STYLES = {
  eval:    { wall: '#4a2f2f', floor: '#7a5858', accent: '#ff9b9b' },
  dev:     { wall: '#2a3f52', floor: '#4a5e74', accent: '#7cc7e8' },
  top:     { wall: '#2c2c34', floor: '#5a5868', accent: '#ffd54f' },
  canteen: { wall: '#2f4234', floor: '#6a8464', accent: '#8be28b' },
};

// Build a multi-band wall/floor gradient so every row of characters sits
// against its own wall-above-floor band — matching what the sprite art
// expects. Without this, row-2 characters end up on pure floor color
// while their sprite still renders a wall/window above them, leaving a
// visible "ceiling" mismatch (the product owner flagged this as the
// white-rectangle issue). The math here mirrors the assign() layout —
// each row occupies 240px starting at roomTop+40.
function buildRoomBg(rowCount, rowHeight, headerPad, bottomPad, wall, floor) {
  if (rowCount <= 1) {
    // Original 2-band look for single-row rooms / canteen.
    return `linear-gradient(to bottom, ${wall} 0%, ${wall} 45%, ${floor} 45%, ${floor} 100%)`;
  }
  const total = headerPad + rowCount * rowHeight + bottomPad;
  const stops = [`${wall} 0px`, `${wall} ${headerPad}px`];
  for (let i = 0; i < rowCount; i++) {
    const rowStart = headerPad + i * rowHeight;
    const rowMid   = rowStart + Math.round(rowHeight * 0.5);
    const rowEnd   = rowStart + rowHeight;
    if (i > 0) stops.push(`${wall} ${rowStart}px`);
    stops.push(`${wall} ${rowMid}px`);
    stops.push(`${floor} ${rowMid}px`);
    stops.push(`${floor} ${rowEnd}px`);
  }
  stops.push(`${floor} ${total}px`);
  return `linear-gradient(to bottom, ${stops.join(', ')})`;
}

function statusFor(state, lang) {
  const tbl = lang === 'ko' ? DESK_STATUS_KO : DESK_STATUS_EN;
  return tbl[state] || tbl.idle;
}

function Desk({ agent, x, y, onClick, onDoubleClick, isSelected, lang, tint }) {
  const state = agent.state || 'idle';
  const working = state === 'working';
  const displayName = t(`agent.${agent.name}`, lang) || agent.name;
  const statusText = statusFor(state, lang);

  return (
    <div
      className={`desk-cell state-${state}${isSelected ? ' selected' : ''}`}
      style={{ left: x, top: y }}
      // Stop pointerdown/up from reaching the parent's marquee-zoom
      // handlers. Without this the parent captures the pointer and the
      // synthesized click never lands on the desk — so clicking a
      // character did nothing in custom mode (general mode works because
      // it has no marquee handler).
      onPointerDown={(e) => e.stopPropagation()}
      onPointerUp={(e) => e.stopPropagation()}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      title={`${displayName} · ${agent.model} · ${statusText}`}
    >
      <div className="desk-nameplate">
        <span className="desk-name">{displayName}</span>
        <span className={`desk-model model-${agent.model}`}>{agent.model}</span>
      </div>

      {state !== 'idle' && (
        <div className={`desk-bubble state-${state}`}>{statusText}</div>
      )}

      <div className={`desk-char${working ? ' working' : ''}`}>
        <SharedSprite agent={agent} pose={poseForDesk(agent)} size={140} />
      </div>

      {working && <div className="desk-glow" />}
    </div>
  );
}

// Pixel-art MCP appliance (coffee machine / server / printer), skill
// recipe book, or knowledge reference doc. Click → opens a small detail
// card via onSelectItem.
function CanteenItem({ item, x, y, onClick }) {
  const isMcp = item.kind === 'mcp';
  const isKnowledge = item.kind === 'knowledge';
  const klass = isMcp ? 'is-mcp' : isKnowledge ? 'is-knowledge' : 'is-skill';
  const titlePrefix = isMcp ? 'MCP' : isKnowledge ? 'Knowledge' : 'Skill';
  return (
    <div
      className={`canteen-item ${klass}`}
      style={{ left: x, top: y }}
      onPointerDown={(e) => e.stopPropagation()}
      onPointerUp={(e) => e.stopPropagation()}
      onClick={onClick}
      title={`${titlePrefix}: ${item.label}`}
    >
      <svg viewBox="0 0 32 32" width="56" height="56" style={{ imageRendering: 'pixelated' }}>
        {isMcp ? (
          <>
            {/* Appliance silhouette — coffee machine style */}
            <rect x="6" y="6" width="20" height="22" fill="#3a3a3a" />
            <rect x="8" y="8" width="16" height="8" fill="#7cc7e8" />
            <rect x="10" y="18" width="12" height="6" fill="#111" />
            <rect x="14" y="24" width="4" height="2" fill="#6b3d2a" />
            <rect x="12" y="26" width="8" height="2" fill="#222" />
            <rect x="8" y="10" width="4" height="2" fill="#fff" opacity="0.5" />
          </>
        ) : isKnowledge ? (
          <>
            {/* Knowledge: thick reference book with a bookmark ribbon —
                distinct from the skill/recipe book so the user sees
                "도메인 지식 참조 자료" at a glance. */}
            <rect x="4" y="4" width="24" height="24" fill="#2f4a6b" />
            <rect x="6" y="6" width="20" height="20" fill="#e8d7a0" />
            <rect x="8" y="9" width="16" height="1" fill="#5a3a1a" />
            <rect x="8" y="12" width="14" height="1" fill="#5a3a1a" />
            <rect x="8" y="15" width="16" height="1" fill="#5a3a1a" />
            <rect x="8" y="18" width="12" height="1" fill="#5a3a1a" />
            <rect x="8" y="21" width="14" height="1" fill="#5a3a1a" />
            {/* bookmark ribbon */}
            <rect x="22" y="2" width="3" height="12" fill="#ff9b9b" />
            <rect x="22" y="14" width="3" height="2" fill="#c46c6c" />
          </>
        ) : (
          <>
            {/* Recipe book / scroll */}
            <rect x="5" y="7" width="22" height="20" fill="#7a4a2a" />
            <rect x="7" y="9" width="18" height="16" fill="#fff8dc" />
            <rect x="9" y="11" width="14" height="1" fill="#6b3d2a" />
            <rect x="9" y="14" width="12" height="1" fill="#6b3d2a" />
            <rect x="9" y="17" width="14" height="1" fill="#6b3d2a" />
            <rect x="9" y="20" width="10" height="1" fill="#6b3d2a" />
            <rect x="15" y="23" width="2" height="2" fill="#ff9b9b" />
          </>
        )}
      </svg>
      <div className="canteen-item-label">{item.label}</div>
    </div>
  );
}

export default function OfficeScene({
  topology, onSelect, selected, lang,
  mcps = [], skills = [], onSelectMcp, onSelectSkill,
  backlog = [], reports = [], activity = [],
  onSelectKnowledge,
}) {
  // Knowledge reference docs (slug → title). After the 2026-04-19 slim,
  // domain agents (process-tagger etc.) are replaced by these markdown
  // docs that dev-lead/orchestrator read directly. Rendered as a small
  // bookshelf in the canteen so the viewer has a visual anchor for
  // "도메인 지식은 에이전트가 아닌 참조 자료" principle.
  const knowledgeDocs = (topology && topology.knowledge) || [];

  const rootRef = useRef(null);
  const [zoom, setZoom] = useState(0.75);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef({ active: false, start: null, moved: 0 });

  const agents = (topology && topology.agents) || [];

  // dev-lead sits at the top of the dev room. No other leads — eval
  // reviewers don't have a lead (orchestrator calls them directly).
  const LEAD_TEAM_OF = {
    'dev-lead': 'dev',
  };
  // Agents whose backend team isn't in the active room set get dropped
  // on the floor — we no longer render mgmt / leads / domain rooms, so
  // any stray legacy agent there is visually omitted rather than
  // summoning an empty room back. Keeps the scene clean when
  // `_state/state.json` still holds retired names.
  const ACTIVE_TEAMS = new Set(['top', 'dev', 'eval']);
  const byTeam = {};
  for (const a of agents) {
    const k = LEAD_TEAM_OF[a.name] || a.team;
    if (!ACTIVE_TEAMS.has(k)) continue;
    if (!byTeam[k]) byTeam[k] = [];
    byTeam[k].push(a);
  }
  // Sort each team so its lead is the first cell in the room. Secondary
  // sort by name keeps placement stable when an agent is added or
  // retired mid-session — otherwise existing agents visibly shuffle.
  for (const k of Object.keys(byTeam)) {
    byTeam[k].sort((a, b) => {
      const al = LEAD_TEAM_OF[a.name] ? 0 : 1;
      const bl = LEAD_TEAM_OF[b.name] ? 0 : 1;
      if (al !== bl) return al - bl;
      return a.name.localeCompare(b.name);
    });
  }

  // All team rooms share the SAME width and column count so the three
  // boxes line up evenly under HQ. Agents flow top-to-bottom within
  // each room — the lead is always row 0 col 0, then the rest fill in
  // reading order.
  const TEAM_COLS = 3;
  const roomFor = (members) => {
    const count = Math.max(1, members.length);
    const cols = TEAM_COLS;
    const rows = Math.ceil(count / cols);
    return { cols, rows, w: 80 + cols * 200, h: 60 + rows * 240 };
  };

  const evalRoom = roomFor(byTeam.eval || []);
  const devRoom  = roomFor(byTeam.dev  || []);

  // Canteen sized so MCP / Skill / Knowledge columns each get equal
  // width and a clean grid. MCPs (appliances) + Skills (recipe books) +
  // Knowledge (domain reference docs) — three vertical strips divided
  // by a 60px gap each.
  const ITEM_TILE = 110;
  const ITEM_GAP = 14;
  const mcpCols = Math.min(3, Math.max(1, mcps.length));
  const mcpRows = Math.ceil(mcps.length / mcpCols) || 1;
  const skillCols = Math.min(2, Math.max(1, skills.length));
  const skillRows = Math.ceil(skills.length / skillCols) || 1;
  const knowledgeCols = knowledgeDocs.length > 0 ? Math.min(2, knowledgeDocs.length) : 0;
  const knowledgeRows = knowledgeCols ? Math.ceil(knowledgeDocs.length / knowledgeCols) : 0;
  const canteenSectionH = 80 + Math.max(mcpRows, skillRows, knowledgeRows || 0) * (ITEM_TILE + ITEM_GAP);
  const canteenRoom = {
    w: 80 + mcpCols * (ITEM_TILE + ITEM_GAP)
         + 60 /* divider */ + skillCols * (ITEM_TILE + ITEM_GAP)
         + (knowledgeCols
              ? 60 /* divider */ + knowledgeCols * (ITEM_TILE + ITEM_GAP)
              : 0),
    h: canteenSectionH,
  };

  const W = Math.max(1700, 360 + Math.max(
    devRoom.w + evalRoom.w + 80,
    canteenRoom.w + 80,
  ));
  const GUTTER = 40;

  const HQ    = { x: W / 2 - 220, y: 40,  w: 440, h: 240, team: 'top' };

  const floor2Y = HQ.y + HQ.h + 80;
  // Only dev + eval rooms render on floor 2. Empty ones (no agents yet)
  // still get skipped so we never draw a blank placeholder wall.
  const floor2Rooms = [];
  if ((byTeam.dev  || []).length > 0) floor2Rooms.push({ key: 'dev',  room: devRoom,  team: 'dev'  });
  if ((byTeam.eval || []).length > 0) floor2Rooms.push({ key: 'eval', room: evalRoom, team: 'eval' });
  const totalF2W = floor2Rooms.length
    ? floor2Rooms.reduce((a, r) => a + r.room.w, 0) + GUTTER * (floor2Rooms.length - 1)
    : 0;
  let fx = (W - totalF2W) / 2;
  const floor2 = [];
  let f2MaxH = 0;
  for (const r of floor2Rooms) {
    floor2.push({ x: fx, y: floor2Y, w: r.room.w, h: r.room.h, team: r.team, key: r.key });
    fx += r.room.w + GUTTER;
    f2MaxH = Math.max(f2MaxH, r.room.h);
  }

  const floor3Y = floor2Y + f2MaxH + 60;
  // Canteen — centered below floor 2. Domain room is gone (domain
  // knowledge lives as bookshelf items inside the canteen now).
  const CANTEEN = {
    x: W / 2 - canteenRoom.w / 2,
    y: floor3Y,
    w: canteenRoom.w,
    h: canteenRoom.h,
    team: 'canteen',
  };

  const H = CANTEEN.y + CANTEEN.h + 120;

  const agentPos = {};
  const assign = (room, list, cols) => {
    list.forEach((a, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      agentPos[a.name] = { x: room.x + 40 + col * 200, y: room.y + 40 + row * 240 };
    });
  };
  if (byTeam.top && byTeam.top[0]) {
    agentPos[byTeam.top[0].name] = { x: HQ.x + HQ.w / 2 - 90, y: HQ.y + 30 };
  }
  for (const room of floor2) {
    const team = room.team;
    const r = team === 'eval' ? evalRoom : devRoom;
    assign(room, byTeam[team] || [], r.cols);
  }

  useEffect(() => {
    if (!rootRef.current) return;
    const r = rootRef.current.getBoundingClientRect();
    const fit = Math.min(r.width / W, r.height / H) * 0.98;
    const z = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, fit));
    setZoom(z);
    setPan({ x: (r.width - W * z) / 2, y: (r.height - H * z) / 2 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [W, H]);

  // Wheel zoom intentionally disabled — it ate the page scroll, so the
  // user couldn't reach the tabs / activity log under the canvas. Use
  // the marquee drag below to zoom in/out, or the +/- buttons.

  // Marquee zoom: left-click drag draws a rectangle. On release:
  //   • drag goes top-left → bottom-right ⇒ zoom INTO that rectangle
  //   • drag goes bottom-right → top-left (reverse) ⇒ zoom OUT
  //   • a tiny click (<4 px) is treated as a click, not a drag
  // Pan: middle-mouse drag (or shift+drag) when you need to slide the
  // already-zoomed canvas around.
  const [marquee, setMarquee] = useState(null);
  const onPointerDown = (e) => {
    const r = rootRef.current.getBoundingClientRect();
    const mx = e.clientX - r.left;
    const my = e.clientY - r.top;
    if (e.button === 1 || e.shiftKey) {
      // Pan mode
      dragRef.current = { active: true, mode: 'pan', start: { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y }, moved: 0 };
    } else if (e.button === 0) {
      // Marquee zoom mode
      dragRef.current = { active: true, mode: 'marquee', start: { x: mx, y: my }, moved: 0 };
      setMarquee({ x1: mx, y1: my, x2: mx, y2: my });
    } else {
      return;
    }
    rootRef.current.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e) => {
    const d = dragRef.current;
    if (!d.active) return;
    if (d.mode === 'pan') {
      const dx = e.clientX - d.start.x;
      const dy = e.clientY - d.start.y;
      d.moved = Math.max(d.moved, Math.hypot(dx, dy));
      setPan({ x: d.start.px + dx, y: d.start.py + dy });
    } else if (d.mode === 'marquee') {
      const r = rootRef.current.getBoundingClientRect();
      const mx = e.clientX - r.left;
      const my = e.clientY - r.top;
      d.moved = Math.max(d.moved, Math.hypot(mx - d.start.x, my - d.start.y));
      setMarquee({ x1: d.start.x, y1: d.start.y, x2: mx, y2: my });
    }
  };
  const onPointerUp = (e) => {
    const d = dragRef.current;
    if (d.active && d.mode === 'marquee' && d.moved > DRAG_THRESHOLD) {
      const m = marquee;
      if (m) {
        const dx = m.x2 - m.x1;
        const dy = m.y2 - m.y1;
        const reverse = dx < 0 || dy < 0;
        if (reverse) {
          // Reverse drag → zoom out toward fit
          const r = rootRef.current.getBoundingClientRect();
          const fit = Math.min(r.width / W, r.height / H) * 0.98;
          const next = Math.max(MIN_ZOOM, Math.min(zoom, fit));
          setZoom(next);
          setPan({ x: (r.width - W * next) / 2, y: (r.height - H * next) / 2 });
        } else {
          // Forward drag → fit the marquee box to the viewport
          const left = Math.min(m.x1, m.x2);
          const top = Math.min(m.y1, m.y2);
          const w = Math.abs(dx);
          const h = Math.abs(dy);
          if (w > 8 && h > 8) {
            const r = rootRef.current.getBoundingClientRect();
            // Convert screen marquee → world coordinates first.
            const wx = (left - pan.x) / zoom;
            const wy = (top - pan.y) / zoom;
            const ww = w / zoom;
            const wh = h / zoom;
            const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM,
              Math.min(r.width / ww, r.height / wh) * 0.95));
            setZoom(newZoom);
            setPan({
              x: (r.width - ww * newZoom) / 2 - wx * newZoom,
              y: (r.height - wh * newZoom) / 2 - wy * newZoom,
            });
          }
        }
      }
    }
    dragRef.current.active = false;
    setMarquee(null);
    try { rootRef.current.releasePointerCapture(e.pointerId); } catch {/* ignore */}
  };

  const resetView = useCallback(() => {
    if (!rootRef.current) return;
    const r = rootRef.current.getBoundingClientRect();
    const fit = Math.min(r.width / W, r.height / H) * 0.98;
    setZoom(fit);
    setPan({ x: (r.width - W * fit) / 2, y: (r.height - H * fit) / 2 });
  }, [W, H]);

  const onDoubleClick = (e) => {
    if (e.target.closest('.desk-cell') || e.target.closest('.canteen-item')) return;
    resetView();
  };

  // Single-click on a character opens the side panel; double-click on
  // EMPTY canvas resets the zoom (handled in onDoubleClick above, which
  // already excludes desk-cell / canteen-item).
  const handleNodeClick = (agent) => (e) => {
    if (dragRef.current.moved > DRAG_THRESHOLD) return;
    e.stopPropagation();
    onSelect && onSelect(agent);
  };
  const handleNodeDoubleClick = (agent) => (e) => {
    e.stopPropagation();
    onSelect && onSelect(agent);
  };

  const orchestrator = (byTeam.top || [])[0];
  // Connector orchestrator → each lead (now first cell of its team room).
  const leads = agents.filter((a) => LEAD_TEAM_OF[a.name]);
  const paths = orchestrator ? leads.map((ld) => {
    const p = agentPos[orchestrator.name];
    const c = agentPos[ld.name];
    if (!p || !c) return null;
    const x1 = p.x + 90, y1 = p.y + 150;
    const x2 = c.x + 90, y2 = c.y - 10;
    const midY = (y1 + y2) / 2;
    return { key: `${orchestrator.name}-${ld.name}`, d: `M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}` };
  }).filter(Boolean) : [];

  const allRooms = [
    { ...HQ, key: 'hq', labelKey: 'team.top', count: (byTeam.top || []).length },
    ...floor2.map((r) => ({ ...r, labelKey: `team.${r.team}`, count: (byTeam[r.team] || []).length })),
    { ...CANTEEN, key: 'canteen', labelKey: 'team.canteen', count: mcps.length + skills.length + (knowledgeDocs?.length || 0) },
  ];

  // Canteen item layout — clean two-column-group grid with MCPs on the
  // left half (each item in its own slot, no overlaps) and Skills on
  // the right half. The grid math here mirrors how canteenRoom was
  // sized so item rectangles never collide.
  const canteenContent = [];
  const mcpAreaX = CANTEEN.x + 30;
  const mcpAreaY = CANTEEN.y + 60;
  mcps.forEach((m, i) => {
    const col = i % mcpCols;
    const row = Math.floor(i / mcpCols);
    canteenContent.push({
      kind: 'mcp', ...m,
      label: (lang === 'ko' ? m.name_ko : m.name_en) || m.id,
      x: mcpAreaX + col * (ITEM_TILE + ITEM_GAP),
      y: mcpAreaY + row * (ITEM_TILE + ITEM_GAP),
    });
  });
  const skillAreaX = mcpAreaX + mcpCols * (ITEM_TILE + ITEM_GAP) + 60;
  skills.forEach((s, i) => {
    const col = i % skillCols;
    const row = Math.floor(i / skillCols);
    canteenContent.push({
      kind: 'skill', ...s,
      label: s.label || s.name || s.id,
      x: skillAreaX + col * (ITEM_TILE + ITEM_GAP),
      y: mcpAreaY + row * (ITEM_TILE + ITEM_GAP),
    });
  });
  // Knowledge bookshelf — rendered as pixel "books" (reuse skill sprite)
  // positioned to the right of the skill column with its own divider.
  if (knowledgeCols > 0) {
    const knowledgeAreaX = skillAreaX + skillCols * (ITEM_TILE + ITEM_GAP) + 60;
    knowledgeDocs.forEach((k, i) => {
      const col = i % knowledgeCols;
      const row = Math.floor(i / knowledgeCols);
      canteenContent.push({
        kind: 'knowledge',
        id: k.slug,
        slug: k.slug,
        label: lang === 'en' ? (k.title_en || k.slug) : (k.title_ko || k.slug),
        x: knowledgeAreaX + col * (ITEM_TILE + ITEM_GAP),
        y: mcpAreaY + row * (ITEM_TILE + ITEM_GAP),
      });
    });
  }

  return (
    <div
      ref={rootRef}
      className="office-scene"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onDoubleClick={onDoubleClick}
    >
      <div className="scene-help">{t('zoom.help', lang)}</div>
      <SceneTodo
        lang={lang}
        working={agents.filter((a) => a.state === 'working')}
        backlog={backlog}
        reports={reports}
        activity={activity}
      />
      {marquee && (
        <div
          className="scene-marquee"
          style={{
            left: Math.min(marquee.x1, marquee.x2),
            top: Math.min(marquee.y1, marquee.y2),
            width: Math.abs(marquee.x2 - marquee.x1),
            height: Math.abs(marquee.y2 - marquee.y1),
            borderColor: (marquee.x2 < marquee.x1 || marquee.y2 < marquee.y1) ? '#ff6b6b' : '#ffd54f',
          }}
        />
      )}

      <div
        className="office-world"
        style={{
          width: W, height: H,
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
        }}
      >
        {allRooms.map((r) => {
          const style = ROOM_STYLES[r.team] || ROOM_STYLES.dev;
          const working = r.team === 'canteen' ? 0 : (byTeam[r.team] || []).filter((a) => a.state === 'working').length;
          const isCanteen = r.team === 'canteen';
          const roomRows = (r.team === 'top' || r.team === 'canteen')
            ? 1
            : Math.max(1, (byTeam[r.team] || []).length === 0
                ? 1
                : Math.ceil((byTeam[r.team] || []).length / TEAM_COLS));
          const roomBg = (r.team === 'top' || isCanteen)
            ? `linear-gradient(to bottom, ${style.wall} 0%, ${style.wall} 45%, ${style.floor} 45%, ${style.floor} 100%)`
            : buildRoomBg(roomRows, 240, 40, 20, style.wall, style.floor);
          return (
            <div
              key={r.key}
              className={`office-room room-${r.team}`}
              style={{
                left: r.x, top: r.y, width: r.w, height: r.h,
                background: roomBg,
                borderColor: style.accent,
              }}
            >
              <div className="wall-window" style={{ left: 30 }} />
              {r.w > 300 && <div className="wall-window" style={{ left: r.w - 90 }} />}
              <div className="wall-plaque" style={{ borderColor: style.accent }}>
                <div className="plaque-label" style={{ color: style.accent }}>
                  {t(r.labelKey, lang)} · {r.count}
                </div>
                {working > 0 && <div className="plaque-working">⚡ {working}</div>}
              </div>
              {isCanteen && (
                <div className="canteen-caption">
                  <span className="canteen-tag" style={{ background: style.accent }}>🍵</span>
                  <span className="canteen-help">
                    <b>{t('canteen.mcp_label', lang)}</b> · {t('canteen.skill_label', lang)}
                  </span>
                </div>
              )}
              {r.w > 360 && !isCanteen && <div className="floor-plant" style={{ right: 18, bottom: 18 }}>
                <svg viewBox="0 0 16 16" width="28" height="28"><rect x="6" y="10" width="4" height="5" fill="#4a2b15"/><rect x="4" y="4" width="8" height="7" fill="#2f7a3a"/><rect x="5" y="3" width="6" height="2" fill="#3a8a42"/></svg>
              </div>}
            </div>
          );
        })}

        <svg className="office-connector" width={W} height={H} style={{ position: 'absolute', left: 0, top: 0, pointerEvents: 'none' }}>
          {paths.map((p) => (
            <path key={p.key} d={p.d} fill="none" stroke="#ffd54f" strokeOpacity={0.6} strokeWidth={3} strokeLinecap="round" strokeDasharray="6 4" />
          ))}
        </svg>

        {agents.map((a) => {
          const pos = agentPos[a.name];
          if (!pos) return null;
          const tint = ROOM_STYLES[a.team]?.accent;
          return (
            <Desk
              key={a.name}
              agent={a}
              x={pos.x} y={pos.y}
              onClick={handleNodeClick(a)}
              onDoubleClick={handleNodeDoubleClick(a)}
              isSelected={selected && selected.name === a.name}
              lang={lang}
              tint={tint}
            />
          );
        })}

        {canteenContent.map((item, i) => (
          <CanteenItem
            key={`${item.kind}-${item.id || item.label}-${i}`}
            item={item}
            x={item.x}
            y={item.y}
            onClick={(e) => {
              e.stopPropagation();
              if (item.kind === 'mcp' && onSelectMcp) onSelectMcp(item);
              else if (item.kind === 'skill' && onSelectSkill) onSelectSkill(item);
              else if (item.kind === 'knowledge' && onSelectKnowledge) onSelectKnowledge(item);
            }}
          />
        ))}
      </div>
    </div>
  );
}

// Left-dock overlay: click any row to expand the task list. Each task
// gets a mgmt-lead-style plain-language description so the product
// owner can scan without opening the full tab.
function SceneTodo({ lang, working, backlog, reports, activity }) {
  const [openSection, setOpenSection] = useState(null); // 'working' | 'next' | 'done' | null

  // Working: pair each working agent with the most recent activity entry
  // we can find for them — that's the closest thing to "what they're
  // doing right now" without a dedicated task field.
  const workingItems = useMemo(() => {
    const recent = new Map();
    for (const ev of (activity || [])) {
      if (!ev?.agent || !ev?.detail) continue;
      if (!recent.has(ev.agent)) recent.set(ev.agent, ev);
    }
    return (working || []).map((a) => ({
      title: t(`agent.${a.name}`, lang) || a.name,
      sub: a.name,
      desc: plainDescForAgent(a, recent.get(a.name), lang),
    }));
  }, [working, activity, lang]);

  const nextItems = useMemo(() => {
    // 예정 = 아직 시작 안 한 백로그 (next / planning). cancelled / done /
    // working 은 각자 다른 섹션(또는 숨김) 담당.
    return (backlog || [])
      .filter((b) => {
        const s = (b.status || '').toLowerCase();
        return s === 'next' || s === 'planning';
      })
      .map((b) => ({
        title: b.title || b.name || '?',
        sub: b.team ? `@${b.team}` : '',
        desc: plainDescForBacklog(b, lang),
      }));
  }, [backlog, lang]);

  const doneItems = useMemo(() => {
    // 완료 = 백로그 중 status=done (+ 기존 reports 는 아래에 병합). 이전에는
    // reports 만 봐서 실제로 끝낸 요구사항이 카운트되지 않았다.
    const doneBacklog = (backlog || [])
      .filter((b) => (b.status || '').toLowerCase() === 'done')
      .map((b) => ({
        title: b.title || b.name || '?',
        sub: b.team ? `@${b.team}` : '',
        desc: plainDescForBacklog(b, lang),
      }));
    const doneReports = (reports || []).map((r) => ({
      title: r.title || r.name || (lang === 'ko' ? '보고서' : 'report'),
      sub: r.created ? new Date(r.created).toLocaleDateString(lang === 'ko' ? 'ko-KR' : 'en-US') : '',
      desc: plainDescForReport(r, lang),
    }));
    return [...doneBacklog, ...doneReports];
  }, [backlog, reports, lang]);

  // Per-section empty-state copy — the product owner specifically asked
  // for these three phrasings instead of one generic "nothing here".
  const emptyCopy = (key) => {
    if (lang === 'ko') {
      if (key === 'working') return '진행중인 작업이 없어요.';
      if (key === 'next')    return '예정된 작업이 없어요.';
      return '완료된 작업이 없어요.';
    }
    if (key === 'working') return 'No work in progress.';
    if (key === 'next')    return 'No upcoming work.';
    return 'No completed work yet.';
  };

  const sections = [
    { key: 'working', icon: '⚡', label: lang === 'ko' ? '작업중' : 'Working', items: workingItems },
    { key: 'next',    icon: '📋', label: lang === 'ko' ? '예정'   : 'Next',    items: nextItems },
    { key: 'done',    icon: '✅', label: lang === 'ko' ? '완료'   : 'Done',    items: doneItems },
  ];

  // Parent OfficeScene captures pointerdown for its marquee-zoom — if we
  // let the event bubble, the parent grabs pointer capture and the
  // synthesized click never lands on the row (same bug Desk hit earlier,
  // see onPointerDown comment in Desk above).
  const stopPtr = (e) => e.stopPropagation();

  const toggle = (key) => setOpenSection((cur) => (cur === key ? null : key));

  return (
    <div
      className="scene-todo"
      onPointerDown={stopPtr}
      onPointerUp={stopPtr}
    >
      {sections.map((s) => {
        const isOpen = openSection === s.key;
        return (
          <div key={s.key}>
            <div
              className={`scene-todo-row${isOpen ? ' active' : ''}`}
              role="button"
              tabIndex={0}
              aria-expanded={isOpen}
              aria-controls={`scene-todo-detail-${s.key}`}
              onClick={() => toggle(s.key)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  toggle(s.key);
                }
              }}
            >
              <span className="scene-todo-label">{s.icon} {s.label}</span>
              <span className={`scene-todo-count${s.items.length === 0 ? ' zero' : ''}`}>
                {s.items.length}
              </span>
              <span className="scene-todo-caret">›</span>
            </div>
            {isOpen && (
              <div className="scene-todo-detail" id={`scene-todo-detail-${s.key}`}>
                {s.items.length === 0 ? (
                  <div className="scene-todo-item-empty">{emptyCopy(s.key)}</div>
                ) : (
                  s.items.map((item, i) => (
                    <div className="scene-todo-item" key={i}>
                      <span className="scene-todo-item-title">{item.title}</span>
                      {item.sub && <span className="scene-todo-item-meta">{item.sub}</span>}
                      <div className="scene-todo-item-desc">{item.desc}</div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Plain-language summaries — the mgmt-lead voice: short, non-technical,
// tells the user WHAT the agent is doing, not the raw tool call.
function plainDescForAgent(agent, recentEvent, lang) {
  const role = agent.description || '';
  const tail = recentEvent?.detail || '';
  if (lang === 'ko') {
    if (tail) return `지금은 「${tail.slice(0, 90)}」 를 진행 중입니다.` + (role ? ` 이 에이전트는 ${role.slice(0, 80)}.` : '');
    if (role) return `이 에이전트는 ${role.slice(0, 140)}. 작업이 곧 시작됩니다.`;
    return '작업이 할당됐고 곧 첫 출력이 나옵니다.';
  }
  if (tail) return `Currently: "${tail.slice(0, 90)}".` + (role ? ` This agent ${role.slice(0, 80)}.` : '');
  if (role) return `This agent ${role.slice(0, 140)}. Work is about to start.`;
  return 'Task assigned — first output is on its way.';
}

function plainDescForBacklog(item, lang) {
  const desc = item.description || item.summary || '';
  const team = item.team ? ` (${item.team} 팀 담당)` : '';
  const prio = item.priority ? ` · 우선순위 ${item.priority}` : '';
  if (lang === 'ko') {
    if (desc) return desc.slice(0, 200) + team + prio;
    return `팀 리드가 승인한 예정 작업입니다${team}${prio}. 곧 담당자가 배정됩니다.`;
  }
  const enTeam = item.team ? ` (owned by ${item.team})` : '';
  const enPrio = item.priority ? ` · priority ${item.priority}` : '';
  if (desc) return desc.slice(0, 200) + enTeam + enPrio;
  return `Approved by a team lead${enTeam}${enPrio}. An owner will pick it up shortly.`;
}

function plainDescForReport(report, lang) {
  const body = report.body || report.summary || report.description || '';
  if (lang === 'ko') {
    if (body) return body.slice(0, 220);
    return '보고원이 정리한 완료 요약입니다. 탭에서 전체 본문을 볼 수 있어요.';
  }
  if (body) return body.slice(0, 220);
  return 'Summary written by the reporter. Open the Reports tab for the full text.';
}

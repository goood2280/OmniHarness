// GeneralViewer.jsx — General mode scene.
//
// Game-like composition: a modern arena floor with the main Claude
// standing in the middle, a canteen shelf on the left wall (MCP
// appliances), a skill shelf on the right wall (recipe books), and
// plants/decor scattered around. Traced subagents appear as characters
// around the perimeter, each at a small desk. Everything is composed
// from individual PNG tiles when available, with SVG / emoji fallbacks
// when they aren't, so the layout is always intact.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Sprite, { POSE } from './Sprite';
import ItemTile from './ItemTile';
import { t } from './i18n';

const POSE_NAMES_KO = [
  '대기 (idle)', 'Sonnet 평상 작업', 'Opus 열일모드', '손 든 질문',
  '대기중 zzz', '생각 중', '축하 🎉', '에러 (facepalm)',
  '보고 작성', '리서치', '커피 브레이크', '설명/지시',
  '인사 👋', '걷기', '통화', '번아웃 😴',
];

function poseName(p) {
  return POSE_NAMES_KO[p] ?? '';
}

const DEMO_POSE_ORDER = [
  POSE.IDLE, POSE.WORK_SONNET, POSE.WORK_OPUS, POSE.QUESTION,
  POSE.WAIT, POSE.THINKING, POSE.CELEBRATE, POSE.ERROR,
  POSE.REPORTING, POSE.READING, POSE.COFFEE, POSE.POINTING,
  POSE.WAVING, POSE.WALKING, POSE.PHONE, POSE.SLEEPING,
];

// Map canteen MCP ids → item tile filenames.
const MCP_TILE = {
  filesystem: 'fridge',
  browser:    'water-cooler',
  shell:      'coffee-machine',
  github:     'printer',
  memory:     'server-rack',
};
// Map skill ids → book tile filenames.
const SKILL_TILE = {
  review:          'book-review',
  'security-review': 'book-security',
  simplify:        'book-simplify',
  init:            'book-init',
};

// Hierarchical layout — Claude on top, traced subagents stack in a row
// directly below him. Mirrors the OrgChart custom-mode shape: HQ →
// leads. Only the orchestrator + 3 lead character sheets exist as PNGs
// today; every other agent reuses one of the lead sheets so the panel
// still shows a full-body character at desk instead of the procedural
// SVG fallback. Labels still respect i18n when the agent name is known
// — only unknown agents get the generic "subagent (Sonnet/Opus)" label.
const HAS_SHEET = new Set([
  'orchestrator',
  'dev-lead', 'eval-lead', 'mgmt-lead',
  'hr', 'reporter',
  'ux-reviewer', 'dev-verifier', 'security-auditor',
  'user-role-tester', 'admin-role-tester', 'domain-researcher',
  'dev-dashboard', 'dev-spc', 'dev-wafer-map', 'dev-ml',
  'dev-ettime', 'dev-tablemap', 'dev-tracker', 'dev-filebrowser',
  'dev-admin', 'dev-messages',
  'process-tagger', 'causal-analyst', 'dvc-curator', 'adapter-engineer',
]);
const FALLBACK_SPRITES = ['dev-lead', 'eval-lead', 'mgmt-lead'];

function isKnownAgent(name, lang) {
  // i18n.t() returns the key unchanged when the entry is missing.
  return t(`agent.${name}`, lang) !== `agent.${name}`;
}

function modelTag(model) {
  const m = (model || 'sonnet').toLowerCase();
  return m.charAt(0).toUpperCase() + m.slice(1);
}

// Pose → human-readable status. Used for the speech bubble above each
// character so the user sees WHAT the agent is doing, not just an
// abstract lightning bolt.
const POSE_STATUS_KO = {
  [POSE.IDLE]:        { text: '대기',         icon: '☕',   cls: 'state-idle' },
  [POSE.WORK_SONNET]: { text: '작업중',       icon: '⚡',   cls: 'state-working' },
  [POSE.WORK_OPUS]:   { text: '열일중',       icon: '⚡⚡', cls: 'state-working' },
  [POSE.QUESTION]:    { text: '질문있음',     icon: '?',    cls: 'state-question' },
  [POSE.WAIT]:        { text: '대기중 zZ',    icon: '💤',   cls: 'state-waiting' },
  [POSE.THINKING]:    { text: '생각중',       icon: '💭',   cls: 'state-thinking' },
  [POSE.CELEBRATE]:   { text: '신난중 🎉',    icon: '🎉',   cls: 'state-celebrate' },
  [POSE.ERROR]:       { text: '에러 😵',     icon: '⚠',   cls: 'state-error' },
  [POSE.REPORTING]:   { text: '보고 작성중',   icon: '📋',   cls: 'state-reporting' },
  [POSE.READING]:     { text: '리서치중',     icon: '📚',   cls: 'state-reading' },
  [POSE.COFFEE]:      { text: '커피타임중',    icon: '☕',   cls: 'state-coffee' },
  [POSE.POINTING]:    { text: '설명중',       icon: '👉',   cls: 'state-pointing' },
  [POSE.WAVING]:      { text: '인사중',       icon: '👋',   cls: 'state-waving' },
  [POSE.WALKING]:     { text: '산책중',       icon: '🚶',   cls: 'state-walking' },
  [POSE.PHONE]:       { text: '통화중',       icon: '📞',   cls: 'state-phone' },
  [POSE.SLEEPING]:    { text: '쉬는중 💤',    icon: '💤',   cls: 'state-sleeping' },
};
const POSE_STATUS_EN = {
  [POSE.IDLE]:        { text: 'idle',          icon: '☕',   cls: 'state-idle' },
  [POSE.WORK_SONNET]: { text: 'working',       icon: '⚡',   cls: 'state-working' },
  [POSE.WORK_OPUS]:   { text: 'hustle',        icon: '⚡⚡', cls: 'state-working' },
  [POSE.QUESTION]:    { text: 'question',      icon: '?',    cls: 'state-question' },
  [POSE.WAIT]:        { text: 'waiting zZ',    icon: '💤',   cls: 'state-waiting' },
  [POSE.THINKING]:    { text: 'thinking',      icon: '💭',   cls: 'state-thinking' },
  [POSE.CELEBRATE]:   { text: 'celebrate 🎉',  icon: '🎉',   cls: 'state-celebrate' },
  [POSE.ERROR]:       { text: 'error 😵',      icon: '⚠',   cls: 'state-error' },
  [POSE.REPORTING]:   { text: 'reporting',     icon: '📋',   cls: 'state-reporting' },
  [POSE.READING]:     { text: 'researching',   icon: '📚',   cls: 'state-reading' },
  [POSE.COFFEE]:      { text: 'coffee break',  icon: '☕',   cls: 'state-coffee' },
  [POSE.POINTING]:    { text: 'explaining',    icon: '👉',   cls: 'state-pointing' },
  [POSE.WAVING]:      { text: 'waving',        icon: '👋',   cls: 'state-waving' },
  [POSE.WALKING]:     { text: 'walking',       icon: '🚶',   cls: 'state-walking' },
  [POSE.PHONE]:       { text: 'on call',       icon: '📞',   cls: 'state-phone' },
  [POSE.SLEEPING]:    { text: 'resting 💤',    icon: '💤',   cls: 'state-sleeping' },
};

function statusFor(pose, agentState, lang) {
  // If a pose was explicitly set (demo mode etc.), use it. Otherwise
  // derive from the live agent.state coming from the hook bridge.
  let p = pose;
  if (typeof p !== 'number') {
    if (agentState === 'working')  p = POSE.WORK_SONNET;
    else if (agentState === 'waiting')  p = POSE.WAIT;
    else                                p = POSE.IDLE;
  }
  const table = lang === 'ko' ? POSE_STATUS_KO : POSE_STATUS_EN;
  return table[p] || table[POSE.IDLE];
}

// Detail-text matchers → which canteen item id should glow.
// Used to highlight MCPs/Skills while Claude is actually using them.
const TOOL_GLOW_MAP = [
  // MCPs
  { test: (d) => /\b(Bash|bash)\b/.test(d), mcp: 'shell' },
  { test: (d) => /\b(Read|Edit|Write|Grep|Glob|MultiEdit)\b/.test(d), mcp: 'filesystem' },
  { test: (d) => /\b(WebFetch|WebSearch|browser|navigate)\b/i.test(d), mcp: 'browser' },
  { test: (d) => /\bgh\b|github/i.test(d), mcp: 'github' },
  { test: (d) => /memory|knowledge/i.test(d), mcp: 'memory' },
  // Skills
  { test: (d) => /review|코드\s*리뷰/i.test(d), skill: 'review' },
  { test: (d) => /security|보안/i.test(d), skill: 'security-review' },
  { test: (d) => /simplify|단순화/i.test(d), skill: 'simplify' },
  { test: (d) => /\binit\b|CLAUDE\.md/i.test(d), skill: 'init' },
];

export default function GeneralViewer({ activity, topology, mcps, skills, lang, onSelect, onSelectMcp, onSelectSkill }) {
  // Lookup table for converting a branch.name into the full agent record
  // so the AgentPanel can show description / tools / model on click.
  const agentByName = useMemo(() => {
    const map = {};
    for (const a of (topology?.agents || [])) map[a.name] = a;
    return map;
  }, [topology]);
  const openAgent = (name) => {
    if (!onSelect) return;
    const full = agentByName[name];
    if (full) onSelect(full);
    // Fall back to a stub object so the panel still opens for unknown
    // agents (e.g. unnamed subagents traced via Task tool).
    else onSelect({ name, model: 'sonnet', state: 'idle', description: '' });
  };
  // Demo-mode: run a full simulated scenario entirely client-side — the
  // main character cycles poses, fake branches appear, MCPs glow in
  // sequence. NEVER POSTs to backend → zero cost accrual. Stopping the
  // demo clears every simulated state back to empty.
  const [demoIdx, setDemoIdx] = useState(-1); // -1 = demo off
  const [demoActiveMcp, setDemoActiveMcp] = useState(null);
  const [demoActiveSkill, setDemoActiveSkill] = useState(null);
  const [demoBranches, setDemoBranches] = useState([]);
  const demoRef = useRef();
  const demoStepRef = useRef(0);
  useEffect(() => {
    if (demoIdx < 0) {
      if (demoRef.current) clearInterval(demoRef.current);
      setDemoActiveMcp(null);
      setDemoActiveSkill(null);
      setDemoBranches([]);
      demoStepRef.current = 0;
      return;
    }
    // Demo scenario — 16 steps, one per pose, with overlapping MCP /
    // skill / branch events so the scene feels alive.
    demoRef.current = setInterval(() => {
      const step = demoStepRef.current;
      setDemoIdx(step % DEMO_POSE_ORDER.length);
      // Cycle MCP glow (step through filesystem / shell / browser / memory)
      const mcpCycle = ['filesystem', 'shell', 'browser', 'github', 'memory'];
      setDemoActiveMcp(mcpCycle[step % mcpCycle.length]);
      // Occasional skill glow
      if (step % 3 === 2) {
        const sk = ['review', 'security-review', 'simplify', 'init'];
        setDemoActiveSkill(sk[(step / 3 | 0) % sk.length]);
      } else if (step % 3 === 0) {
        setDemoActiveSkill(null);
      }
      // Branches appear after a few steps and accumulate
      if (step === 3) setDemoBranches([{ name: 'dev-lead', count: 1, state: 'working' }]);
      if (step === 6) setDemoBranches((b) => [...b, { name: 'eval-lead', count: 2, state: 'working' }]);
      if (step === 10) setDemoBranches((b) => b.map((x) => ({ ...x, count: x.count + 1 })).concat([{ name: 'mgmt-lead', count: 1, state: 'waiting' }]));
      demoStepRef.current = step + 1;
    }, 1400);
    return () => clearInterval(demoRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demoIdx >= 0]);
  const demoActive = demoIdx >= 0;
  const demoPose = demoActive ? DEMO_POSE_ORDER[demoIdx] : undefined;
  // Derive subagent branches from activity log. We exclude `orchestrator`
  // because the orchestrator IS the central main character — showing it
  // as a branch would be duplicate. Only NON-orchestrator subagents
  // become branches.
  const branches = useMemo(() => {
    const map = new Map();
    for (const ev of activity || []) {
      if (!ev.agent) continue;
      if (['system', 'user', 'orchestrator'].includes(ev.agent)) continue;
      const key = ev.agent;
      const prev = map.get(key) || { name: key, count: 0, last: ev.ts, state: 'idle' };
      prev.count += 1;
      if (ev.ts > prev.last) { prev.last = ev.ts; }
      if (ev.kind === 'state' && ev.detail?.includes('working')) prev.state = 'working';
      map.set(key, prev);
    }
    return Array.from(map.values()).sort((a, b) => b.count - a.count).slice(0, 6);
  }, [activity]);

  // Main Claude is "working" when any orchestrator activity happened
  // in the last 30 s. This lights up a ⚡ speech bubble over the main
  // character so users can see the single-agent case clearly.
  const mainWorking = useMemo(() => {
    const now = Date.now();
    for (const ev of activity || []) {
      if (ev.agent !== 'orchestrator') continue;
      if (!ev.ts) continue;
      const t = Date.parse(ev.ts.endsWith('Z') ? ev.ts : ev.ts + 'Z');
      if (!isFinite(t)) continue;
      if (now - t < 30_000) return true;
    }
    return false;
  }, [activity]);

  // Which MCPs / Skills should currently glow? Glow lasts until the
  // orchestrator is idle for ≥5s (i.e. response finished) so the user
  // can clearly see which tools were used for the last answer.
  const activeToolIds = useMemo(() => {
    if (demoActive) {
      return {
        mcp: demoActiveMcp ? new Set([demoActiveMcp]) : new Set(),
        skill: demoActiveSkill ? new Set([demoActiveSkill]) : new Set(),
      };
    }
    const now = Date.now();
    const mcp = new Set();
    const skill = new Set();
    for (const ev of activity || []) {
      if (!ev.detail) continue;
      if (!ev.ts) continue;
      const ts = Date.parse(ev.ts.endsWith('Z') ? ev.ts : ev.ts + 'Z');
      if (!isFinite(ts)) continue;
      if (now - ts > 30_000) continue;
      for (const m of TOOL_GLOW_MAP) {
        if (!m.test(ev.detail)) continue;
        if (m.mcp) mcp.add(m.mcp);
        if (m.skill) skill.add(m.skill);
      }
    }
    return { mcp, skill };
  }, [activity, demoActive, demoActiveMcp, demoActiveSkill]);

  // Main Claude agent proxy — uses the orchestrator character sheet
  const mainAgent = {
    name: 'orchestrator',
    state: mainWorking ? 'working' : 'idle',
    model: 'opus',
  };

  // Merge real + demo branches (demo overrides when active so the user
  // sees exactly the scripted scenario)
  const shownBranches = demoActive ? demoBranches : branches;

  return (
    <div className="general-viewer">
      <div className="general-header">
        <div className="general-header-row">
          <h2>{t('gen.title', lang)}</h2>
          <button
            className={`gen-demo-btn${demoActive ? ' active' : ''}`}
            onClick={() => setDemoIdx(demoActive ? -1 : 0)}
            title={t('gen.demo_hint', lang)}
          >
            {demoActive ? t('gen.demo_off', lang) : t('gen.demo_on', lang)}
          </button>
        </div>
        <p className="general-hint">
          {t('gen.hint', lang)}
          {demoActive && (
            <span className="gen-demo-pose">
              &nbsp;· pose {demoIdx + 1}/{DEMO_POSE_ORDER.length}
              <span className="gen-demo-posename"> {poseName(demoPose)}</span>
            </span>
          )}
        </p>
      </div>

      <div className="general-body">
        <ArenaCanvas
          lang={lang}
          overlayLeft={
            <div className="arena-wall-left">
              <div className="arena-wall-label">{t('canteen.mcp_label', lang)}</div>
              <div className="arena-shelf">
                {(mcps || []).map((m) => (
                  <ItemTile
                    key={m.id}
                    id={MCP_TILE[m.id] || 'server-rack'}
                    size={72}
                    label={lang === 'ko' ? m.name_ko : m.name_en}
                    onClick={() => onSelectMcp && onSelectMcp(m)}
                    active={activeToolIds.mcp.has(m.id)}
                  />
                ))}
              </div>
            </div>
          }
          overlayRight={
            <div className="arena-wall-right">
              <div className="arena-wall-label">{t('canteen.skill_label', lang)}</div>
              <div className="arena-shelf">
                {(skills || []).map((s) => (
                  <ItemTile
                    key={s.id}
                    id={SKILL_TILE[s.id] || 'book-review'}
                    size={72}
                    label={s.label || s.id}
                    onClick={() => onSelectSkill && onSelectSkill(s)}
                    active={activeToolIds.skill.has(s.id)}
                  />
                ))}
              </div>
            </div>
          }
        >
          <div className="general-arena">
            {/* Guide rings — subtle background pattern, not a real backdrop */}
            <svg className="arena-rings" viewBox="0 0 1000 680" preserveAspectRatio="none">
              <circle cx="500" cy="340" r="280" fill="none" stroke="#2c2c2c" strokeDasharray="3 7" />
              <circle cx="500" cy="340" r="160" fill="none" stroke="#2c2c2c" strokeDasharray="3 7" />
            </svg>

          {/* TOP — main Claude panel (HQ-style box, mirrors the
              orchestrator card in OrgChart custom mode). */}
          <div
            className="gen-main-panel"
            onClick={(e) => { e.stopPropagation(); openAgent('orchestrator'); }}
            style={{ cursor: 'pointer' }}
            title={lang === 'ko' ? '클릭: 상세 보기' : 'Click for details'}
          >
            {(() => {
              const status = statusFor(demoPose, mainAgent.state, lang);
              if (mainAgent.state === 'idle' && !demoActive) return null;
              return (
                <div className={`gen-status-bubble ${status.cls}`}>
                  <span className="gen-status-icon">{status.icon}</span>
                  <span className="gen-status-text">{status.text}</span>
                </div>
              );
            })()}
            <div className="gen-main-tag">{lang === 'ko' ? '메인 · HQ' : 'MAIN · HQ'}</div>
            <Sprite agent={mainAgent} size={220} pose={demoPose} />
            <div className="gen-main-label">
              <span className="gen-main-title">CLAUDE</span>
              <span className="gen-main-sub">{t('gen.main_label', lang)}</span>
            </div>
          </div>

          {/* Measurement-based connector lines — re-computed after every
              render so curves anchor to the *actual* HQ-bottom and
              branch-top positions in world coords. Avoids the
              fall-short look that fixed-percentage paths had. */}
          <ArenaConnectors deps={[shownBranches.length, demoIdx]} />


          {/* BOTTOM — subagent row. Each spawned agent gets its own
              panel sized to match the HQ panel. Unknown agents reuse a
              lead sprite sheet + a "subagent (Sonnet)" label so the
              user can still tell what model fired. */}
          {shownBranches.length > 0 && (
            <div className="gen-branch-row">
              {shownBranches.map((b, i) => {
                const known = isKnownAgent(b.name, lang);
                const hasSheet = HAS_SHEET.has(b.name);
                const spriteName = hasSheet ? b.name : FALLBACK_SPRITES[i % FALLBACK_SPRITES.length];
                const branchModel = b.model || mainAgent.model;
                const label = known
                  ? t(`agent.${b.name}`, lang)
                  : (lang === 'ko' ? `서브에이전트 (${modelTag(branchModel)})` : `subagent (${modelTag(branchModel)})`);
                // In real (non-demo) mode each branch follows its OWN
                // live state (carried in `b.state` from the activity
                // log). Demo mode still uses the orchestrator's pose so
                // the scripted scenario plays in unison.
                const branchState = demoActive ? mainAgent.state : (b.state || 'idle');
                const status = statusFor(demoPose, branchState, lang);
                return (
                  <div
                    key={b.name}
                    className="gen-branch"
                    onClick={(e) => { e.stopPropagation(); openAgent(b.name); }}
                    style={{ cursor: 'pointer' }}
                    title={lang === 'ko' ? '클릭: 상세 보기' : 'Click for details'}
                  >
                    <div className="gen-branch-tag">{lang === 'ko' ? '서브' : 'SUB'}</div>
                    {(branchState !== 'idle' || demoActive) && (
                      <div className={`gen-status-bubble gen-status-bubble--branch ${status.cls}`}>
                        <span className="gen-status-icon">{status.icon}</span>
                        <span className="gen-status-text">{status.text}</span>
                      </div>
                    )}
                    <Sprite
                      agent={{ name: spriteName, state: branchState, model: branchModel }}
                      pose={demoPose}
                      size={168}
                    />
                    <div className="gen-branch-label">
                      <span className="gen-branch-name">{label}</span>
                      <span className="gen-branch-count" title={t('gen.count_suffix', lang)}>
                        {b.count}{lang === 'ko' ? '회' : '×'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {!shownBranches.length && (
            <div className="arena-empty">{t('gen.trace_empty', lang)}</div>
          )}
          </div>
        </ArenaCanvas>
      </div>
    </div>
  );
}

// ── ArenaConnectors — dashed curves linking the main HQ panel to each
//    spawned subagent panel. Measures the DOM each render so the curves
//    always anchor to the *real* panel positions (in world coords),
//    avoiding the fixed-percentage misalignment that the first cut had.
function ArenaConnectors({ deps }) {
  const [paths, setPaths] = useState([]);
  useEffect(() => {
    const main = document.querySelector('.gen-main-panel');
    const branches = Array.from(document.querySelectorAll('.gen-branch'));
    const world = document.querySelector('.arena-canvas-world');
    if (!main || !branches.length || !world) { setPaths([]); return; }

    const worldRect = world.getBoundingClientRect();
    const scale = worldRect.width / WORLD_W;
    if (!scale) { setPaths([]); return; }

    const toWorld = (rect) => ({
      cx: (rect.left + rect.width / 2 - worldRect.left) / scale,
      top: (rect.top - worldRect.top) / scale,
      bottom: (rect.bottom - worldRect.top) / scale,
    });

    const m = toWorld(main.getBoundingClientRect());
    const next = branches.map((br) => {
      const b = toWorld(br.getBoundingClientRect());
      const my = (m.bottom + b.top) / 2;
      // Cubic Bezier with horizontal tangents at both ends so curves
      // leave the HQ vertically and arrive at each branch vertically.
      return `M ${m.cx} ${m.bottom} C ${m.cx} ${my}, ${b.cx} ${my}, ${b.cx} ${b.top}`;
    });
    setPaths(next);
    // We intentionally re-measure on every render whose deps change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  if (!paths.length) return null;
  return (
    <svg
      className="gen-connectors"
      viewBox={`0 0 ${WORLD_W} ${WORLD_H}`}
      preserveAspectRatio="none"
    >
      {paths.map((d, i) => (
        <g key={i}>
          {/* outer glow + shadow under the connector */}
          <path d={d} fill="none" stroke="rgba(0,0,0,0.75)" strokeWidth="10" />
          <path d={d} fill="none" stroke="rgba(255,213,79,0.25)" strokeWidth="8" />
          {/* the visible dashed line */}
          <path d={d} fill="none" stroke="#ffd54f" strokeWidth="4" strokeDasharray="14 9" strokeLinecap="round" />
        </g>
      ))}
    </svg>
  );
}

// ── ArenaCanvas — zoom/pan wrapper, mirrors the OrgTree controls.
//   • Wheel anchored at the cursor for natural zoom
//   • Drag with primary mouse button to pan
//   • Double-click empty area or press the ⌂ button to reset
//   • Children render inside a 1640×1200 "world" so the layout stays
//     stable across viewport sizes — matches the custom-mode OrgTree.
const WORLD_W = 1640;
const WORLD_H = 1100;
const MIN_ZOOM = 0.4;
const MAX_ZOOM = 2.2;

function ArenaCanvas({ children, overlayLeft, overlayRight, lang }) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [didFit, setDidFit] = useState(false);
  const [marquee, setMarquee] = useState(null);
  const dragRef = useRef(null);
  const containerRef = useRef(null);

  // Fit-to-viewport on first mount.
  useEffect(() => {
    if (didFit) return;
    const el = containerRef.current;
    if (!el) return;
    const cw = el.clientWidth;
    const ch = el.clientHeight;
    if (!cw || !ch) return;
    const z = Math.min(cw / WORLD_W, ch / WORLD_H, 1);
    setZoom(z);
    setPan({ x: (cw - WORLD_W * z) / 2, y: (ch - WORLD_H * z) / 2 });
    setDidFit(true);
  }, [didFit]);

  const reset = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const z = Math.min(el.clientWidth / WORLD_W, el.clientHeight / WORLD_H, 1);
    setZoom(z);
    setPan({ x: (el.clientWidth - WORLD_W * z) / 2, y: (el.clientHeight - WORLD_H * z) / 2 });
  }, []);

  // Marquee zoom mirrors OfficeScene: left-drag = box zoom in,
  // reverse-drag = zoom out, Shift+drag = pan. Wheel zoom intentionally
  // disabled so the page can scroll past the canvas to the tabs below.
  const onMouseDown = useCallback((e) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    if (e.button === 1 || e.shiftKey) {
      dragRef.current = { mode: 'pan', startX: e.clientX, startY: e.clientY, panX: pan.x, panY: pan.y, moved: false };
    } else if (e.button === 0) {
      dragRef.current = { mode: 'marquee', sx: mx, sy: my, moved: false };
      setMarquee({ x1: mx, y1: my, x2: mx, y2: my });
    }
  }, [pan]);
  const onMouseMove = useCallback((e) => {
    const d = dragRef.current;
    if (!d) return;
    if (d.mode === 'pan') {
      const dx = e.clientX - d.startX;
      const dy = e.clientY - d.startY;
      if (!d.moved && Math.hypot(dx, dy) < 4) return;
      d.moved = true;
      setPan({ x: d.panX + dx, y: d.panY + dy });
    } else if (d.mode === 'marquee') {
      const rect = containerRef.current.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      d.moved = true;
      setMarquee({ x1: d.sx, y1: d.sy, x2: mx, y2: my });
    }
  }, []);
  const onMouseUp = useCallback(() => {
    const d = dragRef.current;
    if (d?.mode === 'marquee' && marquee) {
      const dx = marquee.x2 - marquee.x1;
      const dy = marquee.y2 - marquee.y1;
      const reverse = dx < 0 || dy < 0;
      const w = Math.abs(dx), h = Math.abs(dy);
      const el = containerRef.current;
      if (el && Math.hypot(dx, dy) > 6) {
        if (reverse) {
          const z = Math.min(el.clientWidth / WORLD_W, el.clientHeight / WORLD_H, zoom);
          setZoom(z);
          setPan({ x: (el.clientWidth - WORLD_W * z) / 2, y: (el.clientHeight - WORLD_H * z) / 2 });
        } else if (w > 8 && h > 8) {
          const left = Math.min(marquee.x1, marquee.x2);
          const top  = Math.min(marquee.y1, marquee.y2);
          const wx = (left - pan.x) / zoom;
          const wy = (top - pan.y) / zoom;
          const ww = w / zoom, wh = h / zoom;
          const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM,
            Math.min(el.clientWidth / ww, el.clientHeight / wh) * 0.95));
          setZoom(newZoom);
          setPan({
            x: (el.clientWidth - ww * newZoom) / 2 - wx * newZoom,
            y: (el.clientHeight - wh * newZoom) / 2 - wy * newZoom,
          });
        }
      }
    }
    dragRef.current = null;
    setMarquee(null);
  }, [marquee, pan, zoom]);
  const onDoubleClick = useCallback((e) => {
    // Reset on double-click anywhere on the canvas EXCEPT inside a
    // clickable panel (HQ / branch / wall overlay). Mirrors OfficeScene.
    if (e.target.closest('.gen-main-panel, .gen-branch, .arena-overlay-left, .arena-overlay-right, .arena-canvas-toolbar')) {
      return;
    }
    reset();
  }, [reset]);

  return (
    <div className="arena-canvas-host">
      <div
        ref={containerRef}
        className="arena-canvas-viewport"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onDoubleClick={onDoubleClick}
      >
        <div
          className="arena-canvas-world"
          style={{
            width: WORLD_W,
            height: WORLD_H,
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0',
          }}
        >
          {children}
        </div>
      </div>
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
      {/* Floating UI overlays — fixed-size, ignore zoom/pan transforms. */}
      {overlayLeft && <div className="arena-overlay-left">{overlayLeft}</div>}
      {overlayRight && <div className="arena-overlay-right">{overlayRight}</div>}
      <div className="scene-help" style={{ top: 'auto', bottom: 12 }}>
        {t('zoom.help', lang)}
      </div>
      <div className="arena-canvas-toolbar">
        <button className="arena-canvas-btn" onClick={() => setZoom((z) => Math.min(MAX_ZOOM, z * 1.15))} title={t('zoom.in', lang)}>＋</button>
        <button className="arena-canvas-btn" onClick={() => setZoom((z) => Math.max(MIN_ZOOM, z / 1.15))} title={t('zoom.out', lang)}>－</button>
        <button className="arena-canvas-btn" onClick={reset} title={t('zoom.reset', lang)}>⌂</button>
        <span className="arena-canvas-zoom">{Math.round(zoom * 100)}%</span>
      </div>
    </div>
  );
}

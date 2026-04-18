import { useEffect, useRef, useState } from 'react';

// ── Grid ────────────────────────────────────────────────────────────
const TILE = 32;
const CHAR = 48;   // character sprite size
const W = 32;      // tiles wide
const H = 20;      // tiles tall

// ── Environment sprites (shared across scene) ───────────────────────
const ENV_TILES = {
  desk:       '/tiles/desk.png',
  desk2:      '/tiles/desk2.png',
  deskWood:   '/tiles/desk-wood.png',
  deskBig:    '/tiles/desk-big.png',
  chair:      '/tiles/chair.png',
  chairOrange:'/tiles/chair-orange.png',
  plant:      '/tiles/plant.png',
  server:     '/tiles/server.png',
  printer:    '/tiles/printer.png',
  water:      '/tiles/water.png',
  coffee:     '/tiles/coffee.png',
  fridge:     '/tiles/fridge.png',
  window:     '/tiles/window.png',
};

// ── Agent placement (tile coords — desk position) ───────────────────
// Team leads sit at the TOP of their team area; members arrange below.
const PLACEMENT = {
  // 총괄 — boss corner
  orchestrator:         { x: 4,  y: 5,  deskW: 3, lead: true },

  // 평가팀 — lead at top, 6 members in 2 rows below
  'eval-lead':          { x: 22, y: 4,  deskW: 2, lead: true },
  'ux-reviewer':        { x: 15, y: 7 },
  'dev-verifier':       { x: 18, y: 7 },
  'user-tester':        { x: 21, y: 7 },
  'admin-tester':       { x: 24, y: 7 },
  'feature-auditor':    { x: 17, y: 9 },
  'industry-researcher':{ x: 22, y: 9 },

  // 개발팀 — lead top, BE row + FE row
  'dev-lead':           { x: 5,  y: 12, deskW: 2, lead: true },
  'be-dashboard':       { x: 2,  y: 15 },
  'be-filebrowser':     { x: 5,  y: 15 },
  'be-tracker':         { x: 8,  y: 15 },
  'fe-dashboard':       { x: 2,  y: 18 },
  'fe-filebrowser':     { x: 5,  y: 18 },
  'fe-tracker':         { x: 8,  y: 18 },

  // 경영지원팀
  'mgmt-lead':          { x: 17, y: 12, deskW: 2, lead: true },
  reporter:             { x: 15, y: 15 },
  hr:                   { x: 19, y: 15 },
};

// ── Area rectangles ─────────────────────────────────────────────────
const AREAS = [
  { id: 'top',     x: 0,  y: 2,  w: 12, h: 6,  tint: 'rgba(232,119,34,0.10)',  label: '총괄' },
  { id: 'eval',    x: 12, y: 2,  w: 20, h: 8,  tint: 'rgba(108,108,108,0.12)', label: '평가팀' },
  { id: 'dev',     x: 0,  y: 10, w: 14, h: 10, tint: 'rgba(140,90,60,0.10)',   label: '개발팀' },
  { id: 'mgmt',    x: 14, y: 10, w: 12, h: 10, tint: 'rgba(120,95,70,0.12)',   label: '경영지원팀' },
  { id: 'kitchen', x: 26, y: 10, w: 6,  h: 10, tint: 'rgba(200,200,200,0.12)', label: '키친 · MCP' },
];

// ── Decor (plants/appliances/servers scattered through the office) ──
const DECOR = [
  // top-left corners
  { t: 'plant',   x: 0,  y: 3 },
  { t: 'plant',   x: 11, y: 3 },
  // eval area corners
  { t: 'plant',   x: 13, y: 3 },
  { t: 'plant',   x: 31, y: 3 },
  { t: 'printer', x: 28, y: 7 },
  // divider plants between top and bottom
  { t: 'plant',   x: 0,  y: 10 },
  { t: 'plant',   x: 6,  y: 10 },
  { t: 'plant',   x: 13, y: 10 },
  { t: 'plant',   x: 25, y: 10 },
  // dev area extras
  { t: 'server',  x: 11, y: 15 },
  { t: 'printer', x: 11, y: 18 },
  { t: 'plant',   x: 0,  y: 18 },
  { t: 'plant',   x: 13, y: 18 },
  // mgmt area
  { t: 'plant',   x: 14, y: 15 },
  { t: 'plant',   x: 21, y: 18 },
  // kitchen strip (MCPs — appliances)
  { t: 'coffee',  x: 27, y: 12 },
  { t: 'water',   x: 29, y: 12 },
  { t: 'fridge',  x: 27, y: 15 },
  { t: 'printer', x: 29, y: 15 },
  { t: 'server',  x: 27, y: 18 },
  { t: 'plant',   x: 30, y: 18 },
];

// ── Component ───────────────────────────────────────────────────────
export default function PixelOffice({ topology, onSelect, selected }) {
  const canvasRef = useRef(null);
  const [sprites, setSprites] = useState(null);
  const topoRef = useRef(topology);
  const selRef = useRef(selected);
  topoRef.current = topology;
  selRef.current = selected;

  // Preload env + per-agent character sprites
  useEffect(() => {
    if (!topology) return;
    const entries = [
      ...Object.entries(ENV_TILES),
      ...topology.agents.map((a) => [`char:${a.name}`, `/tiles/chars/${a.name}.png`]),
    ];
    const loaded = {};
    let remaining = entries.length;
    entries.forEach(([k, path]) => {
      const img = new Image();
      img.onload = () => {
        loaded[k] = img;
        if (--remaining === 0) setSprites(loaded);
      };
      img.onerror = () => {
        if (--remaining === 0) setSprites(loaded);
      };
      img.src = path;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topology && topology.total]);

  // Animation loop
  useEffect(() => {
    if (!sprites) return;
    const ctx = canvasRef.current.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    let t = 0;
    let raf = 0;
    const render = () => {
      t += 1;
      drawScene(ctx, topoRef.current, selRef.current, t, sprites);
      raf = requestAnimationFrame(render);
    };
    render();
    return () => cancelAnimationFrame(raf);
  }, [sprites]);

  const handleClick = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const mx = (e.clientX - rect.left) * scaleX;
    const my = (e.clientY - rect.top) * scaleY;
    let closest = null;
    let minD = 42;
    for (const agent of topology.agents) {
      const p = PLACEMENT[agent.name];
      if (!p) continue;
      const cx = (p.x + (p.deskW || 1) / 2) * TILE;
      const cy = p.y * TILE - CHAR / 2;
      const d = Math.hypot(cx - mx, cy - my);
      if (d < minD) {
        minD = d;
        closest = agent;
      }
    }
    onSelect(closest);
  };

  return (
    <canvas
      ref={canvasRef}
      width={W * TILE}
      height={H * TILE}
      className="office"
      onClick={handleClick}
    />
  );
}

// ═══════════════════════════════════════════════════════════════════
// Scene rendering
// ═══════════════════════════════════════════════════════════════════
function drawScene(ctx, topology, selected, t, sprites) {
  // Floor
  const floor = ctx.createLinearGradient(0, 0, 0, H * TILE);
  floor.addColorStop(0, '#dbc58f');
  floor.addColorStop(1, '#c9ae72');
  ctx.fillStyle = floor;
  ctx.fillRect(0, 0, W * TILE, H * TILE);

  // Floor tile grid
  ctx.strokeStyle = 'rgba(90,60,30,0.09)';
  ctx.lineWidth = 1;
  for (let x = 0; x <= W; x++) {
    ctx.beginPath();
    ctx.moveTo(x * TILE + 0.5, 2 * TILE);
    ctx.lineTo(x * TILE + 0.5, H * TILE);
    ctx.stroke();
  }
  for (let y = 2; y <= H; y++) {
    ctx.beginPath();
    ctx.moveTo(0, y * TILE + 0.5);
    ctx.lineTo(W * TILE, y * TILE + 0.5);
    ctx.stroke();
  }

  // Wall band
  const wall = ctx.createLinearGradient(0, 0, 0, 2 * TILE);
  wall.addColorStop(0, '#9a7d51');
  wall.addColorStop(1, '#7d6339');
  ctx.fillStyle = wall;
  ctx.fillRect(0, 0, W * TILE, 2 * TILE);
  ctx.fillStyle = '#4d3821';
  ctx.fillRect(0, 2 * TILE - 4, W * TILE, 4);

  // Windows
  drawWindow(ctx, 1, 0, 4, 2);
  drawWindow(ctx, 14, 0, 5, 2);
  drawWindow(ctx, 26, 0, 5, 2);

  // Area tints
  for (const a of AREAS) {
    ctx.fillStyle = a.tint;
    ctx.fillRect(a.x * TILE, a.y * TILE, a.w * TILE, a.h * TILE);
    ctx.strokeStyle = 'rgba(60,40,20,0.4)';
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1;
    ctx.strokeRect(a.x * TILE + 1, a.y * TILE + 1, a.w * TILE - 2, a.h * TILE - 2);
    ctx.setLineDash([]);
    ctx.fillStyle = 'rgba(50,30,10,0.8)';
    ctx.font = "bold 10px 'Press Start 2P'";
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(a.label, a.x * TILE + 6, a.y * TILE + 5);
  }

  // Decor (plants/appliances scattered through)
  for (const d of DECOR) {
    drawEnvSprite(ctx, sprites[d.t], d.x, d.y);
  }

  // Desks + chairs (background — drawn before characters)
  for (const [name, p] of Object.entries(PLACEMENT)) {
    const deskSprite = p.lead
      ? (name === 'orchestrator' ? sprites.deskBig : sprites.deskWood)
      : sprites.desk;
    const w = p.deskW || 1;
    if (deskSprite) {
      for (let i = 0; i < w; i++) {
        drawEnvSprite(ctx, deskSprite, p.x + i, p.y);
      }
    }
    const chairSprite = p.lead ? sprites.chairOrange : sprites.chair;
    if (chairSprite) {
      drawEnvSprite(ctx, chairSprite, p.x + Math.floor(w / 2), p.y + 1);
    }
  }

  // Agent characters (drawn in front — they overlap chairs slightly)
  if (topology) {
    for (const agent of topology.agents) {
      const p = PLACEMENT[agent.name];
      if (!p) continue;
      drawAgent(ctx, agent, p, sprites[`char:${agent.name}`],
        selected && selected.name === agent.name, t);
    }
  }

  // Pigeons (tool-call carriers)
  if (topology) {
    const workingCount = topology.agents.filter((a) => a.state === 'working').length;
    const pigeons = Math.min(6, Math.max(1, Math.floor(workingCount / 2) + 1));
    for (let i = 0; i < pigeons; i++) {
      drawPigeon(ctx, t + i * 180, i % 3);
    }
  }
}

// ── Helpers ─────────────────────────────────────────────────────────
function drawEnvSprite(ctx, img, tx, ty) {
  if (!img) return;
  ctx.drawImage(img, tx * TILE, ty * TILE, TILE, TILE);
}

function drawWindow(ctx, tx, ty, tw, th) {
  const px = tx * TILE;
  const py = ty * TILE + 4;
  const pw = tw * TILE;
  const ph = th * TILE - 12;
  ctx.fillStyle = '#3a2713';
  ctx.fillRect(px - 2, py - 2, pw + 4, ph + 4);
  const sky = ctx.createLinearGradient(0, py, 0, py + ph);
  sky.addColorStop(0, '#a8dcf2');
  sky.addColorStop(1, '#74b3d1');
  ctx.fillStyle = sky;
  ctx.fillRect(px, py, pw, ph);
  ctx.fillStyle = 'rgba(255,255,255,0.65)';
  ctx.fillRect(px + 8, py + 10, 18, 4);
  ctx.fillRect(px + 14, py + 7, 10, 3);
  ctx.fillRect(px + pw - 40, py + 20, 22, 4);
  ctx.strokeStyle = '#3a2713';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(px + pw / 2, py);
  ctx.lineTo(px + pw / 2, py + ph);
  ctx.moveTo(px, py + ph / 2);
  ctx.lineTo(px + pw, py + ph / 2);
  ctx.stroke();
}

function drawAgent(ctx, agent, p, charImg, isSelected, t) {
  const state = agent.state || 'idle';
  const phase = t * 0.1 + agent.name.length;
  const bob =
    state === 'working'
      ? Math.sin(phase) * 1.6
      : state === 'waiting'
      ? Math.sin(phase * 0.4) * 0.5
      : Math.sin(phase * 0.2) * 0.3;

  const w = p.deskW || 1;
  const deskCx = (p.x + w / 2) * TILE;
  // Character bottom aligns to desk-top line; sprite is 48 tall
  const charX = Math.round(deskCx - CHAR / 2);
  const charY = Math.round(p.y * TILE - CHAR + 8 + bob); // +8 so the character peeks above the desk

  // State halo (rendered under the character)
  if (state === 'working') {
    const pulse = (Math.sin(phase) + 1) * 0.5;
    ctx.fillStyle = `rgba(255, 215, 64, ${0.2 + pulse * 0.35})`;
    ctx.beginPath();
    ctx.ellipse(deskCx, charY + CHAR - 2, CHAR * 0.55, CHAR * 0.28, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = `rgba(255, 235, 100, ${0.5 + pulse * 0.5})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.ellipse(deskCx, charY + CHAR - 2, CHAR * 0.6, CHAR * 0.32, 0, 0, Math.PI * 2);
    ctx.stroke();
  } else if (state === 'waiting') {
    ctx.fillStyle = 'rgba(80, 95, 130, 0.22)';
    ctx.beginPath();
    ctx.ellipse(deskCx, charY + CHAR - 2, CHAR * 0.45, CHAR * 0.22, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  // Selection ring
  if (isSelected) {
    ctx.strokeStyle = '#ffeb3b';
    ctx.lineWidth = 2;
    ctx.setLineDash([3, 3]);
    ctx.strokeRect(charX - 3, charY - 3, CHAR + 6, CHAR + 6);
    ctx.setLineDash([]);
  }

  // Character sprite (fallback: colored square if not loaded)
  if (charImg && charImg.complete && charImg.naturalWidth > 0) {
    // Dim when waiting
    if (state === 'waiting') {
      ctx.globalAlpha = 0.65;
    }
    ctx.drawImage(charImg, charX, charY, CHAR, CHAR);
    ctx.globalAlpha = 1;
  } else {
    // fallback: colored block
    ctx.fillStyle = agent.color || '#888';
    ctx.fillRect(charX + 12, charY + 12, CHAR - 24, CHAR - 16);
  }

  // State badge (top-right of character)
  if (state === 'working') {
    drawBadge(ctx, charX + CHAR - 4, charY + 4, '#ffc107', '#4a2a00', '!');
  } else if (state === 'waiting') {
    drawBadge(ctx, charX + CHAR - 4, charY + 4, '#8797a8', '#1a2332', 'Z');
  }

  // Name label chip
  const nameW = agent.name.length * 5 + 6;
  ctx.fillStyle = 'rgba(255,255,255,0.9)';
  ctx.fillRect(deskCx - nameW / 2, p.y * TILE + TILE - 2, nameW, 11);
  ctx.strokeStyle = 'rgba(0,0,0,0.3)';
  ctx.lineWidth = 1;
  ctx.strokeRect(deskCx - nameW / 2 + 0.5, p.y * TILE + TILE - 1.5, nameW - 1, 10);
  ctx.fillStyle = '#2a1d0b';
  ctx.font = "6px 'Press Start 2P'";
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(agent.name, deskCx, p.y * TILE + TILE);

  // Model dot
  const modelColor =
    agent.model === 'opus' ? '#ffd54f' : agent.model === 'haiku' ? '#7cc7e8' : '#e57373';
  ctx.fillStyle = modelColor;
  ctx.fillRect(charX + 2, charY + 2, 5, 5);
  ctx.strokeStyle = '#1a1a1a';
  ctx.strokeRect(charX + 2.5, charY + 2.5, 4, 4);
}

function drawBadge(ctx, bx, by, fill, textColor, char) {
  ctx.fillStyle = fill;
  ctx.beginPath();
  ctx.arc(bx, by, 7, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#1a1a1a';
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.fillStyle = textColor;
  ctx.font = "bold 8px 'Press Start 2P'";
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(char, bx, by + 1);
}

function drawPigeon(ctx, t, lane) {
  const laneY = [3.8, 10.2, 19.2][lane];
  const progress = (t * 0.45) % (W * TILE + 80);
  const x = progress - 40;
  const y = laneY * TILE + Math.sin(t * 0.12) * 3;
  ctx.fillStyle = 'rgba(0,0,0,0.25)';
  ctx.fillRect(x, y + 7, 8, 2);
  ctx.fillStyle = '#c0c5c9';
  ctx.fillRect(x, y, 7, 5);
  ctx.fillStyle = '#8a9399';
  ctx.fillRect(x + 5, y - 1, 4, 4);
  ctx.fillStyle = '#111';
  ctx.fillRect(x + 7, y, 1, 1);
  ctx.fillStyle = '#f4a63a';
  ctx.fillRect(x + 8, y + 1, 2, 1);
  ctx.fillStyle = '#f2c94c';
  ctx.fillRect(x - 3, y + 2, 3, 3);
  ctx.strokeStyle = '#8a6a1c';
  ctx.lineWidth = 1;
  ctx.strokeRect(x - 2.5, y + 2.5, 2, 2);
}

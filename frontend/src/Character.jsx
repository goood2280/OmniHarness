// Character.jsx — procedural front-facing pixel-art character (SVG).
//
// Zoo-style: every agent is an animal (fox · cat · owl · bear · panda ·
// rabbit · wolf · raccoon) wearing a suit / hoodie / vest. Each is
// assembled pixel-by-pixel so scale is crisp and colors are tunable.
// If a real PNG sprite exists at `/tiles/chars/<name>.png` we prefer
// that (for future high-quality art drops); otherwise we render the SVG.
//
// Props:
//  - agent:   { name, state } — state 'working' bobs the sprite
//  - size:    px height (defaults to 88)
//  - seated:  hide legs (character is behind a desk)
//  - tint:    team accent color, applied to suit outline

const TONES = {
  fur: {
    orange:  '#e08a45',
    red:     '#c04a2e',
    cream:   '#f1c992',
    grey:    '#8a8a92',
    white:   '#ebe6dc',
    brown:   '#7a4a2a',
    tan:     '#c2935e',
    black:   '#2a2118',
    blue:    '#5e8ab5',
    pink:    '#e6a8b2',
  },
  outfit: {
    navy:    '#2c3656',
    char:    '#2a2a30',
    crimson: '#7a2a2a',
    teal:    '#2c6a6a',
    olive:   '#4a5a2a',
    brown:   '#5a3a22',
    purple:  '#4a2a5a',
    hood:    '#1a3d4a',
  },
};

const SPECIES = [
  'fox', 'cat', 'owl', 'bear', 'panda',
  'rabbit', 'wolf', 'raccoon', 'deer', 'frog',
];

// Per-agent personality. Only the base team is fixed; dynamic agents
// derive a look from name hash.
export const LOOKS = {
  orchestrator:        { species: 'fox',    fur: 'orange', outfit: 'navy',    acc: 'crown',   tie: '#ffd54f', hood: false },
  'dev-lead':          { species: 'owl',    fur: 'brown',  outfit: 'navy',    acc: 'glasses', tie: '#7cc7e8', hood: false },
  'mgmt-lead':         { species: 'bear',   fur: 'tan',    outfit: 'brown',   acc: 'clip',    tie: '#b48f5c', hood: false },
  'eval-lead':         { species: 'cat',    fur: 'white',  outfit: 'crimson', acc: 'magnif',  tie: '#ff9b9b', hood: false },
  reporter:            { species: 'raccoon', fur: 'grey',  outfit: 'brown',   acc: 'clip' },
  hr:                  { species: 'panda',  fur: 'white',  outfit: 'char',    acc: 'clip' },
  'ux-reviewer':       { species: 'rabbit', fur: 'cream',  outfit: 'hood',    acc: 'magnif',  hood: true },
  'dev-verifier':      { species: 'wolf',   fur: 'grey',   outfit: 'hood',    acc: 'check',   hood: true },
  'user-role-tester':  { species: 'fox',    fur: 'red',    outfit: 'hood',    acc: 'check',   hood: true },
  'admin-role-tester': { species: 'owl',    fur: 'white',  outfit: 'hood',    acc: 'shield',  hood: true },
  'security-auditor':  { species: 'bear',   fur: 'black',  outfit: 'char',    acc: 'shield' },
  'domain-researcher': { species: 'deer',   fur: 'brown',  outfit: 'olive',   acc: 'book' },
};

function hashLook(name) {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const furs = Object.keys(TONES.fur);
  const outfits = Object.keys(TONES.outfit);
  const accs = ['headset', 'clip', 'book', 'check', 'glasses'];
  return {
    species: SPECIES[h % SPECIES.length],
    fur: furs[(h >> 2) % furs.length],
    outfit: outfits[(h >> 4) % outfits.length],
    acc: accs[(h >> 6) % accs.length],
    hood: ((h >> 8) & 1) === 1,
  };
}

export function lookFor(agent) {
  if (agent?.name && LOOKS[agent.name]) return LOOKS[agent.name];
  if (agent?.name) return hashLook(agent.name);
  return LOOKS.orchestrator;
}

function P(x, y, c, w = 1, h = 1, key) {
  return <rect key={key || `${x}-${y}-${w}-${h}`} x={x} y={y} width={w} height={h} fill={c} />;
}

// ── Species-specific head ornaments (ears, snout, beak, etc.) ────────
function Ears(species, fur) {
  const darken = darken6(fur);
  switch (species) {
    case 'fox':
    case 'wolf':
    case 'cat':
      // Pointed triangle ears atop the head
      return [
        P(4, 1, fur, 2, 3, 'earL1'),
        P(5, 2, fur, 1, 1, 'earL2'),
        P(10, 1, fur, 2, 3, 'earR1'),
        P(10, 2, fur, 1, 1, 'earR2'),
        P(5, 2, darken, 1, 1, 'earLin'),
        P(10, 2, darken, 1, 1, 'earRin'),
      ];
    case 'rabbit':
      // Tall upright ears
      return [
        P(5, -3, fur, 2, 7, 'rbL'),
        P(9, -3, fur, 2, 7, 'rbR'),
        P(5, -2, '#f8c7cf', 2, 4, 'rbLin'),
        P(9, -2, '#f8c7cf', 2, 4, 'rbRin'),
      ];
    case 'bear':
    case 'panda':
    case 'raccoon':
      // Small round ears (circle-ish)
      return [
        P(4, 2, fur, 2, 2, 'bL'),
        P(10, 2, fur, 2, 2, 'bR'),
        P(5, 3, darken, 1, 1, 'bLin'),
        P(10, 3, darken, 1, 1, 'bRin'),
      ];
    case 'deer':
      // Antlers (silhouette)
      return [
        P(4, 0, '#a0703a', 1, 3, 'deerAntL1'),
        P(3, 1, '#a0703a', 1, 1, 'deerAntL2'),
        P(11, 0, '#a0703a', 1, 3, 'deerAntR1'),
        P(12, 1, '#a0703a', 1, 1, 'deerAntR2'),
        P(5, 2, fur, 2, 2, 'deerL'),
        P(9, 2, fur, 2, 2, 'deerR'),
      ];
    case 'owl':
      // Feather tufts
      return [
        P(4, 2, fur, 2, 2, 'owlL'),
        P(10, 2, fur, 2, 2, 'owlR'),
        P(5, 1, fur, 1, 1, 'owlLtip'),
        P(10, 1, fur, 1, 1, 'owlRtip'),
      ];
    case 'frog':
      // Bulging eye mounts
      return [
        P(4, 3, fur, 2, 2, 'frogL'),
        P(10, 3, fur, 2, 2, 'frogR'),
      ];
    default:
      return [];
  }
}

function Face(species, fur) {
  const out = [];
  // Base head 6×6 at (5,4)
  out.push(P(5, 4, fur, 6, 6));

  // Species face markings
  if (species === 'panda') {
    out.push(P(5, 6, '#1a1a1a', 2, 2)); // left eye patch
    out.push(P(9, 6, '#1a1a1a', 2, 2)); // right eye patch
    out.push(P(6, 7, '#fff', 1, 1));    // pupil L
    out.push(P(9, 7, '#fff', 1, 1));    // pupil R
  } else if (species === 'raccoon') {
    out.push(P(5, 7, '#1a1a1a', 6, 1)); // mask stripe
    out.push(P(6, 7, '#ff9', 1, 1));
    out.push(P(9, 7, '#ff9', 1, 1));
  } else if (species === 'owl') {
    out.push(P(5, 6, '#fff', 2, 2));
    out.push(P(9, 6, '#fff', 2, 2));
    out.push(P(6, 7, '#0d0d0d', 1, 1));
    out.push(P(9, 7, '#0d0d0d', 1, 1));
  } else if (species === 'frog') {
    out.push(P(5, 6, '#fff', 2, 2));
    out.push(P(9, 6, '#fff', 2, 2));
    out.push(P(6, 6, '#0d0d0d', 1, 2));
    out.push(P(9, 6, '#0d0d0d', 1, 2));
  } else {
    // Default eyes
    out.push(P(6, 7, '#0d0d0d'));
    out.push(P(9, 7, '#0d0d0d'));
  }

  // Snout / nose / beak / mouth
  if (species === 'owl') {
    out.push(P(7, 8, '#ffb655', 2, 2)); // beak
  } else if (species === 'frog') {
    out.push(P(5, 9, darken6(fur), 6, 1)); // wide mouth
  } else if (species === 'deer') {
    out.push(P(7, 8, '#fff', 2, 1));
    out.push(P(7, 9, '#111', 2, 1));
  } else if (species === 'cat' || species === 'fox' || species === 'wolf' || species === 'raccoon') {
    // Snout + nose + whisker dots
    out.push(P(6, 9, '#fff4e0', 4, 1));
    out.push(P(7, 8, '#111', 2, 1)); // nose
    out.push(P(6, 10, '#111', 4, 1)); // mouth line
  } else {
    // Bear / panda / rabbit — small muzzle
    out.push(P(7, 9, '#fff4e0', 2, 1));
    out.push(P(7, 9, '#111', 1, 1));
  }
  return out;
}

function darken6(c) {
  // Very small shading helper: just return a darker fixed hue; not exact
  // but good enough for a 1-pixel inner shade.
  if (c === '#e08a45') return '#a15924';
  if (c === '#c04a2e') return '#8a2f1d';
  if (c === '#f1c992') return '#c59e6a';
  if (c === '#8a8a92') return '#5a5a60';
  if (c === '#ebe6dc') return '#b8b2a5';
  if (c === '#7a4a2a') return '#4a2a10';
  if (c === '#c2935e') return '#8a6332';
  if (c === '#2a2118') return '#0a0a05';
  if (c === '#5e8ab5') return '#2e5a8a';
  if (c === '#e6a8b2') return '#a86c76';
  return '#333';
}

function Accessory(acc, accent) {
  const out = [];
  if (acc === 'crown') {
    const g = '#ffd54f';
    out.push(P(5, -1, g, 6, 1, 'cr1'));
    out.push(P(5, 0, g, 1, 1, 'cr2'));
    out.push(P(7, 0, g, 1, 1, 'cr3'));
    out.push(P(9, 0, g, 1, 1, 'cr4'));
    out.push(P(10, 0, g, 1, 1, 'cr5'));
  } else if (acc === 'glasses') {
    out.push(P(5, 7, '#0d0d0d', 2, 1, 'gl1'));
    out.push(P(9, 7, '#0d0d0d', 2, 1, 'gl2'));
    out.push(P(7, 7, '#0d0d0d', 2, 1, 'gl3'));
  } else if (acc === 'headset') {
    const c = accent || '#7cc7e8';
    out.push(P(4, 4, c, 1, 3, 'hs1'));
    out.push(P(11, 4, c, 1, 3, 'hs2'));
    out.push(P(4, 3, c, 8, 1, 'hs3'));
  } else if (acc === 'clip') {
    out.push(P(2, 14, '#cfbf7e', 3, 5, 'cl1'));
    out.push(P(3, 15, '#fff8dc', 1, 3, 'cl2'));
  } else if (acc === 'magnif') {
    out.push(P(11, 13, '#7cc7e8', 2, 2, 'mg1'));
    out.push(P(13, 15, '#666666', 1, 2, 'mg2'));
  } else if (acc === 'check') {
    out.push(P(12, 13, '#4ade80', 2, 1, 'ck1'));
    out.push(P(13, 14, '#4ade80', 1, 1, 'ck2'));
  } else if (acc === 'shield') {
    out.push(P(11, 12, '#9aaabe', 3, 4, 'sh1'));
    out.push(P(12, 13, '#3a6ea5', 1, 2, 'sh2'));
  } else if (acc === 'book') {
    out.push(P(11, 14, '#5a3a22', 3, 4, 'bk1'));
    out.push(P(12, 15, '#fff8dc', 1, 2, 'bk2'));
  }
  return out;
}

function Tie(color) {
  if (!color) return null;
  return [
    P(7, 13, color, 2, 1, 'ti1'),
    P(7, 14, color, 2, 3, 'ti2'),
    P(7, 17, color, 2, 1, 'ti3'),
  ];
}

function Suit(outfitColor, hood, accent) {
  const parts = [];
  const dark = darken6(outfitColor) || '#111';

  // Shoulders
  parts.push(P(3, 11, outfitColor, 10, 2));
  parts.push(P(3, 13, outfitColor, 10, 5));
  // V-neck / collar
  parts.push(P(7, 11, '#0d0d0d', 2, 1));
  parts.push(P(6, 12, dark, 1, 1));
  parts.push(P(9, 12, dark, 1, 1));
  // Suit lapels
  parts.push(P(5, 12, dark, 1, 4));
  parts.push(P(10, 12, dark, 1, 4));
  // Sleeves
  parts.push(P(2, 12, outfitColor, 1, 5));
  parts.push(P(13, 12, outfitColor, 1, 5));
  // Team accent trim at sleeve cuffs
  if (accent) {
    parts.push(P(2, 16, accent, 1, 1));
    parts.push(P(13, 16, accent, 1, 1));
  }
  // Hands (showing through sleeves)
  parts.push(P(2, 17, '#f3d0b0', 1, 2));
  parts.push(P(13, 17, '#f3d0b0', 1, 2));

  if (hood) {
    // Hood around the head + drape behind shoulders
    const hoodC = '#1a3d4a';
    parts.push(P(4, 3, hoodC, 8, 2));
    parts.push(P(3, 5, hoodC, 1, 6));
    parts.push(P(12, 5, hoodC, 1, 6));
    parts.push(P(3, 11, hoodC, 1, 3));
    parts.push(P(12, 11, hoodC, 1, 3));
    // Drawstrings
    parts.push(P(6, 12, '#f0eacb', 1, 3));
    parts.push(P(9, 12, '#f0eacb', 1, 3));
  }
  return parts;
}

/**
 * Character — procedural Zoo-style front-facing pixel art.
 */
export default function Character({ agent, size = 88, seated = false, tint }) {
  const look = lookFor(agent);
  const fur = TONES.fur[look.fur] || TONES.fur.orange;
  const outfit = TONES.outfit[look.outfit] || TONES.outfit.navy;
  const state = agent?.state || 'idle';

  const parts = [];

  // Hood (drawn under the head if hood=true) — handled inside Suit() for z-order
  // Ears / antlers
  for (const el of Ears(look.species, fur)) parts.push(el);
  // Neck
  parts.push(P(7, 10, fur, 2, 1, 'neck'));
  // Face / head
  for (const el of Face(look.species, fur)) parts.push(el);
  // Suit / hoodie
  for (const el of Suit(outfit, look.hood, tint)) parts.push(el);

  if (!seated) {
    // Pants
    parts.push(P(4, 18, '#1f2028', 8, 5, 'pants'));
    parts.push(P(4, 18, '#0d0d0d', 8, 1, 'belt'));
    parts.push(P(7, 18, '#0d0d0d', 2, 5, 'split'));
    parts.push(P(4, 23, '#0d0d0d', 3, 1, 'shoeL'));
    parts.push(P(9, 23, '#0d0d0d', 3, 1, 'shoeR'));
  }

  // Accessories
  for (const el of Accessory(look.acc, tint)) parts.push(el);
  for (const el of Tie(look.tie) || []) parts.push(el);

  const vbH = seated ? 18 : 28;
  const bobbing = state === 'working';

  // Note: do NOT auto-try /tiles/chars/<name>.png here anymore — the new
  // Sprite component handles PNG sheets. Character is the pure SVG
  // fallback used by OfficeScene or by Sprite when the sheet is missing.

  return (
    <svg
      viewBox={`0 -4 16 ${vbH + 4}`}
      width={size * 16 / vbH}
      height={size}
      style={{ imageRendering: 'pixelated', overflow: 'visible' }}
      className={`char char-${state}`}
    >
      <g>{parts}</g>
    </svg>
  );
}

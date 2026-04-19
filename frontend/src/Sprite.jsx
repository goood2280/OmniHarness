// Sprite.jsx — renders a pose-frame from a 4x4 (16-pose) character
// sprite sheet, falling back to the procedural SVG Character when the
// PNG is missing.
//
// Sheet layout (reading order left-to-right, top-to-bottom):
//
//   Row 1 — work states
//     0  IDLE         idle standing
//     1  WORK_SONNET  seated typing, relaxed
//     2  WORK_OPUS    seated typing, intense (hustle)
//     3  QUESTION     standing, hand raised
//
//   Row 2 — mental states
//     4  WAIT         seated leaning back, zzz
//     5  THINKING     hand on chin, looking up
//     6  CELEBRATE    arms raised in victory
//     7  ERROR        facepalm
//
//   Row 3 — activity
//     8  REPORTING    writing on clipboard
//     9  READING      reading a book
//     10 COFFEE       holding coffee mug
//     11 POINTING     explaining / pointing off-screen
//
//   Row 4 — social / motion
//     12 WAVING       hello wave
//     13 WALKING      side-profile walk
//     14 PHONE        on a phone call
//     15 SLEEPING     head down on desk
//
// Props:
//   agent           — { name, state, model }
//   pendingQuestion — override → QUESTION pose
//   pose            — explicit pose index (overrides the state-based default)
//   size            — px height
//
// Pose selection priority (highest first):
//   1. explicit `pose` prop
//   2. pendingQuestion  → QUESTION
//   3. state 'waiting'  → WAIT
//   4. state 'working'  → WORK_OPUS if model=opus else WORK_SONNET
//   5. default          → IDLE

import { useEffect, useState } from 'react';
import Character from './Character';

export const POSE = {
  IDLE:        0,
  WORK_SONNET: 1,
  WORK_OPUS:   2,
  QUESTION:    3,
  WAIT:        4,
  THINKING:    5,
  CELEBRATE:   6,
  ERROR:       7,
  REPORTING:   8,
  READING:     9,
  COFFEE:      10,
  POINTING:    11,
  WAVING:      12,
  WALKING:     13,
  PHONE:       14,
  SLEEPING:    15,
  // Extras shown only in demo mode when the sheet is larger than 4×4
  EXTRA_1:     16,
  EXTRA_2:     17,
  EXTRA_3:     18,
  EXTRA_4:     19,
  EXTRA_5:     20,
  EXTRA_6:     21,
  EXTRA_7:     22,
  EXTRA_8:     23,
};

// Sprite sheet grid. Nano Banana sometimes gives 4×4 (1024×1024,
// what we ask for) and sometimes a wider 6×3 grid (1408×768) when it
// over-packs panels. We measure the image aspect ratio after load and
// pick the matching grid so every sheet renders without cropping.
function gridFor(natW, natH) {
  if (!natW || !natH) return { cols: 4, rows: 4 };
  const aspect = natW / natH;
  // Nano Banana sometimes returns the 4×4 we ask for (1024×1024,
  // aspect 1.0) and sometimes a wider 6×4 grid (1408×768, aspect 1.83).
  if (aspect > 1.4) return { cols: 6, rows: 4 };
  return { cols: 4, rows: 4 };
}

function defaultPose(agent, pendingQuestion) {
  if (pendingQuestion) return POSE.QUESTION;
  const state = agent?.state || 'idle';
  if (state === 'waiting') return POSE.WAIT;
  if (state === 'working') return agent?.model === 'opus' ? POSE.WORK_OPUS : POSE.WORK_SONNET;
  return POSE.IDLE;
}

// Bust the browser cache once per session so freshly-regenerated
// sprite sheets show up immediately instead of getting served the old
// dimensions from the HTTP cache.
const SHEET_CACHE_BUSTER = `?v=${Date.now()}`;

export default function Sprite({ agent, pendingQuestion, pose, size = 128 }) {
  const [sheetState, setSheetState] = useState({ status: null, cols: 4, rows: 4 });
  const sheetSrc = agent?.name
    ? `/tiles/chars/${agent.name}-sheet.png${SHEET_CACHE_BUSTER}`
    : null;

  useEffect(() => {
    if (!sheetSrc) { setSheetState({ status: false, cols: 4, rows: 4 }); return; }
    let cancelled = false;
    const img = new Image();
    img.onload = () => {
      if (cancelled) return;
      const { cols, rows } = gridFor(img.naturalWidth, img.naturalHeight);
      setSheetState({ status: true, cols, rows });
    };
    img.onerror = () => { if (!cancelled) setSheetState({ status: false, cols: 4, rows: 4 }); };
    img.src = sheetSrc;
    return () => { cancelled = true; };
  }, [sheetSrc]);

  if (sheetState.status === false) {
    return <Character agent={agent} size={size} />;
  }
  if (sheetState.status === null) {
    return <div style={{ width: size, height: size, opacity: 0.15 }} />;
  }

  const { cols, rows } = sheetState;
  const p = typeof pose === 'number' ? pose : defaultPose(agent, pendingQuestion);
  // Clamp to the grid so a stray pose index can't show empty panel space.
  const safeP = Math.min(p, cols * rows - 1);
  const col = safeP % cols;
  const row = Math.floor(safeP / cols);

  return (
    <div
      className="sprite-sheet"
      style={{
        width: size,
        height: size,
        backgroundImage: `url(${sheetSrc})`,
        backgroundRepeat: 'no-repeat',
        backgroundSize: `${cols * 100}% ${rows * 100}%`,
        backgroundPosition: cols > 1 && rows > 1
          ? `${(col / (cols - 1)) * 100}% ${(row / (rows - 1)) * 100}%`
          : '0 0',
        imageRendering: 'pixelated',
      }}
    />
  );
}

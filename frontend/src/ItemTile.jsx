// ItemTile.jsx — free-placement pixel-art item (desk, plant, water cooler,
// server, book, etc.). Loads /tiles/items/<id>.png when it exists;
// otherwise renders a simple placeholder so the scene still composes.
//
// Props:
//   id     — e.g. "plant-snake", "water-cooler", "book-review"
//   size   — px height
//   onClick — optional (for MCP / Skill items to open a detail panel)
//   label  — optional caption under the item

import { useEffect, useState } from 'react';

export default function ItemTile({ id, size = 96, onClick, label, title, active = false }) {
  const [ok, setOk] = useState(null);
  const src = `/tiles/items/${id}.png`;

  useEffect(() => {
    let cancelled = false;
    const img = new Image();
    img.onload = () => { if (!cancelled) setOk(true); };
    img.onerror = () => { if (!cancelled) setOk(false); };
    img.src = src;
    return () => { cancelled = true; };
  }, [src]);

  // PNG missing?  Fail quietly.  Decorative items (no label, no click)
  // disappear entirely so we don't clutter the scene with empty
  // placeholder boxes when the backdrop already contains the object
  // painted in.  Informational items (with a label, e.g. MCP/Skill
  // shelf entries) collapse to just the label chip.
  if (ok === false) {
    if (!label) return null;
    return (
      <div
        className={`item-tile item-tile-labelonly${onClick ? ' clickable' : ''}${active ? ' active' : ''}`}
        onClick={onClick}
        title={title || label}
      >
        <div className="item-tile-label">{label}</div>
      </div>
    );
  }

  return (
    <div
      className={`item-tile${onClick ? ' clickable' : ''}${active ? ' active' : ''}`}
      onClick={onClick}
      title={title || label}
    >
      {ok === true ? (
        <img src={src} alt="" style={{ height: size, imageRendering: 'pixelated' }} />
      ) : null}
      {label && ok === true && <div className="item-tile-label">{label}</div>}
    </div>
  );
}

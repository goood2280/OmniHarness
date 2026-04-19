"""generate_assets.py — mint OmniHarness sprite sheets via Gemini.

Per-character sprite sheets (not one-off images).  Each character gets
ONE image containing 5 poses in a horizontal row:

    frame 0 — idle standing (arms at sides)
    frame 1 — seated at desk, relaxed typing   (Sonnet working)
    frame 2 — seated at desk, leaning forward, intense focus   (Opus hustle)
    frame 3 — standing, one hand raised asking a question
    frame 4 — seated, leaning back, casual wait

The GeneralViewer (and later OfficeScene) slices this sheet with CSS
`background-position` to show the frame that matches the agent's current
state / model. If a sheet PNG is missing, the procedural SVG character
still renders as a fallback.

Scope for this first pass: characters that actually show up in the
General Viewer mode (12 base-team agents). Custom-mode dev/domain art
comes later.

Usage:
    pip install google-genai
    # Put GEMINI_API_KEY=... in ./.env at the repo root
    python OmniHarness/scripts/generate_assets.py
    python OmniHarness/scripts/generate_assets.py --agent orchestrator
    python OmniHarness/scripts/generate_assets.py --backdrop
    python OmniHarness/scripts/generate_assets.py --force
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
CHARS_DIR = ROOT / "frontend" / "public" / "tiles" / "chars"
GEN_DIR = ROOT / "frontend" / "public" / "tiles" / "general"
ITEMS_DIR = ROOT / "frontend" / "public" / "tiles" / "items"
CHARS_DIR.mkdir(parents=True, exist_ok=True)
GEN_DIR.mkdir(parents=True, exist_ok=True)
ITEMS_DIR.mkdir(parents=True, exist_ok=True)


# ── .env loader (no external deps) ──────────────────────────────────
def _load_dotenv():
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        f = parent / ".env"
        if not f.exists():
            continue
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
        except Exception:
            pass
        break


_load_dotenv()


# ── Live activity → OmniHarness viewer ──────────────────────────────
# Post each step of the generation pipeline so the General viewer's
# activity log + trace tree reflects image-generation work in real time.
OMNI_URL = os.environ.get("OMNIHARNESS_URL", "http://localhost:8082").rstrip("/")


def _post_activity(agent: str, kind: str, detail: str) -> None:
    try:
        body = json.dumps({"agent": agent, "kind": kind, "detail": detail},
                          ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            OMNI_URL + "/api/activity", data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=1.5).read()
    except (urllib.error.URLError, TimeoutError, Exception):
        pass


def _post_state(agent: str, state: str) -> None:
    try:
        body = json.dumps({"state": state}).encode("utf-8")
        req = urllib.request.Request(
            OMNI_URL + f"/api/agents/{agent}/state", data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=1.5).read()
    except Exception:
        pass


# ── Corrections feedback loop ───────────────────────────────────────
# After each sheet is generated, the human reviewer (Claude) writes
# observations to scripts/art_corrections.md. Subsequent generations
# prepend that file to the prompt so improvements carry forward.
CORRECTIONS_FILE = Path(__file__).resolve().parent / "art_corrections.md"


def _load_corrections() -> str:
    if not CORRECTIONS_FILE.exists():
        return ""
    try:
        return CORRECTIONS_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


# ── Consistent-style preamble ───────────────────────────────────────
STYLE_PREAMBLE = (
    "Modern chunky pixel-art character sheet in a clean 16-bit cozy "
    "office game style. Crisp pixel outlines, flat shading with two tones "
    "of shadow, vibrant but readable palette. Contemporary corporate "
    "office aesthetic (no rustic wood floors). "
)

SHEET_LAYOUT = (
    "Output ONE square sprite sheet arranged as a clean 4x4 grid — "
    "exactly 16 equally-sized square panels, 4 columns by 4 rows, each "
    "panel 256x256 pixels, total image 1024x1024. Panels are arranged "
    "strictly left-to-right then top-to-bottom (reading order). Keep the "
    "character centered within each panel. CRITICAL: the art style, "
    "palette, line weight, pixel density, and character proportions must "
    "be absolutely identical across all 16 panels — same character, same "
    "outfit, same colors, just different poses / expressions / held "
    "objects. Solid magenta (#ff00ff) background filling every non-"
    "character pixel in every panel. No text, labels, gridlines, panel "
    "numbers, borders, or speech bubbles. "
)

POSES = (
    "CRITICAL FRAMING RULE: Panels 1–12 (rows 1, 2, 3) ALL show the "
    "character seated at the SAME modern office desk with the SAME "
    "ergonomic chair, SAME flat-panel monitor, and SAME keyboard in the "
    "SAME position in every one of those 12 panels. Only the "
    "character's pose / expression / held object changes between those "
    "panels — the desk, chair, monitor, keyboard, and coffee mug must "
    "remain pixel-identical across panels 1–12. Panels 13–16 (row 4) "
    "are the OFF-DESK social / motion shots with no desk visible.\n\n"
    "The 16 poses in reading order (left-to-right, then next row):\n"
    "Row 1 — AT DESK, work progression:\n"
    "  1. Seated at desk, hands resting near keyboard, looking at "
    "monitor, relaxed neutral face (idle-at-desk).\n"
    "  2. Seated at desk, both hands on keyboard typing casually, "
    "focused face, monitor showing code (Sonnet normal work).\n"
    "  3. Seated at desk, leaning forward intensely, both hands "
    "pounding the keyboard, sleeves rolled up, wide-eyed determined "
    "expression, monitor glowing brighter (Opus hustle mode).\n"
    "  4. Seated at desk, one hand raised straight up asking a "
    "question, other hand still on keyboard, curious expression.\n"
    "Row 2 — AT DESK, break / mental states:\n"
    "  5. Seated at desk, leaning back in the chair, arms relaxed, eyes "
    "closed, tiny Zzz bubble above head — brief wait.\n"
    "  6. Seated at desk, holding the same coffee mug from the desk with "
    "both hands close to chest, relaxed smile — coffee break.\n"
    "  7. Seated at desk, one hand on chin, eyes up to the side — "
    "thinking about something.\n"
    "  8. Seated at desk, one fist raised in a tight victory punch, "
    "bright smile, small sparkle effects around — celebrating.\n"
    "Row 3 — AT DESK, emotional / communication states:\n"
    "  9. Seated at desk, one hand covering face / facepalm, other hand "
    "loose on desk, slumped shoulders — error / frustration.\n"
    "  10. Seated at desk, arms stretched up overhead in a big stretch, "
    "eyes closed, relaxed yawn — stretch break.\n"
    "  11. Seated at desk, one hand holding a smartphone to the ear, "
    "other hand gesturing, talking — phone call.\n"
    "  12. Seated at desk, head down face-first on the keyboard, arms "
    "dangling limp at sides — exhausted / sleeping.\n"
    "Row 4 — OFF-DESK, social / motion (no desk in these panels):\n"
    "  13. Standing full-body portrait, arms at sides, friendly neutral "
    "expression (reference pose).\n"
    "  14. Half-body shot, waving hello with one hand raised, warm "
    "smile.\n"
    "  15. Walking in profile (side view) — seen from the left side, "
    "one leg forward mid-step, carrying no props.\n"
    "  16. Standing holding a clipboard with a pen, writing, focused "
    "(reporting / out-of-desk work).\n"
)


# ── Character identities ────────────────────────────────────────────
# Each entry is a short description of the animal + outfit; the script
# wraps it with STYLE_PREAMBLE + SHEET_LAYOUT + POSES.
CHARACTERS: dict[str, str] = {
    # ── Tier 1 (HQ) — executive, formal.
    "orchestrator":
        "An orange fox character. Business-formal: sharp navy suit, "
        "crisp white dress shirt, red tie. Small golden crown on head "
        "marking HQ / CEO status. Confident executive demeanor.",

    # ── Tier 2 (Team leads) — mixed, each lead's outfit reflects the
    # team they run. Dev-lead is senior engineer (casual tech), eval-
    # lead is QA lead (smart casual + magnifier), mgmt-lead is the
    # only formally suited lead.
    "dev-lead":
        "A brown owl character. SENIOR ENGINEER look: wearing a "
        "charcoal zip-up tech hoodie over a dark t-shirt, dark jeans, "
        "black over-ear headset slung around the neck, wire-frame "
        "glasses, a pencil tucked behind the ear. Slim silver laptop "
        "sticker-covered. No tie, no suit. Casual but authoritative.",
    "mgmt-lead":
        "A friendly tan bear character. Business-smart: brown "
        "corduroy blazer over a cream shirt with a tan tie, holding "
        "a clipboard.",
    "eval-lead":
        "A white cat character with sharp green eyes. Smart-casual: "
        "a crimson cardigan over a white mock-neck top, dark trousers, "
        "magnifying glass clipped to belt, small notepad in one hand.",

    # ── Mgmt team — admin office attire.
    "reporter":
        "A grey raccoon character in a brown vest over a white dress "
        "shirt, rolled-up scroll tucked under one arm.",
    "hr":
        "A panda character in a charcoal blouse and dark trousers, "
        "holding a stack of printed HR documents.",

    # ── Eval team — QA engineers, hoodie + headset tech-casual.
    "ux-reviewer":
        "A cream rabbit character wearing a soft pink zip hoodie over "
        "a white t-shirt, dark jeans. Tablet in one hand, magnifying "
        "glass dangling on a lanyard.",
    "dev-verifier":
        "A grey wolf character wearing a black tech hoodie with a "
        "green checkmark patch on the chest, dark jeans, black "
        "over-ear gaming headset with a boom mic.",
    "user-role-tester":
        "A red fox character wearing an orange hi-vis vest OVER a "
        "charcoal zip hoodie, dark jeans, holding a smartphone in "
        "one hand.",
    "admin-role-tester":
        "A white snowy owl character wearing a dark navy hoodie with "
        "a silver shield logo on the chest, dark cargo pants, ring of "
        "keys clipped to a belt loop, headset around neck.",
    "security-auditor":
        "A black bear character wearing a dark grey tactical hooded "
        "jacket, dark cargo pants, small glowing translucent blue "
        "shield badge on the chest.",
    "domain-researcher":
        "A brown deer character with soft antlers, wearing a white "
        "lab coat OVER an olive sweater, holding a glowing blue "
        "crystal cube.",

    # ── Dev team (catalog) — developer tech-casual. Each dev has a
    # DIFFERENT personality-outfit combo but all follow the "hoodie /
    # t-shirt + headset + laptop-sticker energy" of a real dev floor.
    "dev-dashboard":
        "A grey tabby cat developer in a navy pullover hoodie, light "
        "jeans, stickered laptop on desk, black over-ear headphones "
        "on the head, monitor shows bar charts.",
    "dev-spc":
        "A brown bear developer in a heather-grey hooded sweatshirt "
        "with a math-symbol print, dark jeans, wired earbuds, monitor "
        "shows a statistical control line chart.",
    "dev-wafer-map":
        "An owl developer in safety goggles pushed up on the head, "
        "a blue work hoodie, dark jeans, monitor shows a circular "
        "wafer map.",
    "dev-ml":
        "A fennec fox with huge ears, developer wearing a purple "
        "oversized crewneck sweatshirt with a neural-net print, "
        "dark jeans, round headphones on the ears, monitor shows a "
        "neural network graph.",
    "dev-ettime":
        "An otter developer in a teal hoodie with the hood half up, "
        "dark jeans, analog watch, monitor shows a time-series "
        "heatmap.",
    "dev-tablemap":
        "A rat developer in a grey zip hoodie over a band t-shirt, "
        "dark jeans, black headset on the head, monitor shows a "
        "highlighted spreadsheet grid.",
    "dev-tracker":
        "A hedgehog developer in a green retro gamer t-shirt and a "
        "black half-zip hoodie around the waist, dark jeans, black "
        "headphones, monitor shows a kanban board.",
    "dev-filebrowser":
        "A mouse developer in denim overalls over a grey tee, black "
        "earbuds, monitor shows a file-tree explorer.",
    "dev-admin":
        "A black-and-white cat developer in a white button-down "
        "rolled at the sleeves, dark jeans, lanyard with an admin "
        "badge, monitor shows a user admin panel.",
    "dev-messages":
        "A cockatoo developer in a pink graphic hoodie, dark jeans, "
        "pink over-ear headphones, monitor shows a chat window with "
        "speech bubbles.",

    # ── Domain specialists — semiconductor-fab subject matter experts.
    "process-tagger":
        "A red panda specialist in a navy zip hoodie with a small "
        "wafer-icon patch on the sleeve, dark jeans, ESD wrist strap, "
        "monitor shows process-step tags / lot history.",
    "causal-analyst":
        "A grey wolf specialist in a charcoal turtleneck under an "
        "olive cardigan, slim glasses, holding a tablet, monitor "
        "shows a causal-graph diagram.",
    "dvc-curator":
        "A platinum-grey rabbit specialist in a slate-blue tech "
        "vest over a white shirt, holding a small server-disk icon, "
        "monitor shows a Git-like data-version branch tree.",
    "adapter-engineer":
        "A brown bear specialist in a denim work jacket over a "
        "grey henley, tool-belt with a spanner, monitor shows two "
        "system-icon nodes connected by a glowing pipe.",
}


# ── Free-placement item tiles ───────────────────────────────────────
# Individual pixel-art furniture / tech items, each on a solid magenta
# background for easy keying. These are composed by the scene engine
# at arbitrary (x, y) just like a tile-based RPG.

ITEM_STYLE = (
    "Single item centered in the frame, shown in 3/4 perspective (slight "
    "tilt from above, same angle across ALL items so they compose "
    "together). Modern pixel-art tile asset, clean outlines, flat two-tone "
    "shading, modern office aesthetic (no rustic wood). 256x256 image, "
    "solid magenta (#ff00ff) background filling every non-item pixel "
    "(for chroma-key transparency). No text, no shadow on the background, "
    "the item should cast a short drop-shadow directly beneath itself. "
)

ITEMS: dict[str, str] = {
    # Desks / seating
    "desk-modern":      "A clean modern white standing desk with a sleek flat-panel monitor, wireless keyboard, small notepad, and a beige coffee mug.",
    "chair-ergo":       "A modern mesh-back ergonomic office chair, charcoal grey, 5-wheel base.",
    "chair-exec":       "A tall executive leather office chair, deep brown, high backrest with tufted diamond pattern.",
    # Plants / decor
    "plant-snake":      "A tall snake plant (Sansevieria) in a matte white ceramic pot.",
    "plant-monstera":   "A medium monstera plant with large split leaves, in a terracotta pot.",
    "lamp-arc":         "A tall arc floor lamp with a brushed-steel stem and white shade.",
    "rug-round":        "A round geometric area rug, muted navy and cream chevron pattern, seen from slight 3/4 angle.",
    # Canteen appliances (MCP metaphor: each MCP = one appliance)
    "water-cooler":     "A modern bottled water cooler with a transparent 5-gallon jug, blue and grey plastic body, two taps (red + blue).",
    "coffee-machine":   "A modern chrome espresso machine with portafilter, single cup glass underneath.",
    "fridge":           "A tall modern stainless-steel double-door refrigerator, slim profile.",
    "printer":          "A modern white multifunction office printer, slim, minimal front panel.",
    "server-rack":      "A short modern server rack cabinet with blinking LEDs and cable management at the back.",
    # Skills (recipe-book metaphor)
    "book-review":      "A thick hardcover book labeled 'CODE REVIEW' with a green bookmark ribbon, standing upright.",
    "book-security":    "A hardcover book labeled 'SECURITY' with a red lock icon on the cover, standing upright.",
    "book-simplify":    "A hardcover book labeled 'SIMPLIFY' with a lightbulb icon on the cover, standing upright.",
    "book-init":        "A hardcover book labeled 'INIT' with a rocket icon on the cover, standing upright.",
    # Shared shelving / surfaces
    "bookshelf":        "A tall modern open bookshelf with four shelves, empty so books can be composed on top. Matte black frame, oak shelves.",
    "counter-long":     "A long white laminate service counter / cabinet, eye-level height, plain top surface for placing appliances on top of it.",
    "whiteboard":       "A wall-mounted whiteboard with a thin black aluminum frame, a single sticky note in the corner.",
    "monitor-wall":     "A wall-mounted large flat-panel display showing abstract blue charts and code, slim bezel.",
}


# Backdrop for the General viewer canvas — a real modern IT startup
# office, NOT a sci-fi arena. Seen from a straight-on perspective so a
# character placed at center reads as 'sitting in the middle of the
# open-plan office'. No glowing guide circles, no futuristic tech pods.
BACKDROP_PROMPT = (
    "Pixel art interior of a modern tech-startup open-plan office. "
    "Daylight streaming from a floor-to-ceiling window on the right. "
    "Straight-on view at desk height. Light hardwood or grey carpet "
    "floor. Exposed concrete ceiling with track lighting. Soft, "
    "neutral, contemporary startup-office palette: off-white walls, "
    "warm wood accents, muted blue and yellow highlights. Wide 16:10 "
    "layout, 1920x1200. No characters, no text, no watermark.\n\n"
    "CRITICAL LAYOUT — the scene MUST contain SIX clearly-readable, "
    "EMPTY workstation 'slots' arranged so that a character sprite "
    "placed on top of any slot reads as 'sitting / standing at that "
    "station'. Each slot is empty (no character, no chair occupant) "
    "and the rest of the room is decor only.\n"
    "  • SLOT A — center-bottom, foreground: a single executive desk "
    "    with a high-back leather chair viewed from behind, large "
    "    monitor, keyboard, coffee mug. This is THE main desk.\n"
    "  • SLOT B — upper-left third: a whiteboard wall covered with "
    "    colorful sticky notes, a desk + monitor + chair facing it.\n"
    "  • SLOT C — upper-center: a large wall-mounted flat-panel TV "
    "    showing an abstract bar chart, with a small standing-meeting "
    "    spot (rug + low side table) directly in front of it.\n"
    "  • SLOT D — upper-right third: a glass-walled meeting room "
    "    with a conference table visible through the glass; an open "
    "    door on the near side so a character placed there reads as "
    "    'just stepped out of the meeting room'.\n"
    "  • SLOT E — lower-left corner: a tall snake-plant in a matte "
    "    planter beside a small lounge chair.\n"
    "  • SLOT F — lower-right area, foreground: a second desk + "
    "    monitor + chair, mirror of slot B but on the right side.\n"
    "Leave a clean walkable floor band between the four upper slots "
    "(B, C, D) and the three foreground slots (E, A, F) so the "
    "compositor can drop sprites without any of them overlapping "
    "furniture from another slot. Distribute snake plants / monstera "
    "in the gaps between slots for atmosphere only.\n"
    + STYLE_PREAMBLE
)


def _seed_for(name: str) -> int:
    # Gemini wants int32 (max ~2.1B); trim to 7 hex chars = ~268M
    return int(hashlib.sha256(name.encode()).hexdigest()[:7], 16)


def _ensure_client():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY in .env (or GOOGLE_API_KEY).", file=sys.stderr)
        sys.exit(2)
    try:
        from google import genai
    except ImportError:
        print("ERROR: pip install google-genai", file=sys.stderr)
        sys.exit(2)
    return genai.Client(api_key=api_key)


MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")


def _is_magenta(r: int, g: int, b: int, strict: bool = False) -> bool:
    """Return True if (r,g,b) is plausibly the magenta backdrop.

    Pure #ff00ff is R=255, G=0, B=255. Gemini's output anti-aliases
    edges so we accept a wide cone around that hue: R and B must both
    be well above G, and R,B themselves reasonably saturated."""
    if strict:
        return r >= 230 and b >= 230 and g <= 30 and (r - g) >= 180 and (b - g) >= 180
    # Looser: anything visibly magenta-ish
    return (r >= 140 and b >= 140
            and g <= 130
            and (r - g) >= 60
            and (b - g) >= 60
            and abs(r - b) <= 90)


def _chroma_key(path: Path) -> None:
    """Strip the magenta (#ff00ff-ish) backdrop, including anti-aliased
    edges. Uses numpy for speed when available, plain Pillow otherwise.

    Strategy: vectorise a magenta-ness score per pixel — how strongly
    R and B dominate G — and map high scores to full transparency with
    a soft cutoff so AA edges fade cleanly instead of leaving a halo."""
    try:
        from PIL import Image
    except ImportError:
        print("  [chroma] Pillow not installed; skipping chroma-key")
        return
    try:
        img = Image.open(path).convert("RGBA")
    except Exception as e:
        print(f"  [chroma] could not open {path}: {e}")
        return

    try:
        import numpy as np
    except ImportError:
        return _chroma_key_slow(img, path)

    arr = np.array(img)
    r = arr[..., 0].astype(np.int16)
    g = arr[..., 1].astype(np.int16)
    b = arr[..., 2].astype(np.int16)
    a = arr[..., 3]

    # Score ranges 0–255 roughly; higher = more magenta.
    # min(r,b) − g rewards both R and B being above G; subtract |r−b|
    # to avoid killing neutral pinks where R and B diverge a lot.
    score = np.minimum(r, b) - g - (np.abs(r - b) // 2)

    # Full kill above this, partial fade between this and `soft_floor`.
    # Tighter cutoffs than the first version — the real artifacts we
    # need to scrub are AA-residue pixels like RGB(55, 0, 53) with
    # score ~52, which snuck through the old hard=90 threshold.
    hard = 45
    soft_floor = 15

    # Pixels clearly NOT magenta (low score) keep their alpha.
    # Pixels clearly magenta (score >= hard) → alpha 0.
    # In between → linear fade.
    kill = score >= hard
    fade_mask = (score >= soft_floor) & (score < hard)

    new_alpha = a.astype(np.int16)
    new_alpha[kill] = 0
    # Linear 1→0 fade across [soft_floor .. hard)
    fade_amount = (score - soft_floor).astype(np.float32) / float(hard - soft_floor)
    fade_amount = np.clip(fade_amount, 0.0, 1.0)
    new_alpha[fade_mask] = (a[fade_mask].astype(np.float32) *
                            (1.0 - fade_amount[fade_mask])).astype(np.int16)
    new_alpha = np.clip(new_alpha, 0, 255).astype(np.uint8)

    arr[..., 3] = new_alpha
    # For fully-killed pixels, also zero RGB so premultiplied / downstream
    # filters don't leak pink.
    killed = new_alpha == 0
    arr[..., 0][killed] = 0
    arr[..., 1][killed] = 0
    arr[..., 2][killed] = 0

    cleared = int(kill.sum())
    faded = int(fade_mask.sum())

    # ── Second pass: flood-fill near-black pixels that are CONNECTED to
    #    image edges. This strips the black matte / panel borders Nano
    #    Banana sometimes draws, while preserving interior black (which
    #    is the character outline).
    border_removed = _strip_edge_connected_dark(arr)
    if border_removed:
        killed2 = arr[..., 3] == 0
        arr[..., 0][killed2] = 0
        arr[..., 1][killed2] = 0
        arr[..., 2][killed2] = 0

    # ── Third pass (erode): every partially-transparent pixel that has
    #    ≥2 fully-transparent 4-neighbours is an AA residue sliver — kill
    #    it. Repeat a few times so thin outlines of background colour
    #    left over between character and transparency dissolve away.
    eroded = _erode_partial_alpha(arr, iterations=6)
    if eroded:
        killed3 = arr[..., 3] == 0
        arr[..., 0][killed3] = 0
        arr[..., 1][killed3] = 0
        arr[..., 2][killed3] = 0

    # ── Final pass: strip near-white backgrounds. Some Nano Banana
    #    generations drop the magenta prompt and return white-backdrop
    #    sheets instead — those render as visible white rectangles when
    #    composited onto the office scene. Kill them too.
    white_cleared = _strip_white_bg(arr, threshold=240)

    Image.fromarray(arr, "RGBA").save(path)
    print(f"  [chroma] {path.name}: killed={cleared}, faded={faded}, "
          f"border_black={border_removed}, eroded={eroded}, "
          f"white_cleared={white_cleared}")


def _strip_white_bg(arr, threshold: int = 240) -> int:
    """Alpha-out every pixel whose RGB is all >= threshold (near-white).

    Only runs if at least one corner pixel is near-white — avoids
    nuking legitimate white highlights on art that already had a clean
    transparent background."""
    try:
        import numpy as np
    except ImportError:
        return 0
    h, w, _ = arr.shape
    corners = [arr[0, 0], arr[0, w - 1], arr[h - 1, 0], arr[h - 1, w - 1]]
    if not any(c[0] >= threshold and c[1] >= threshold and c[2] >= threshold for c in corners):
        return 0
    r = arr[..., 0]; g = arr[..., 1]; b = arr[..., 2]
    mask = (r >= threshold) & (g >= threshold) & (b >= threshold)
    changed = int(mask.sum())
    arr[..., 3][mask] = 0
    return changed


def _erode_partial_alpha(arr, iterations: int = 2) -> int:
    """Kill partially-transparent pixels that neighbour transparent ones.

    AA residue at chroma-keyed edges often leaves thin 1–2 px lines of
    low-alpha pixels that look like a faint outline around characters.
    Eroding them in a few passes removes the outline cleanly while
    keeping character interior untouched (those pixels are alpha 255)."""
    try:
        import numpy as np
    except ImportError:
        return 0
    h, w, _ = arr.shape
    alpha = arr[..., 3]
    total = 0
    for _ in range(iterations):
        mask_trans = alpha == 0
        # Count transparent 4-neighbours per pixel
        tn = np.zeros_like(alpha, dtype=np.int16)
        tn[1:,  :] += mask_trans[:-1, :]
        tn[:-1, :] += mask_trans[1:,  :]
        tn[:, 1:]  += mask_trans[:, :-1]
        tn[:, :-1] += mask_trans[:, 1:]
        # Partial-alpha pixels bordering any transparency → kill them
        # if they're not solidly opaque (≥240). This peels residue AA
        # lines one pass at a time; over 6 passes a thin halo fully
        # dissolves.
        target = (alpha > 0) & (alpha < 240) & (tn >= 1)
        count = int(target.sum())
        if count == 0:
            break
        alpha[target] = 0
        total += count
    arr[..., 3] = alpha
    return total


def _strip_edge_connected_dark(arr) -> int:
    """Flood-fill near-black + already-transparent pixels from image
    edges. Anything reachable via this fill must be background (matte /
    panel border) and is knocked to alpha=0. Character outline strokes
    in the middle of a panel stay intact because they aren't connected
    to the edge.

    Also used to bleed the fill through individual panel gutters —
    gutters are typically lines of uniform near-black that touch all
    four outer edges of their panel, so the fill enters them from the
    image border and then spreads along the line."""
    try:
        import numpy as np
    except ImportError:
        return 0
    h, w, _ = arr.shape
    alpha = arr[..., 3]
    r = arr[..., 0].astype(np.int16)
    g = arr[..., 1].astype(np.int16)
    b = arr[..., 2].astype(np.int16)
    # "background-ish" = already transparent OR very dark (R+G+B < 60)
    # OR still has a faint magenta tint (G low) — the generator sometimes
    # leaves a pale greyish magenta at the border after chroma key.
    brightness = r + g + b
    bg = (alpha == 0) | (brightness < 60)

    visited = np.zeros((h, w), dtype=bool)
    from collections import deque
    q = deque()
    # Seed from the outer frame
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))

    changed = 0
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        if visited[y, x]:
            continue
        if not bg[y, x]:
            continue
        visited[y, x] = True
        if alpha[y, x] != 0:
            alpha[y, x] = 0
            changed += 1
        q.append((x - 1, y)); q.append((x + 1, y))
        q.append((x, y - 1)); q.append((x, y + 1))

    arr[..., 3] = alpha
    return changed


def _chroma_key_slow(img, path):
    """Fallback used when numpy isn't installed."""
    from PIL import Image
    px = img.load()
    w, h = img.size
    changed = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            score = min(r, b) - g - abs(r - b) // 2
            if score >= 90:
                px[x, y] = (0, 0, 0, 0); changed += 1
            elif score >= 40:
                fade = (score - 40) / 50.0
                px[x, y] = (r, g, b, int(a * (1 - fade)))
                changed += 1
    img.save(path)
    print(f"  [chroma] {path.name}: changed={changed}")


def _gen_one(client, prompt: str, out: Path, seed: int | None = None,
             agent_for_viewer: str = "orchestrator",
             label: str = "", chroma: bool = True) -> bool:
    """Generate one image via Gemini, write to `out`, and stream progress
    into the OmniHarness viewer so users see the pipeline live."""
    _post_state(agent_for_viewer, "working")
    _post_activity(agent_for_viewer, "invoke",
                   f"🎨 Gemini 이미지 생성 시작: {label or out.name}")
    ok = False
    try:
        from google.genai import types
        cfg_kwargs = {"response_modalities": ["IMAGE"]}
        if seed is not None:
            cfg_kwargs["seed"] = seed
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(**cfg_kwargs),
        )
    except Exception as e:
        print(f"  failed: {e}")
        _post_activity(agent_for_viewer, "error",
                       f"Gemini 요청 실패: {str(e)[:120]}")
        _post_state(agent_for_viewer, "idle")
        return False

    for candidate in getattr(resp, "candidates", []) or []:
        parts = getattr(getattr(candidate, "content", None), "parts", []) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if not inline or not getattr(inline, "data", None):
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(inline.data)
            _post_activity(agent_for_viewer, "tool",
                           f"✅ 이미지 저장: {out.name} ({len(inline.data)//1024}KB)")
            if chroma:
                _post_activity(agent_for_viewer, "tool",
                               f"🔲 크로마키 처리: {out.name}")
                _chroma_key(out)
            ok = True
            break
        if ok:
            break

    if not ok:
        print("  no image returned")
        _post_activity(agent_for_viewer, "error",
                       f"이미지 응답 없음: {out.name}")
    _post_state(agent_for_viewer, "idle")
    return ok


def build_character_prompt(name: str, identity: str, extra: str = "") -> str:
    corrections = _load_corrections()
    correction_block = ""
    if corrections:
        correction_block = (
            "\n\n# Prior-review corrections (apply these FIRST, they override "
            "anything conflicting below):\n" + corrections + "\n\n"
        )
    extra_block = f"\n\nAdditional guidance for this attempt:\n{extra}\n" if extra else ""
    return (
        correction_block +
        STYLE_PREAMBLE +
        f"Character subject: {identity} " +
        SHEET_LAYOUT +
        POSES +
        f"The same {name} character identity is preserved across all 16 panels." +
        extra_block
    )


def build_item_prompt(name: str, description: str) -> str:
    corrections = _load_corrections()
    correction_block = ""
    if corrections:
        correction_block = (
            "# Prior-review corrections:\n" + corrections + "\n\n"
        )
    return correction_block + STYLE_PREAMBLE + ITEM_STYLE + f"\n\nItem: {description}"


def _generate_sheet(client, name: str, identity: str, out: Path,
                    extra_guidance: str = "") -> bool:
    prompt = build_character_prompt(name, identity, extra=extra_guidance)
    return _gen_one(client, prompt, out,
                    seed=_seed_for(f"sheet:{name}:{extra_guidance}"),
                    agent_for_viewer=name if name == "orchestrator" else "orchestrator",
                    label=f"{name} 스프라이트 시트 (16 포즈)")


def run(only_char: str | None, do_backdrop: bool, force: bool,
        do_items: bool = True, only_item: str | None = None,
        evaluate: bool = False, retry: int = 0) -> None:  # eval knobs kept for CLI compat
    client = _ensure_client()

    generated_chars: list[tuple[str, Path]] = []
    generated_items: list[tuple[str, Path]] = []

    # ── Characters ─────────────────────────────────────────────────
    print("== character sprite sheets ==")
    for name, identity in CHARACTERS.items():
        if only_char and only_char != name:
            continue
        out = CHARS_DIR / f"{name}-sheet.png"
        if out.exists() and not force:
            print(f"  [skip] {out.name}")
            generated_chars.append((name, out))
            continue
        print(f"  → {out.name}")
        if _generate_sheet(client, name, identity, out):
            generated_chars.append((name, out))
        time.sleep(0.8)

    # ── Item tiles (game-like furniture/appliances/books) ──────────
    if do_items and not only_char:
        print("== item tiles ==")
        for name, desc in ITEMS.items():
            if only_item and only_item != name:
                continue
            out = ITEMS_DIR / f"{name}.png"
            if out.exists() and not force:
                print(f"  [skip] {out.name}")
                generated_items.append((name, out))
                continue
            print(f"  → {out.name}")
            prompt = build_item_prompt(name, desc)
            if _gen_one(client, prompt, out, seed=_seed_for(f"item:{name}")):
                generated_items.append((name, out))
            time.sleep(0.8)

    if do_backdrop:
        print("== general viewer backdrop ==")
        out = GEN_DIR / "backdrop.png"
        if out.exists() and not force:
            print(f"  [skip] {out.name}")
        else:
            print(f"  → {out.name}")
            # Backdrops are full-bleed scenes — NO chroma-keying.
            _gen_one(client, BACKDROP_PROMPT, out,
                     seed=_seed_for("general:backdrop"),
                     chroma=False,
                     label="제너럴 뷰어 배경")

    # NOTE: consistency evaluation is handled by the human-in-the-loop
    # reviewer (Claude). After each generation, the reviewer inspects the
    # PNG and writes observations to scripts/art_corrections.md; the next
    # generation picks them up via _load_corrections(). This is slower
    # but produces a better match to the curator's taste than a vision
    # model self-grading.
    print(
        "\n== review step ==\n"
        "  Review the generated PNG(s) and append any corrections to:\n"
        f"    {CORRECTIONS_FILE}\n"
        "  Then re-run this script (--force to regenerate the same sheet)."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", help="generate just this one character sheet")
    ap.add_argument("--item", help="generate just this one item tile")
    ap.add_argument("--backdrop", action="store_true",
                    help="also (re-)generate the General viewer backdrop")
    ap.add_argument("--only-backdrop", action="store_true",
                    help="skip everything else, only generate the backdrop")
    ap.add_argument("--no-items", action="store_true",
                    help="skip item tile generation")
    ap.add_argument("--force", action="store_true",
                    help="regenerate even if the PNG exists")
    ap.add_argument("--no-eval", action="store_true",
                    help="skip the post-generation consistency evaluation")
    ap.add_argument("--retry", type=int, default=1,
                    help="max re-generation rounds for outliers (default 1)")
    args = ap.parse_args()

    if args.only_backdrop:
        run(only_char="__none__", do_backdrop=True, force=args.force,
            do_items=False)
    else:
        run(only_char=args.agent, do_backdrop=args.backdrop, force=args.force,
            do_items=(not args.no_items),
            only_item=args.item)


if __name__ == "__main__":
    main()

# Art corrections / pose-sheet review feedback

(Reviewer: Claude; appended after inspecting each sheet. Prepended to
every subsequent generation prompt so lessons carry forward.)

## Attempt 1 — orchestrator (fox), 2026-04-19 — ACCEPTED with notes

Outcome: the 16-pose fox sheet came out strong and is fit to ship as the
main-Claude sprite. Below are adjustments to lock in for every future
character sheet so the cast stays uniform with this first one.

### Keep doing
- Bold, crisp outlines; same palette across all 16 panels.
- Clearly readable pose per panel (no ambiguity about which is which).
- Consistent face / eye proportions across panels.

### Fix for future character sheets (apply to dev-lead, mgmt-lead, …)
- **Uniform character scale per panel.** In the fox sheet, panels with
  desks or "walking" felt ~15% smaller than the standing portraits.
  Future sheets must draw every panel's character at the SAME pixel
  height (head-to-toe occupying ~80% of panel height when standing,
  ~55% when seated, measured from the panel top/bottom edges).
- **Strict panel gutters.** Each 256×256 panel should have a 4-pixel
  clear margin on all sides with nothing bleeding into neighbours.
  Panel (3,3) sleeping-at-desk bled slightly into (2,3) in attempt 1.
- **Identity accessory stays visible.** The golden crown on the fox
  got absorbed into the hair outline in row-4 panels. The accessory
  (crown / glasses / tie / badge) must remain readable in every single
  panel, including profile / walking views.
- **Side-view panel (pose 14 walking) uses the same body proportions**
  as front-view panels — just rotated. In attempt 1, the walking fox
  was noticeably smaller.
- **Seated panels show both hands on keyboard**; don't hide a hand
  behind the monitor. Attempt 1's Opus hustle was slightly ambiguous.
- **Sleeping-at-desk panel (pose 16)**: keep the desk + monitor inside
  the panel. In attempt 1 the desk edge extended outside the gutter.

### Format constraints (reiterate each run)
- 4×4 grid, 1024×1024 total, each panel exactly 256×256.
- Reading order left→right, then top→bottom.
- Solid magenta (#ff00ff) fills every non-character pixel including
  panel gutters (no black grid lines, no borders).
- **IMPORTANT**: Do NOT render any dark outline / black matte around
  the panels or around the 4×4 grid itself. Attempt-2 of the fox
  sheet added a 4–6 px black border per panel; that forced the CSS
  slicer to show dark frames around each character. The magenta
  background must extend ALL the way to the panel edges so that
  after chroma-keying, only the character remains on full transparent.
- No white halo around characters either — AA edges should go from
  character color straight to magenta, never via grey or beige.

## Attempt 3 review — notes for every subsequent sheet

### Outline quality reference (target)
- The **attempt-3 waiting/zzz panel** is the reference for clean
  outline quality: uniform 1-pixel dark-navy stroke around the whole
  silhouette, NO yellow / tan bloom or gradient halo, crown in solid
  gold with a single-pixel inner highlight. Every future panel must
  match this line weight and outline color exactly.

### Outline consistency (hard rule)
- Every character in every panel must use the SAME outline: uniform
  1-pixel dark-navy stroke around the silhouette. DO NOT vary
  outline weight panel-to-panel. Attempt 2 had panels where the
  outline thinned to 0 (facepalm, sleeping-at-desk) and panels where
  it thickened to 2 px with a yellowish tint (celebrate, pointing).
  Pick one outline weight and one outline color and keep it pixel-
  identical across all 16 panels.
- No colored outer glow / bloom around characters in any panel — the
  fur / hair silhouette ends at the 1 px dark outline, period.
- Shadows beneath characters must be a single opacity value across
  all panels (do not add ground shadows in some panels and not
  others).

### Opus hustle panel (pose 3) — composition fix
- Panel 3 ("Opus hustle") in attempt 3 ended up showing the BACK of
  the monitor with its code-screen spilling OUT behind the fox's
  head. Visually confusing. The hustle panel must show the character
  from the SAME camera angle as panel 2 (Sonnet work): monitor
  faces us showing code, fox is in front of monitor with both hands
  on keyboard. Only pose / expression intensity differs from panel
  2 — no camera angle change, no reveal of the monitor's back.

### Desk framing rule (for panels 1–12)
- The desk, chair, monitor, keyboard, coffee mug must be drawn
  PIXEL-identically in every one of panels 1–12. Treat them as a
  fixed background layer with only the character / held-object
  changing between panels.
- Never reframe / zoom differently across panels 1–12. The camera
  crop is identical for all 12 desk panels.

### Team-specific outfit rule (applies when generating the dev team)
- Orchestrator + mgmt-lead stay in formal business suits.
- dev-lead + every dev-* catalog agent wear developer-casual: hoodie
  or tee, headset or headphones, sticker-covered laptop vibe.
- eval + QA members wear hoodies / zip-ups with their tool (shield,
  magnifier, checkmark). Never formal suits.
- This reflects a real IT company dress code: one exec floor, one
  dev floor.

## Style polish — match the original orchestrator look (HARD rule)
- Render every character with **detailed, polished pixel art**, NOT
  flat / sticker / chibi style.
- Two-tone shading on every surface (highlight + shadow), with a
  subtle specular highlight on metal accessories (crown, badge,
  glasses, headset).
- Suit / hoodie fabric should show a hint of texture (pinstripe
  shadow on suits, ribbed cuff lines on hoodies).
- Outlines: uniform 1-pixel dark stroke, smooth and clean, not
  jagged or wobbly.
- Faces: eyes with a single specular highlight pixel, eyebrows
  visible and consistent across panels.
- Desk / monitor / chair rendered with subtle 3D depth (a darker
  inset under the desk surface, side-shadow on the monitor stand),
  not flat blocks of one color.
- Avoid the bobble-head chibi proportions. Body should be roughly
  3 heads tall when standing (panels 13–16), not 1.5 heads tall.

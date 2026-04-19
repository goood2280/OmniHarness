import { useEffect, useState } from 'react';
import { t } from './i18n';

// ProviderKeysPanel
// ─────────────────
// 플로팅 모달 카드. HUD 의 🔑 버튼으로 열린다.
// 4개 슬롯: anthropic / openai / gemini / bedrock(toggle).
// - GET /api/providers/keys   → masked "sk-…abcd" 또는 null; bedrock 은 bool.
// - POST /api/providers/keys  → 빈 문자열이면 삭제, 값 있으면 저장.
// Masked 값은 서버가 내려주므로 input placeholder 로만 표시.
// 사용자가 새로 입력한 평문은 저장 시 POST 후 다시 reload → placeholder.
export default function ProviderKeysPanel({ open, onClose, lang }) {
  const [state, setState] = useState(null);  // masked resp
  const [draft, setDraft] = useState({ anthropic: '', openai: '', gemini: '', bedrock: false });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = () => {
    fetch('/api/providers/keys')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setState(d);
        setDraft({ anthropic: '', openai: '', gemini: '', bedrock: !!d.bedrock });
      })
      .catch(() => {});
  };

  useEffect(() => { if (open) load(); }, [open]);

  if (!open) return null;

  const save = async () => {
    setSaving(true); setMsg(null);
    try {
      // Only send fields the user actually touched (non-empty draft for
      // text slots, or the bedrock toggle always). Empty-but-touched
      // clears the slot; we track "touched" via a simple heuristic:
      // if the draft string is non-empty we send it, else we don't.
      const payload = {};
      if (draft.anthropic !== '') payload.anthropic = draft.anthropic;
      if (draft.openai    !== '') payload.openai    = draft.openai;
      if (draft.gemini    !== '') payload.gemini    = draft.gemini;
      // Bedrock toggle: always send (it's a bool, no masked equivalent).
      payload.bedrock = !!draft.bedrock;
      const r = await fetch('/api/providers/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error('save failed');
      const d = await r.json();
      setState(d);
      setDraft({ anthropic: '', openai: '', gemini: '', bedrock: !!d.bedrock });
      setMsg({ ok: true, text: t('keys.saved', lang) });
    } catch (e) {
      setMsg({ ok: false, text: String(e) });
    } finally {
      setSaving(false);
    }
  };

  const clearSlot = async (slot) => {
    // Explicit clear — send empty string to drop both PROVIDER_KEYS and
    // os.environ. Server returns fresh masked view.
    setSaving(true); setMsg(null);
    try {
      const r = await fetch('/api/providers/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [slot]: slot === 'bedrock' ? false : '' }),
      });
      if (!r.ok) throw new Error('clear failed');
      const d = await r.json();
      setState(d);
      setDraft((x) => ({ ...x, [slot]: slot === 'bedrock' ? false : '' }));
      setMsg({ ok: true, text: t('keys.cleared', lang) });
    } catch (e) {
      setMsg({ ok: false, text: String(e) });
    } finally {
      setSaving(false);
    }
  };

  const slotRow = (slot, label) => {
    const masked = state && state[slot];        // "sk-…abcd" or null
    const locked = !!(state && state.env_locked && state.env_locked[slot]);
    return (
      <label className="keys-row" key={slot}>
        <span className="keys-label">
          {label}
          {masked && <em className="keys-masked" data-slot={slot}> · {masked}</em>}
          {locked && <em className="keys-locked"> · env</em>}
        </span>
        <div className="keys-input-wrap">
          <input
            type="password"
            autoComplete="off"
            value={draft[slot]}
            placeholder={masked ? t('keys.replace', lang) : t('keys.paste', lang)}
            onChange={(e) => setDraft((x) => ({ ...x, [slot]: e.target.value }))}
            data-testid={`provider-key-${slot}`}
          />
          {masked && (
            <button type="button" className="keys-clear" onClick={() => clearSlot(slot)}>
              ×
            </button>
          )}
        </div>
      </label>
    );
  };

  return (
    <div className="guide-overlay" onClick={onClose}>
      <div className="guide-card keys-card" onClick={(e) => e.stopPropagation()}>
        <button className="guide-close" onClick={onClose} aria-label="Close">×</button>
        <div className="guide-head">
          <span className="guide-tag">🔑 PROVIDER KEYS</span>
          <h2>{t('keys.title', lang)}</h2>
        </div>
        <div className="guide-body">
          <p className="muted" style={{ marginBottom: 8 }}>
            {t('keys.hint', lang)}
          </p>
          {slotRow('anthropic', 'ANTHROPIC_API_KEY')}
          {slotRow('openai',    'OPENAI_API_KEY')}
          {slotRow('gemini',    'GEMINI_API_KEY')}
          <label className="keys-row keys-row--toggle">
            <span className="keys-label">
              CLAUDE_CODE_USE_BEDROCK
              {state?.env_locked?.bedrock && <em className="keys-locked"> · env</em>}
            </span>
            <input
              type="checkbox"
              checked={!!draft.bedrock}
              onChange={(e) => setDraft((x) => ({ ...x, bedrock: e.target.checked }))}
              data-testid="provider-key-bedrock"
            />
          </label>
          {msg && (
            <div className={'keys-msg ' + (msg.ok ? 'ok' : 'err')}>{msg.text}</div>
          )}
        </div>
        <footer className="guide-foot keys-foot">
          <button
            type="button"
            className="btn-ghost"
            onClick={load}
            disabled={saving}
            data-testid="provider-keys-reload"
          >
            {t('keys.reload', lang)}
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={save}
            disabled={saving}
            data-testid="provider-keys-save"
          >
            {saving ? '…' : t('keys.save', lang)}
          </button>
        </footer>
      </div>
    </div>
  );
}

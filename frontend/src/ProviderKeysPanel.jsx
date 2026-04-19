import { useEffect, useState } from 'react';
import { t } from './i18n';

// ProviderKeysPanel
// ─────────────────
// 플로팅 모달. HUD 의 🔑 버튼으로 열린다.
// 슬롯:
//   • anthropic / openai / gemini — 일반 API 키
//   • bedrock — AWS Bedrock 토글 + 자격증명 3종 (access key / secret / region)
//     추가로 [Test connection] 버튼으로 실제 bedrock-runtime.converse 핑.
//
// Windows-friendly: UI 에 값을 넣고 저장하면 OmniHarness 프로세스가 이미
// PROVIDER_KEYS → os.environ 로 주입하므로 `setx` 나 .env 편집 없이도
// 서버가 재시작될 때까지 유지. 영구 저장이 필요하면 Windows 명령어 가이드
// (BedrockGuide) 를 따로 연다.
export default function ProviderKeysPanel({ open, onClose, lang }) {
  const [state, setState] = useState(null);
  const [draft, setDraft] = useState({
    anthropic: '', openai: '', gemini: '', elevenlabs: '', falai: '',
    bedrock: false,
    aws_access_key_id: '', aws_secret_access_key: '', aws_region: '',
  });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const load = () => {
    fetch('/api/providers/keys')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setState(d);
        setDraft({
          anthropic: '', openai: '', gemini: '',
          bedrock: !!d.bedrock,
          aws_access_key_id: '', aws_secret_access_key: '',
          aws_region: d.aws_region || '',
        });
      })
      .catch(() => {});
  };

  useEffect(() => { if (open) load(); }, [open]);

  if (!open) return null;

  const save = async () => {
    setSaving(true); setMsg(null);
    try {
      const payload = {};
      if (draft.anthropic  !== '') payload.anthropic  = draft.anthropic;
      if (draft.openai     !== '') payload.openai     = draft.openai;
      if (draft.gemini     !== '') payload.gemini     = draft.gemini;
      if (draft.elevenlabs !== '') payload.elevenlabs = draft.elevenlabs;
      if (draft.falai      !== '') payload.falai      = draft.falai;
      payload.bedrock = !!draft.bedrock;
      if (draft.aws_access_key_id     !== '') payload.aws_access_key_id     = draft.aws_access_key_id;
      if (draft.aws_secret_access_key !== '') payload.aws_secret_access_key = draft.aws_secret_access_key;
      if (draft.aws_region            !== '') payload.aws_region            = draft.aws_region;
      const r = await fetch('/api/providers/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error('save failed');
      const d = await r.json();
      setState(d);
      setDraft({
        anthropic: '', openai: '', gemini: '',
        bedrock: !!d.bedrock,
        aws_access_key_id: '', aws_secret_access_key: '',
        aws_region: d.aws_region || '',
      });
      setMsg({ ok: true, text: t('keys.saved', lang) });
    } catch (e) {
      setMsg({ ok: false, text: String(e) });
    } finally {
      setSaving(false);
    }
  };

  const clearSlot = async (slot) => {
    setSaving(true); setMsg(null);
    try {
      const empty = slot === 'bedrock' ? false : '';
      const r = await fetch('/api/providers/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [slot]: empty }),
      });
      if (!r.ok) throw new Error('clear failed');
      const d = await r.json();
      setState(d);
      setDraft((x) => ({ ...x, [slot]: empty }));
      setMsg({ ok: true, text: t('keys.cleared', lang) });
    } catch (e) {
      setMsg({ ok: false, text: String(e) });
    } finally {
      setSaving(false);
    }
  };

  const testBedrock = async () => {
    setTesting(true); setTestResult(null);
    try {
      const r = await fetch('/api/providers/bedrock/test', { method: 'POST' });
      const d = await r.json();
      setTestResult(d);
    } catch (e) {
      setTestResult({ ok: false, error: String(e), hint: '네트워크/서버 연결 확인.' });
    } finally {
      setTesting(false);
    }
  };

  const slotRow = (slot, label) => {
    const masked = state && state[slot];
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

          {slotRow('anthropic',  'ANTHROPIC_API_KEY')}
          {slotRow('openai',     'OPENAI_API_KEY')}
          {slotRow('gemini',     'GEMINI_API_KEY')}
          {slotRow('elevenlabs', 'ELEVENLABS_API_KEY')}
          {slotRow('falai',      'FAL_KEY')}

          {/* ── Bedrock (AWS) — easy-connect 섹션 ─────────────────── */}
          <div className="keys-bedrock-section" style={{
            marginTop: 16, paddingTop: 12, borderTop: '1px solid #333',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <strong style={{ fontSize: 12, letterSpacing: '0.04em' }}>
                {lang === 'ko' ? '🟠 AMAZON BEDROCK (AWS)' : '🟠 AMAZON BEDROCK (AWS)'}
              </strong>
              <label className="keys-row keys-row--toggle" style={{ margin: 0 }}>
                <span className="keys-label" style={{ marginRight: 8 }}>
                  {lang === 'ko' ? 'Bedrock 사용' : 'Use Bedrock'}
                  {state?.env_locked?.bedrock && <em className="keys-locked"> · env</em>}
                </span>
                <input
                  type="checkbox"
                  checked={!!draft.bedrock}
                  onChange={(e) => setDraft((x) => ({ ...x, bedrock: e.target.checked }))}
                  data-testid="provider-key-bedrock"
                />
              </label>
            </div>

            {slotRow('aws_access_key_id',     'AWS_ACCESS_KEY_ID')}
            {slotRow('aws_secret_access_key', 'AWS_SECRET_ACCESS_KEY')}

            {/* Region 은 비밀이 아니므로 평문 노출 */}
            <label className="keys-row" key="aws_region">
              <span className="keys-label">
                AWS_REGION
                {state?.env_locked?.aws_region && <em className="keys-locked"> · env</em>}
              </span>
              <div className="keys-input-wrap">
                <input
                  type="text"
                  autoComplete="off"
                  value={draft.aws_region}
                  placeholder={lang === 'ko' ? '예: us-east-1, us-west-2, ap-northeast-2' : 'e.g. us-east-1, us-west-2, ap-northeast-2'}
                  onChange={(e) => setDraft((x) => ({ ...x, aws_region: e.target.value }))}
                  data-testid="provider-key-aws_region"
                />
              </div>
            </label>

            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8 }}>
              <button
                type="button"
                className="btn-ghost"
                onClick={testBedrock}
                disabled={testing || saving}
                data-testid="provider-keys-test-bedrock"
              >
                {testing
                  ? (lang === 'ko' ? '테스트 중…' : 'Testing…')
                  : (lang === 'ko' ? '🔌 연결 테스트' : '🔌 Test connection')}
              </button>
              {testResult && (
                <span
                  className={'keys-msg ' + (testResult.ok ? 'ok' : 'err')}
                  style={{ flex: 1, fontSize: 11, lineHeight: 1.4 }}
                >
                  {testResult.ok
                    ? (lang === 'ko'
                        ? `✅ 연결 성공 · ${testResult.latency_ms}ms · ${testResult.model}`
                        : `✅ Connected · ${testResult.latency_ms}ms · ${testResult.model}`)
                    : (
                      <>
                        ❌ {testResult.error}
                        {testResult.hint && <div style={{ opacity: 0.75, marginTop: 2 }}>💡 {testResult.hint}</div>}
                      </>
                    )}
                </span>
              )}
            </div>

            <p className="muted" style={{ fontSize: 10, marginTop: 8, lineHeight: 1.5 }}>
              {lang === 'ko'
                ? '💡 Windows 에서는 여기 입력만 하면 OmniHarness 프로세스가 살아있는 동안 유지됩니다. 시스템 전체 영구 저장은 HUD ☁ GUIDE 의 Bedrock 섹션 명령어 참고.'
                : '💡 On Windows, just entering values here keeps them for the life of the OmniHarness process. For system-wide persistence see the Bedrock section in the HUD ☁ GUIDE.'}
            </p>
          </div>

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

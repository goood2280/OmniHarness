// ChatDock.jsx — bottom-right chat widget that talks to /api/chat.
// The endpoint routes to orchestrator (active project or general),
// provider auto-detected: Bedrock > Anthropic > stub.

import { useEffect, useRef, useState } from 'react';
import { t } from './i18n';

export default function ChatDock({ lang, mode, projectSlug }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [provider, setProvider] = useState('stub');
  const [history, setHistory] = useState([]); // {role, content}[]
  const listRef = useRef(null);

  useEffect(() => {
    fetch('/api/chat/provider')
      .then((r) => r.json())
      .then((d) => setProvider(d.provider || 'stub'))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (open && listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [history, open]);

  const send = async () => {
    const msg = input.trim();
    if (!msg) return;
    setBusy(true);
    const nextHistory = [...history, { role: 'user', content: msg }];
    setHistory(nextHistory);
    setInput('');
    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msg,
          project_slug: mode === 'custom' ? projectSlug : null,
          history,
        }),
      });
      if (r.ok) {
        const d = await r.json();
        setHistory([...nextHistory, { role: 'assistant', content: d.reply, provider: d.provider }]);
      } else {
        setHistory([...nextHistory, { role: 'assistant', content: `[오류 ${r.status}]`, provider: 'error' }]);
      }
    } catch (e) {
      setHistory([...nextHistory, { role: 'assistant', content: `[네트워크 오류: ${e}]`, provider: 'error' }]);
    } finally {
      setBusy(false);
    }
  };

  const providerLabel = {
    anthropic: '🟢 Anthropic',
    bedrock:   '🟠 Bedrock',
    stub:      '⚪ STUB (API 미연결)',
  }[provider] || provider;

  if (!open) {
    return (
      <button className="chatdock-fab" onClick={() => setOpen(true)} title={t('chat.open', lang)}>
        💬 {t('chat.open', lang)}
      </button>
    );
  }

  return (
    <div className="chatdock">
      <div className="chatdock-head">
        <div>
          <b>{t('chat.title', lang)}</b>
          <span className="chatdock-provider">{providerLabel}</span>
        </div>
        <button className="chatdock-close" onClick={() => setOpen(false)}>×</button>
      </div>
      <div className="chatdock-list" ref={listRef}>
        {!history.length && (
          <div className="chatdock-empty">{t('chat.empty', lang)}</div>
        )}
        {history.map((h, i) => (
          <div key={i} className={`chatdock-msg chatdock-${h.role}`}>
            <div className="chatdock-msg-role">
              {h.role === 'user' ? '👤 You' : '🎯 orchestrator'}
              {h.provider && <span className="chatdock-msg-provider">· {h.provider}</span>}
            </div>
            <div className="chatdock-msg-body">{h.content}</div>
          </div>
        ))}
      </div>
      <div className="chatdock-input">
        <textarea
          rows={2}
          placeholder={t('chat.placeholder', lang)}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) send();
          }}
        />
        <button className="btn-primary" disabled={busy || !input.trim()} onClick={send}>
          {busy ? t('chat.sending', lang) : t('chat.send', lang)}
        </button>
      </div>
      {provider === 'stub' && (
        <div className="chatdock-warning">
          {t('chat.stub_warning', lang)}
        </div>
      )}
    </div>
  );
}

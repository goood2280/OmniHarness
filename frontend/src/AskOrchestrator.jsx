// AskOrchestrator.jsx — General-mode tab equivalent of Custom-mode
// Requirements: a single in-page entry point for sending a natural-
// language question to the orchestrator. Calls /api/chat directly so
// the same Bedrock / Anthropic / stub plumbing applies.

import { useEffect, useRef, useState } from 'react';
import { t } from './i18n';

export default function AskOrchestrator({ lang }) {
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [provider, setProvider] = useState('stub');
  const [history, setHistory] = useState([]);
  const listRef = useRef(null);

  useEffect(() => {
    fetch('/api/chat/provider')
      .then((r) => r.json())
      .then((d) => setProvider(d.provider || 'stub'))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [history]);

  const send = async () => {
    const msg = input.trim();
    if (!msg) return;
    setBusy(true);
    const next = [...history, { role: 'user', content: msg }];
    setHistory(next);
    setInput('');
    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, project_slug: null, history }),
      });
      if (r.ok) {
        const d = await r.json();
        setHistory([...next, { role: 'assistant', content: d.reply, provider: d.provider }]);
      } else {
        setHistory([...next, { role: 'assistant', content: `[${lang === 'ko' ? '오류' : 'error'} ${r.status}]`, provider: 'error' }]);
      }
    } catch (e) {
      setHistory([...next, { role: 'assistant', content: `[${e}]`, provider: 'error' }]);
    } finally {
      setBusy(false);
    }
  };

  const providerLabel = {
    anthropic: '🟢 Anthropic',
    bedrock:   '🟠 Bedrock',
    stub:      lang === 'ko' ? '⚪ STUB (API 미연결)' : '⚪ STUB (no API)',
  }[provider] || provider;

  return (
    <div className="ask-tab">
      <div className="ask-head">
        <h3 className="ask-title">
          {lang === 'ko' ? '🎯 오케스트레이터에게 질문' : '🎯 Ask Orchestrator'}
        </h3>
        <span className="ask-provider">{providerLabel}</span>
      </div>
      <p className="ask-hint">
        {lang === 'ko'
          ? '자연어로 무엇이든 물어보세요. 오케스트레이터가 답변하거나 적절한 서브에이전트를 호출합니다.'
          : 'Ask anything in natural language. The orchestrator answers or delegates to a subagent.'}
      </p>

      <div className="ask-list" ref={listRef}>
        {!history.length && (
          <div className="ask-empty">
            {lang === 'ko' ? '아직 대화가 없습니다.' : 'No conversation yet.'}
          </div>
        )}
        {history.map((h, i) => (
          <div key={i} className={`ask-msg ask-${h.role}`}>
            <div className="ask-msg-role">
              {h.role === 'user'
                ? (lang === 'ko' ? '👤 나' : '👤 You')
                : '🎯 orchestrator'}
              {h.provider && <span className="ask-msg-provider">· {h.provider}</span>}
            </div>
            <div className="ask-msg-body">{h.content}</div>
          </div>
        ))}
      </div>

      <div className="ask-input">
        <textarea
          rows={3}
          placeholder={lang === 'ko'
            ? '질문을 입력하세요 (Ctrl/⌘+Enter 전송)'
            : 'Type a question (Ctrl/⌘+Enter to send)'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) send();
          }}
        />
        <button className="btn-primary" disabled={busy || !input.trim()} onClick={send}>
          {busy
            ? (lang === 'ko' ? '전송 중…' : 'sending…')
            : (lang === 'ko' ? '전송' : 'Send')}
        </button>
      </div>

      {provider === 'stub' && (
        <div className="ask-warning">
          {lang === 'ko'
            ? '※ LLM API 가 연결되지 않아 스텁 응답입니다. HUD ☁ 가이드 → Bedrock 또는 Anthropic 설정을 참고하세요.'
            : '※ No LLM API configured — replies are stubbed. See HUD ☁ Guide for Bedrock/Anthropic setup.'}
        </div>
      )}
    </div>
  );
}

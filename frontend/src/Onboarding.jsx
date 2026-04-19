// Onboarding.jsx — 3-step wizard that replaces the bare Mission modal.
// Step 1: company / industry / philosophy / goal.
// Step 2: orchestrator proposes dev+domain team; user tweaks the roster.
// Step 3: confirm — team locks in, office scene renders only those agents.
//
// Closing the wizard is only allowed after team_confirmed=true.

import { useEffect, useState } from 'react';
import { t } from './i18n';

const BASE_TEAM = [
  { name: 'orchestrator', team: 'top', note_ko: '총괄. 사용자와 직접 대화하고 구현은 dev-lead, 검증은 리뷰어에게 위임.',
                                        note_en: 'HQ. Talks to the user directly; delegates implementation to dev-lead and review to the reviewers.' },
  { name: 'dev-lead',     team: 'dev', note_ko: '개발 실무. 피처 세분화 없이 풀스택 단일 에이전트.',
                                        note_en: 'Dev. Single full-stack worker — no per-feature fan-out.' },
];

export default function Onboarding({ mission, onSave, lang, onClose }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(mission || { company: '', industry: '', philosophy: '', goal: '' });
  const [catalog, setCatalog] = useState({ dev: [], domain: [] });
  const [devSel, setDevSel] = useState([]);
  const [domainSel, setDomainSel] = useState([]);
  const [proposal, setProposal] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showFullCatalog, setShowFullCatalog] = useState(false);

  useEffect(() => {
    fetch('/api/mission/catalog').then((r) => r.json()).then(setCatalog).catch(() => {});
  }, []);

  useEffect(() => {
    if (!mission) return;
    setForm({
      company: mission.company || '',
      industry: mission.industry || '',
      philosophy: mission.philosophy || '',
      goal: mission.goal || '',
    });
    if (mission.team_confirmed) {
      onSave?.(mission);
      return;
    }
    // If mission is already filled but team isn't confirmed, skip to step 2
    // and kick off a fresh proposal so the user just picks from the roster.
    // We intentionally run this ONCE on mount — the parent passes a fresh
    // {...mission} object every render, so depending on `mission` here would
    // re-fire the proposal and bounce the user back to step 2 every time
    // they tried to advance to step 3. The `[]` dep keeps initial setup
    // tied to component mount only.
    if (!mission.placeholder && mission.company && mission.industry && mission.goal) {
      fetch('/api/mission/propose_team', { method: 'POST' })
        .then((r) => (r.ok ? r.json() : null))
        .then((p) => {
          if (!p) return;
          setProposal(p);
          setDevSel(p.proposed_dev_agents || []);
          setDomainSel(p.proposed_domain_agents || []);
          setStep(2);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const valid1 = form.company?.trim() && form.industry?.trim() && form.goal?.trim();

  const submitMission = async () => {
    if (!valid1) return;
    setBusy(true);
    try {
      const r = await fetch('/api/mission', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company: form.company.trim(),
          industry: form.industry.trim(),
          philosophy: (form.philosophy || '').trim(),
          goal: form.goal.trim(),
        }),
      });
      if (!r.ok) return;
      // Ask orchestrator to propose a team based on the mission
      const p = await fetch('/api/mission/propose_team', { method: 'POST' });
      if (p.ok) {
        const proposed = await p.json();
        setProposal(proposed);
        setDevSel(proposed.proposed_dev_agents || []);
        setDomainSel(proposed.proposed_domain_agents || []);
        setStep(2);
      }
    } finally {
      setBusy(false);
    }
  };

  const toggle = (arr, set, name) => {
    set(arr.includes(name) ? arr.filter((x) => x !== name) : [...arr, name]);
  };

  const confirmTeam = async () => {
    setBusy(true);
    try {
      const r = await fetch('/api/mission/confirm_team', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dev_agents: devSel, domain_agents: domainSel }),
      });
      if (r.ok) {
        const saved = await r.json();
        onSave?.(saved);
      }
    } finally {
      setBusy(false);
    }
  };

  const L = (key) => t(key, lang);

  return (
    <div className="wizard-overlay">
      <div className="wizard-card">
        {onClose && (
          <button
            className="wizard-close"
            onClick={onClose}
            aria-label="Close"
            title={lang === 'ko' ? '닫기' : 'Close'}
          >
            ×
          </button>
        )}
        <div className="wizard-steps">
          <StepDot n={1} active={step === 1} done={step > 1} label={L('wiz.step1')} />
          <div className="wizard-step-line" />
          <StepDot n={2} active={step === 2} done={step > 2} label={L('wiz.step2')} />
          <div className="wizard-step-line" />
          <StepDot n={3} active={step === 3} done={false} label={L('wiz.step3')} />
        </div>

        {step === 1 && (
          <>
            <h2>{L('wiz.title1')}</h2>
            <p className="wizard-hint">{L('wiz.hint1')}</p>

            <label>
              <span>{L('mission.company')} <em>*</em></span>
              <input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} placeholder={L('mission.company_ph')} />
            </label>
            <label>
              <span>{L('mission.industry')} <em>*</em></span>
              <input value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} placeholder={L('mission.industry_ph')} />
            </label>
            <label>
              <span>{L('mission.philosophy')}</span>
              <input value={form.philosophy} onChange={(e) => setForm({ ...form, philosophy: e.target.value })} placeholder={L('mission.philosophy_ph')} />
            </label>
            <label>
              <span>{L('mission.goal')} <em>*</em></span>
              <input value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} placeholder={L('mission.goal_ph')} />
            </label>

            <div className="wizard-actions">
              <button className="btn-primary" disabled={!valid1 || busy} onClick={submitMission}>
                {busy ? L('wiz.thinking') : L('wiz.next')}
              </button>
            </div>
          </>
        )}

        {step === 2 && proposal && (
          <>
            <h2>{L('wiz.title2')}</h2>
            <p className="wizard-hint">{L('wiz.hint2').replace('{company}', form.company)}</p>

            {proposal.proposal_source === 'heuristic' && (
              <div className="wizard-warning">
                <span className="wizard-warning-tag">⚠️</span>
                <span>
                  {lang === 'ko'
                    ? 'LLM API 가 연결되지 않아 키워드 휴리스틱으로 제안된 팀입니다. 프로젝트에 딱 맞는 팀을 받으려면 HUD 의 ☁ 가이드에서 Anthropic / Bedrock 키를 설정하고 다시 시도하세요.'
                    : 'No LLM API connected — this proposal came from keyword heuristics. For a project-specific team, wire up Anthropic or Bedrock via the ☁ GUIDE in the HUD and retry.'}
                </span>
              </div>
            )}
            {proposal.proposal_source && proposal.proposal_source !== 'heuristic' && (
              <div className="wizard-provider">
                {lang === 'ko'
                  ? `🧠 오케스트레이터(${proposal.proposal_source}) 가 이 프로젝트에 맞춰 설계한 팀`
                  : `🧠 Team designed by the orchestrator (${proposal.proposal_source}) for this project`}
              </div>
            )}

            {proposal.proposal_reason && (
              <div className="wizard-reason">
                <span className="wizard-reason-tag">💡 {L('wiz.reason')}</span>
                <span>{proposal.proposal_reason}</span>
              </div>
            )}

            {/* Base team (non-editable) */}
            <h3 className="wizard-section">{L('wiz.base_label')}</h3>
            <div className="wizard-list wizard-list-base">
              {BASE_TEAM.map((a) => (
                <div key={a.name} className="wizard-chip wizard-chip-base">
                  <span className="wizard-chip-name">{t(`agent.${a.name}`, lang) || a.name}</span>
                  <span className="wizard-chip-note">{lang === 'ko' ? a.note_ko : a.note_en}</span>
                </div>
              ))}
              <div className="wizard-chip wizard-chip-base">
                <span className="wizard-chip-name">+ 6 · {L('wiz.eval_team')}</span>
                <span className="wizard-chip-note">{lang === 'ko' ? 'UX · 검증 · 유저/관리자 테스터 · 보안 · 도메인 리서치 (on-demand)' : 'UX · verify · user/admin tester · security · domain research (on-demand)'}</span>
              </div>
              <div className="wizard-chip wizard-chip-base">
                <span className="wizard-chip-name">📚 knowledge × 4</span>
                <span className="wizard-chip-note">{lang === 'ko' ? '공정 영역 · 인과 방향 · DVC 방향 · 어댑터 매핑 (에이전트가 아닌 참조 문서)' : 'process area · causal · DVC · adapter — reference docs, not agents'}</span>
              </div>
            </div>

            {/* Dev catalog — READ-ONLY. The user modifies the team via
                natural language in Claude Code (or via the chat-dock in
                Bedrock mode); this panel just shows what the orchestrator
                currently has staffed. */}
            <h3 className="wizard-section">{L('wiz.dev_label')}</h3>
            <div className="wizard-list">
              {catalog.dev
                .filter((a) => devSel.includes(a.name))
                .map((a) => (
                  <div key={a.name} className="wizard-chip wizard-chip-base wizard-chip-readonly">
                    <span className="wizard-chip-name">{t(`agent.${a.name}`, lang) || a.name}</span>
                    <span className="wizard-chip-tick">✓</span>
                  </div>
                ))}
              {(proposal.proposed_custom_dev_specs || []).map((s) => (
                <div key={s.name} className="wizard-chip wizard-chip-base wizard-chip-readonly wizard-chip-custom">
                  <span className="wizard-chip-name">{s.name}</span>
                  {s.description && <span className="wizard-chip-note">{s.description}</span>}
                  <span className="wizard-chip-tick">✨</span>
                </div>
              ))}
            </div>

            {/* Domain catalog — same read-only treatment */}
            {(domainSel.length > 0 || (proposal.proposed_custom_domain_specs || []).length > 0) && (
              <>
                <h3 className="wizard-section">{L('wiz.domain_label')}</h3>
                <div className="wizard-list">
                  {catalog.domain
                    .filter((a) => domainSel.includes(a.name))
                    .map((a) => (
                      <div key={a.name} className="wizard-chip wizard-chip-base wizard-chip-readonly">
                        <span className="wizard-chip-name">{t(`agent.${a.name}`, lang) || a.name}</span>
                        <span className="wizard-chip-tick">✓</span>
                      </div>
                    ))}
                  {(proposal.proposed_custom_domain_specs || []).map((s) => (
                    <div key={s.name} className="wizard-chip wizard-chip-base wizard-chip-readonly wizard-chip-custom">
                      <span className="wizard-chip-name">{s.name}</span>
                      {s.description && <span className="wizard-chip-note">{s.description}</span>}
                      <span className="wizard-chip-tick">✨</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            <div className="wizard-readonly-note">
              {lang === 'ko'
                ? '※ 이 구성은 자동 제안된 결과예요. 수정이 필요하면 Claude Code에 자연어로 요청하거나, Bedrock 연결 시 우하단 질문하기에서 오케스트레이터에게 부탁하세요.'
                : '※ This roster is auto-proposed. To change it, ask Claude Code in natural language, or (when Bedrock is connected) send a request via the bottom-right Ask button.'}
            </div>

            <div className="wizard-actions">
              <button className="btn-ghost" onClick={() => setStep(1)}>{L('wiz.back')}</button>
              <button className="btn-primary" onClick={() => setStep(3)}>{L('wiz.next')}</button>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <h2>{L('wiz.title3')}</h2>
            <p className="wizard-hint">{L('wiz.hint3').replace('{company}', form.company)}</p>

            <div className="wizard-summary">
              <div className="wizard-summary-row">
                <span className="wizard-summary-key">{L('mission.company')}</span>
                <span className="wizard-summary-val">{form.company}</span>
              </div>
              <div className="wizard-summary-row">
                <span className="wizard-summary-key">{L('mission.industry')}</span>
                <span className="wizard-summary-val">{form.industry}</span>
              </div>
              {form.philosophy && (
                <div className="wizard-summary-row">
                  <span className="wizard-summary-key">{L('mission.philosophy')}</span>
                  <span className="wizard-summary-val">{form.philosophy}</span>
                </div>
              )}
              <div className="wizard-summary-row">
                <span className="wizard-summary-key">{L('mission.goal')}</span>
                <span className="wizard-summary-val">{form.goal}</span>
              </div>
              <div className="wizard-summary-row">
                <span className="wizard-summary-key">{L('wiz.roster_total')}</span>
                <span className="wizard-summary-val">
                  {BASE_TEAM.length + 6 /* reviewers */ + devSel.length + domainSel.length}
                  <span className="wizard-summary-sub"> ({L('wiz.base_count')} {BASE_TEAM.length + 6} + dev {devSel.length} + domain {domainSel.length})</span>
                </span>
              </div>
            </div>

            <div className="wizard-summary-teams">
              <div>
                <strong>{L('wiz.dev_label')}:</strong>{' '}
                {devSel.length ? devSel.map((n) => t(`agent.${n}`, lang) || n).join(', ') : <em>{L('wiz.none')}</em>}
              </div>
              <div>
                <strong>{L('wiz.domain_label')}:</strong>{' '}
                {domainSel.length ? domainSel.map((n) => t(`agent.${n}`, lang) || n).join(', ') : <em>{L('wiz.none')}</em>}
              </div>
            </div>

            <div className="wizard-actions">
              <button className="btn-ghost" onClick={() => setStep(2)}>{L('wiz.back')}</button>
              <button className="btn-primary" disabled={busy} onClick={confirmTeam}>
                {busy ? L('wiz.saving') : L('wiz.confirm')}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StepDot({ n, active, done, label }) {
  return (
    <div className={`wizard-step ${active ? 'active' : ''} ${done ? 'done' : ''}`}>
      <div className="wizard-step-dot">{done ? '✓' : n}</div>
      <div className="wizard-step-label">{label}</div>
    </div>
  );
}

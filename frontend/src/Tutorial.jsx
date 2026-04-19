import { useEffect, useState } from 'react';

const TUTORIAL_KEY = 'omni.tutorial_seen_v1';
const LANG_CHOSEN_KEY = 'omni.lang_chosen_v1';

// Per-tab blurb copy. Kept short — the tutorial is a first-impression
// tour, not documentation. Users learn the rest by doing.
function tabSteps(lang) {
  const ko = [
    { icon: '🏢', title: '조직도', body: '지금 뛰고 있는 팀 구성. 캐릭터를 클릭하면 오른쪽 사이드에 역할과 설정 파일이 뜹니다. 책상 아래 빨간 바는 최근 활동량.' },
    { icon: '📜', title: '활동',   body: 'Claude Code 가 방금 무엇을 읽고 쓰고 실행했는지 실시간 로그. 문제 추적 시 여기부터 보면 됩니다.' },
    { icon: '❓', title: '질문',   body: '에이전트가 모호한 결정을 만나면 오케스트레이터가 사용자 언어로 풀어서 올립니다. 답변도 오케스트레이터가 다시 에이전트 언어로 변환해 전달합니다.' },
    { icon: '🎯', title: '요구사항', body: '이 프로젝트에 필요한 것을 자연어로 적으면 오케스트레이터가 적절한 팀에 할당합니다. 변경·수정도 여기에 올리면 됩니다.' },
    { icon: '🧾', title: '백로그',   body: '리드들이 승인한 예정 작업 목록. 위에서 아래로 우선순위 순.' },
    { icon: '🌱', title: '감사',    body: '감사원이 조직과 진행 상태를 점검하고 새 에이전트·기능·리팩터 제안을 올립니다. 수락하면 실제 팀 구성에 반영됩니다.' },
    { icon: '📚', title: '누적 지식', body: '에이전트들이 작업 중 배운 인사이트가 쌓이는 공용 메모장. 새로 들어오는 에이전트도 이걸 읽고 시작합니다.' },
    { icon: '📊', title: '보고서',   body: '의미있는 변경이 쌓이면 오케스트레이터가 자동으로 평어체 요약 보고서를 발행합니다. 요구사항을 올리면 초안 리포트도 여기에 먼저 뜹니다.' },
  ];
  const en = [
    { icon: '🏢', title: 'Org',          body: 'Your live team. Click any character — their role and config file slide in on the right. The bar under each desk shows recent activity.' },
    { icon: '📜', title: 'Activity',     body: 'Real-time log of what Claude Code just read, wrote, or ran. Start here when debugging.' },
    { icon: '❓', title: 'Questions',    body: 'When an agent hits an ambiguous decision, the orchestrator rewrites it in plain language. Your answer gets translated back into a structured instruction for the agent.' },
    { icon: '🎯', title: 'Requirements', body: 'Describe what this project needs in plain language. The orchestrator assigns to the right team. Post changes and tweaks here too.' },
    { icon: '🧾', title: 'Backlog',      body: 'Upcoming work approved by the leads. Priority top → bottom.' },
    { icon: '🌱', title: 'Audit',        body: 'The auditor checks whether the team and project still match the mission and files proposals (new/retire agents, features, refactors). Accepting actually mutates the roster.' },
    { icon: '📚', title: 'Knowledge',    body: "Shared notepad of insights agents learned while working. New agents read this before starting." },
    { icon: '📊', title: 'Reports',      body: 'When meaningful changes pile up, the orchestrator publishes a plain-language summary here. New requirements also land a draft report first.' },
  ];
  return lang === 'ko' ? ko : en;
}

function otherCopy(lang) {
  return lang === 'ko' ? {
    welcome: '환영합니다',
    intro: 'OmniHarness 사무실에 오신 걸 환영해요. 각 탭이 어떤 역할을 하는지 10초씩만 읽고 시작하면 훨씬 편합니다.',
    next: '다음 →',
    prev: '← 이전',
    skip: '건너뛰기',
    done: '시작하기',
    step: '단계',
    langTitle: '언어를 선택하세요',
    langBody: '나중에 상단 HUD 에서 언제든 바꿀 수 있습니다.',
  } : {
    welcome: 'Welcome',
    intro: "Welcome to the OmniHarness office. Ten seconds on each tab makes the rest click — here's the guided tour.",
    next: 'Next →',
    prev: '← Back',
    skip: 'Skip',
    done: 'Start',
    step: 'Step',
    langTitle: 'Pick your language',
    langBody: 'You can switch anytime from the HUD at the top.',
  };
}

export default function Tutorial({ lang, setLang, onDone }) {
  // Start hidden until we confirm the user hasn't seen the tour — avoids
  // a flash of the welcome card for returning users.
  const [visible, setVisible] = useState(false);
  // Phase: 'lang' → 'welcome' → 'step'
  const [phase, setPhase] = useState('lang');
  const [idx, setIdx] = useState(0);
  const steps = tabSteps(lang);
  const L = otherCopy(lang);

  useEffect(() => {
    try {
      if (localStorage.getItem(TUTORIAL_KEY)) {
        onDone?.();
        return;
      }
      const chosen = localStorage.getItem(LANG_CHOSEN_KEY);
      setPhase(chosen ? 'welcome' : 'lang');
      setVisible(true);
    } catch {
      onDone?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const finish = () => {
    try {
      localStorage.setItem(TUTORIAL_KEY, '1');
      localStorage.setItem(LANG_CHOSEN_KEY, '1');
    } catch { /* ignore */ }
    setVisible(false);
    onDone?.();
  };

  const chooseLang = (code) => {
    try { localStorage.setItem(LANG_CHOSEN_KEY, '1'); } catch { /* ignore */ }
    setLang?.(code);
    setPhase('welcome');
  };

  if (!visible) return null;

  const isLang    = phase === 'lang';
  const isWelcome = phase === 'welcome';
  const isStep    = phase === 'step';
  const step = isStep ? steps[idx] : null;
  const total = steps.length;

  return (
    <div className="tutorial-overlay" onClick={isLang ? undefined : finish}>
      <div className="tutorial-card" onClick={(e) => e.stopPropagation()}>
        {!isLang && (
          <button className="tutorial-skip" onClick={finish}>{L.skip} ×</button>
        )}

        {isLang && (
          <>
            <div className="tutorial-badge">🌐 Language / 언어</div>
            <h2 className="tutorial-title">{L.langTitle}</h2>
            <p className="tutorial-body">{L.langBody}</p>
            <div className="tutorial-lang-grid">
              <button
                className={`tutorial-lang-btn${lang === 'ko' ? ' active' : ''}`}
                onClick={() => chooseLang('ko')}
              >
                <div className="tutorial-lang-flag">🇰🇷</div>
                <div className="tutorial-lang-name">한국어</div>
                <div className="tutorial-lang-sub">Korean</div>
              </button>
              <button
                className={`tutorial-lang-btn${lang === 'en' ? ' active' : ''}`}
                onClick={() => chooseLang('en')}
              >
                <div className="tutorial-lang-flag">🇺🇸</div>
                <div className="tutorial-lang-name">English</div>
                <div className="tutorial-lang-sub">English</div>
              </button>
            </div>
          </>
        )}

        {isWelcome && (
          <>
            <div className="tutorial-badge">👋 {L.welcome}</div>
            <h2 className="tutorial-title">OmniHarness</h2>
            <p className="tutorial-body">{L.intro}</p>
          </>
        )}

        {isStep && (
          <>
            <div className="tutorial-badge">{L.step} {idx + 1} / {total}</div>
            <h2 className="tutorial-title">{step.icon} {step.title}</h2>
            <p className="tutorial-body">{step.body}</p>
            <div className="tutorial-progress">
              {steps.map((_, i) => (
                <span
                  key={i}
                  className={`tutorial-dot${i === idx ? ' active' : ''}${i < idx ? ' done' : ''}`}
                />
              ))}
            </div>
          </>
        )}

        {!isLang && (
          <div className="tutorial-actions">
            {isStep && idx > 0 && (
              <button className="tutorial-btn tutorial-btn--ghost" onClick={() => setIdx(idx - 1)}>
                {L.prev}
              </button>
            )}
            {isWelcome && (
              <button className="tutorial-btn" onClick={() => { setPhase('step'); setIdx(0); }}>
                {L.next}
              </button>
            )}
            {isStep && idx < total - 1 && (
              <button className="tutorial-btn" onClick={() => setIdx(idx + 1)}>
                {L.next}
              </button>
            )}
            {isStep && idx === total - 1 && (
              <button className="tutorial-btn tutorial-btn--primary" onClick={finish}>
                {L.done}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

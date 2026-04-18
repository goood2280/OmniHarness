import { useEffect, useState } from 'react';

export default function MissionBanner({ mission, onSave }) {
  const needsInit = !mission || mission.placeholder;
  const [editing, setEditing] = useState(needsInit);
  const [form, setForm] = useState(mission || { industry: '', philosophy: '', goal: '' });

  useEffect(() => {
    if (mission) setForm(mission);
    if (mission && mission.placeholder) setEditing(true);
  }, [mission]);

  const submit = async () => {
    const body = {
      industry: form.industry.trim(),
      philosophy: form.philosophy.trim(),
      goal: form.goal.trim(),
    };
    if (!body.industry || !body.goal) return; // require at least industry + goal
    const r = await fetch('/api/mission', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (r.ok) {
      const saved = await r.json();
      onSave(saved);
      setEditing(false);
    }
  };

  if (needsInit || editing) {
    return (
      <div className={needsInit ? 'mission-overlay' : 'mission-edit'}>
        <div className="mission-card">
          <h2>사훈 (Mission) 설정</h2>
          <p className="mission-hint">
            이 사훈은 <b>모든 에이전트의 공통 목표</b>가 됩니다. 업종 / 철학 / 목표를
            적어주세요. 이후 상단 배너에서 언제든 수정 가능합니다.
          </p>
          <label>
            <span>업종 <em>*</em></span>
            <input
              value={form.industry}
              onChange={(e) => setForm({ ...form, industry: e.target.value })}
              placeholder="예: 반도체 Fab IT / 수율 분석 도구"
            />
          </label>
          <label>
            <span>철학</span>
            <input
              value={form.philosophy}
              onChange={(e) => setForm({ ...form, philosophy: e.target.value })}
              placeholder="예: 현장 엔지니어가 바로 쓸 수 있게, 복잡도는 숨기고 결정은 빠르게"
            />
          </label>
          <label>
            <span>목표 <em>*</em></span>
            <input
              value={form.goal}
              onChange={(e) => setForm({ ...form, goal: e.target.value })}
              placeholder="예: 3개월 내 SPC/Tracker 통합 + 대시보드 자동 생성"
            />
          </label>
          <div className="mission-actions">
            {!needsInit && (
              <button className="btn-ghost" onClick={() => setEditing(false)}>취소</button>
            )}
            <button className="btn-primary" onClick={submit}>저장</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mission-banner" onClick={() => setEditing(true)} title="클릭해서 수정">
      <div className="mission-label">사훈</div>
      <div className="mission-content">
        <span className="mission-chip">{mission.industry || '—'}</span>
        {mission.philosophy && <span className="mission-sep">·</span>}
        {mission.philosophy && <span className="mission-philo">{mission.philosophy}</span>}
        <span className="mission-sep">→</span>
        <span className="mission-goal">{mission.goal || '—'}</span>
      </div>
      <button className="mission-edit-btn" onClick={(e) => { e.stopPropagation(); setEditing(true); }}>
        ✎
      </button>
    </div>
  );
}

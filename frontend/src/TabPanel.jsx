import { useState } from 'react';
import ActivityLog from './ActivityLog';
import Questions from './Questions';
import Reports from './Reports';
import RequirementInput from './RequirementInput';
import Backlog from './Backlog';
import OrgChart from './OrgChart';
import Evolution from './Evolution';
import Knowledge from './Knowledge';
import AskOrchestrator from './AskOrchestrator';
import { t } from './i18n';

export default function TabPanel({
  topology,
  activity,
  questions,
  reports,
  requirements,
  backlog,
  evolution,
  knowledge,
  org,
  onReloadQuestions,
  onReloadReports,
  onReloadRequirements,
  onReloadEvolution,
  lang,
  mode,
}) {
  const [tab, setTab] = useState(mode === 'general' ? 'activity' : 'org');
  // If parent flips mode mid-session, keep the tab pointer pointed at
  // something the new mode actually renders.
  if (mode === 'general' && (tab === 'org' || tab === 'backlog' || tab === 'evolution' || tab === 'knowledge')) setTab('activity');

  const pendingUser = questions.filter((q) => q.status === 'pending_user').length;
  const pendingTrans = questions.filter((q) => q.status === 'pending_translation' || q.status === 'pending_answer_translation').length;
  const activeReq = requirements.filter((r) => r.status !== 'done' && r.status !== 'cancelled').length;
  const pendingEvo = (evolution || []).filter((e) => e.status === 'proposed').length;

  return (
    <div className="tabs">
      <div className="tab-bar">
        {/* Order kept identical across both modes — 조직도 only appears
            in Custom; everything else lines up so users don't have to
            re-learn the tab strip when switching modes. */}
        {mode === 'custom' && (
          <TabBtn active={tab === 'org'} onClick={() => setTab('org')} icon="🏢" label={t('tab.org', lang)} count={topology.total} />
        )}
        <TabBtn active={tab === 'activity'} onClick={() => setTab('activity')} icon="📜" label={t('tab.activity', lang)} count={activity.length} />
        <TabBtn
          active={tab === 'questions'} onClick={() => setTab('questions')} icon="❓" label={t('tab.questions', lang)}
          badge={pendingUser > 0 ? pendingUser : null}
          count={pendingTrans > 0 ? `+${pendingTrans}` : null}
        />
        <TabBtn
          active={tab === 'requirements'} onClick={() => setTab('requirements')} icon="🎯" label={t('tab.requirements', lang)}
          badge={mode === 'custom' && activeReq > 0 ? activeReq : null}
        />
        {mode === 'custom' && (
          <TabBtn active={tab === 'backlog'} onClick={() => setTab('backlog')} icon="🧾" label={t('tab.backlog', lang)} count={backlog.length} />
        )}
        {mode === 'custom' && (
          <TabBtn
            active={tab === 'evolution'} onClick={() => setTab('evolution')} icon="🌱" label={t('tab.evolution', lang)}
            badge={pendingEvo > 0 ? pendingEvo : null}
          />
        )}
        {mode === 'custom' && (
          <TabBtn
            active={tab === 'knowledge'} onClick={() => setTab('knowledge')} icon="📚" label={t('tab.knowledge', lang)}
            count={(knowledge || []).length}
          />
        )}
        <TabBtn active={tab === 'reports'} onClick={() => setTab('reports')} icon="📊" label={t('tab.reports', lang)} count={reports.length} />
      </div>
      <div className="tab-body">
        {tab === 'org' && <OrgChart topology={topology} org={org} lang={lang} />}
        {tab === 'activity' && <ActivityLog events={activity} lang={lang} />}
        {tab === 'questions' && <Questions items={questions} onReload={onReloadQuestions} lang={lang} />}
        {tab === 'requirements' && (
          /* General mode = chat-style ask-orchestrator; Custom mode =
             structured requirement form against the active project. */
          mode === 'general'
            ? <AskOrchestrator lang={lang} />
            : <RequirementInput items={requirements} onReload={onReloadRequirements} lang={lang} />
        )}
        {tab === 'backlog' && <Backlog items={backlog} lang={lang} />}
        {tab === 'evolution' && <Evolution items={evolution} onReload={onReloadEvolution} lang={lang} />}
        {tab === 'knowledge' && <Knowledge items={knowledge} lang={lang} />}
        {tab === 'reports' && <Reports items={reports} onReload={onReloadReports} lang={lang} />}
      </div>
    </div>
  );
}

function TabBtn({ active, onClick, icon, label, count, badge }) {
  return (
    <button className={active ? 'tab active' : 'tab'} onClick={onClick}>
      <span>{icon} {label}</span>
      {count != null && <span className="tab-count">{count}</span>}
      {badge != null && <span className="tab-badge">{badge}</span>}
    </button>
  );
}

import { useState } from 'react';
import ActivityLog from './ActivityLog';
import Questions from './Questions';
import Reports from './Reports';
import RequirementInput from './RequirementInput';
import Backlog from './Backlog';
import OrgChart from './OrgChart';
import { t } from './i18n';

export default function TabPanel({
  topology,
  activity,
  questions,
  reports,
  requirements,
  backlog,
  org,
  onReloadQuestions,
  onReloadReports,
  onReloadRequirements,
  lang,
}) {
  const [tab, setTab] = useState('org');

  const pendingUser = questions.filter((q) => q.status === 'pending_user').length;
  const pendingTrans = questions.filter((q) => q.status === 'pending_translation').length;
  const activeReq = requirements.filter((r) => r.status !== 'done' && r.status !== 'cancelled').length;

  return (
    <div className="tabs">
      <div className="tab-bar">
        <TabBtn active={tab === 'org'} onClick={() => setTab('org')} icon="🏢" label={t('tab.org', lang)} count={topology.total} />
        <TabBtn active={tab === 'activity'} onClick={() => setTab('activity')} icon="📜" label={t('tab.activity', lang)} count={activity.length} />
        <TabBtn
          active={tab === 'questions'} onClick={() => setTab('questions')} icon="❓" label={t('tab.questions', lang)}
          badge={pendingUser > 0 ? pendingUser : null}
          count={pendingTrans > 0 ? `+${pendingTrans}` : null}
        />
        <TabBtn
          active={tab === 'requirements'} onClick={() => setTab('requirements')} icon="🎯" label={t('tab.requirements', lang)}
          badge={activeReq > 0 ? activeReq : null}
        />
        <TabBtn active={tab === 'backlog'} onClick={() => setTab('backlog')} icon="🧾" label={t('tab.backlog', lang)} count={backlog.length} />
        <TabBtn active={tab === 'reports'} onClick={() => setTab('reports')} icon="📊" label={t('tab.reports', lang)} count={reports.length} />
      </div>
      <div className="tab-body">
        {tab === 'org' && <OrgChart topology={topology} org={org} lang={lang} />}
        {tab === 'activity' && <ActivityLog events={activity} lang={lang} />}
        {tab === 'questions' && <Questions items={questions} onReload={onReloadQuestions} lang={lang} />}
        {tab === 'requirements' && <RequirementInput items={requirements} onReload={onReloadRequirements} lang={lang} />}
        {tab === 'backlog' && <Backlog items={backlog} lang={lang} />}
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

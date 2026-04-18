import { useState } from 'react';
import ActivityLog from './ActivityLog';
import Questions from './Questions';
import Reports from './Reports';

export default function TabPanel({ topology, activity, questions, reports, onReloadQuestions, onReloadReports }) {
  const [tab, setTab] = useState('activity');

  const pending = questions.filter((q) => q.status === 'pending_user').length;
  const pendingTrans = questions.filter((q) => q.status === 'pending_translation').length;

  return (
    <div className="tabs">
      <div className="tab-bar">
        <button
          className={tab === 'activity' ? 'tab active' : 'tab'}
          onClick={() => setTab('activity')}
        >
          📜 ACTIVITY
          <span className="tab-count">{activity.length}</span>
        </button>
        <button
          className={tab === 'questions' ? 'tab active' : 'tab'}
          onClick={() => setTab('questions')}
        >
          ❓ QUESTIONS
          {pending > 0 && <span className="tab-badge">{pending}</span>}
          {pendingTrans > 0 && <span className="tab-count">+{pendingTrans}</span>}
        </button>
        <button
          className={tab === 'reports' ? 'tab active' : 'tab'}
          onClick={() => setTab('reports')}
        >
          📊 REPORTS
          <span className="tab-count">{reports.length}</span>
        </button>
      </div>
      <div className="tab-body">
        {tab === 'activity' && <ActivityLog events={activity} />}
        {tab === 'questions' && <Questions items={questions} onReload={onReloadQuestions} />}
        {tab === 'reports' && <Reports items={reports} onReload={onReloadReports} />}
      </div>
    </div>
  );
}

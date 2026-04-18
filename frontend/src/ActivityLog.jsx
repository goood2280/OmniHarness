import { t } from './i18n';

const KIND_ICON = {
  state: '⚡',
  tool: '🔧',
  invoke: '▶',
  complete: '✓',
  question: '❓',
  report: '📊',
  requirement: '🎯',
  'user-prompt': '🗣',
  boot: '🚀',
  demo: '🎬',
  mission: '🎯',
  error: '⚠️',
};

export default function ActivityLog({ events, lang }) {
  if (!events.length) {
    return (
      <div className="empty">
        <p>{t('activity.empty_title', lang)}</p>
        <p className="muted">{t('activity.empty_body', lang)}</p>
        <p className="muted">{t('activity.empty_hint', lang)}</p>
      </div>
    );
  }
  return (
    <div className="activity">
      {events.map((e) => (
        <div key={e.id} className={`act-row act-${e.kind}`}>
          <span className="act-ts">{(e.ts || '').slice(11, 19)}</span>
          <span className="act-icon">{KIND_ICON[e.kind] || '·'}</span>
          <span className="act-agent">{e.agent}</span>
          <span className="act-detail">{e.detail}</span>
        </div>
      ))}
    </div>
  );
}

import { t } from './i18n';

const PRI_ORDER = { P0: 0, P1: 1, P2: 2 };

export default function Backlog({ lang, items }) {
  if (!items || items.length === 0) {
    return (
      <div className="backlog">
        <p className="backlog-hint" style={{ textAlign: 'center' }}>
          {t('bk.empty', lang)}
        </p>
      </div>
    );
  }

  const sorted = [...items].sort((a, b) => {
    const pa = PRI_ORDER[a.priority] ?? 99;
    const pb = PRI_ORDER[b.priority] ?? 99;
    if (pa !== pb) return pa - pb;
    return (a.title || '').localeCompare(b.title || '');
  });

  return (
    <div className="backlog">
      <p className="backlog-hint">{t('bk.hint', lang)}</p>
      <table className="backlog-table">
        <thead>
          <tr>
            <th>{t('bk.col.title', lang)}</th>
            <th>{t('bk.col.team', lang)}</th>
            <th>{t('bk.col.priority', lang)}</th>
            <th>{t('bk.col.estimate', lang)}</th>
            <th>{t('bk.col.status', lang)}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((it) => (
            <tr key={it.id}>
              <td>{it.title}</td>
              <td>
                <span className={`team-chip team-${it.team}`}>
                  {t(`team.${it.team}`, lang)}
                </span>
              </td>
              <td>
                <span className={`pri-dot pri-${it.priority}`} />
                {it.priority}
              </td>
              <td>{it.estimate}</td>
              <td>
                <span className={`bk-status bk-status-${it.status}`}>
                  {it.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

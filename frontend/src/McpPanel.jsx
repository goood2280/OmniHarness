import { t } from './i18n';

// Right-docked sidebar (mirrors AgentPanel). No more center popup — the
// product owner wants every detail surface to land in the same place so
// users don't hunt around the screen.
export default function McpPanel({ mcp, onClose, lang }) {
  if (!mcp) return null;
  const isSkill = !mcp.icon_tile;
  const name = lang === 'en'
    ? (mcp.name_en || mcp.name_ko || mcp.label)
    : (mcp.name_ko || mcp.name_en || mcp.label);
  const purpose = lang === 'en'
    ? (mcp.purpose_en || mcp.purpose_ko)
    : (mcp.purpose_ko || mcp.purpose_en);
  const kindLabel = isSkill ? t('canteen.skill_label', lang) : t('canteen.mcp_label', lang);
  const kindDesc = isSkill ? t('canteen.skill_desc', lang) : t('canteen.mcp_desc', lang);

  return (
    <div className="panel">
      <button className="close" onClick={onClose} aria-label={t('mcp.close', lang)}>×</button>
      <div className="panel-head">
        <div className="panel-emoji">{isSkill ? '📖' : '🔧'}</div>
        <div className="panel-head-text">
          <h2>{name}</h2>
          <div className="panel-subname">{mcp.id}</div>
          <div className="meta">
            <span className="chip">{kindLabel}</span>
          </div>
        </div>
      </div>

      <h3>{lang === 'ko' ? '용도' : 'Purpose'}</h3>
      <p className="desc">{purpose || t('mcp.not_found', lang)}</p>

      <h3>{lang === 'ko' ? '분류' : 'Category'}</h3>
      <p className="desc">{kindDesc}</p>
    </div>
  );
}

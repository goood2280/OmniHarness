import { t } from './i18n';

export default function McpPanel({ mcp, onClose, lang }) {
  if (!mcp) return null;
  const isSkill = !mcp.icon_tile;
  const name = lang === 'en' ? (mcp.name_en || mcp.name_ko || mcp.label) : (mcp.name_ko || mcp.name_en || mcp.label);
  const purpose = lang === 'en' ? (mcp.purpose_en || mcp.purpose_ko) : (mcp.purpose_ko || mcp.purpose_en);
  return (
    <div className="mcp-overlay" onClick={onClose}>
      <div className={`mcp-card${isSkill ? ' mcp-card-skill' : ''}`} onClick={(e) => e.stopPropagation()}>
        <button className="mcp-close" onClick={onClose} aria-label={t('mcp.close', lang)}>×</button>
        <div className="mcp-head">
          <div className="mcp-emoji-box">{isSkill ? '📖' : '🔧'}</div>
          <div>
            <div className="mcp-tag">{isSkill ? t('canteen.skill_label', lang) : t('canteen.mcp_label', lang)}</div>
            <h2>{name}</h2>
            <code className="mcp-id">{mcp.id}</code>
          </div>
        </div>
        <p className="mcp-purpose">{purpose || t('mcp.not_found', lang)}</p>
      </div>
    </div>
  );
}

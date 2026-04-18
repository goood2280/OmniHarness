import { t } from './i18n';

export default function McpPanel({ mcp, onClose, lang }) {
  if (!mcp) return null;
  const name = lang === 'en' ? (mcp.name_en || mcp.name_ko) : (mcp.name_ko || mcp.name_en);
  const purpose = lang === 'en' ? (mcp.purpose_en || mcp.purpose_ko) : (mcp.purpose_ko || mcp.purpose_en);
  return (
    <div className="mcp-overlay" onClick={onClose}>
      <div className="mcp-card" onClick={(e) => e.stopPropagation()}>
        <button className="mcp-close" onClick={onClose} aria-label={t('mcp.close', lang)}>×</button>
        <div className="mcp-head">
          <img className="mcp-icon" src={`/tiles/${mcp.icon_tile}.png`} alt="" />
          <div>
            <div className="mcp-tag">{t('mcp.title', lang)}</div>
            <h2>{name}</h2>
            <code className="mcp-id">{mcp.id}</code>
          </div>
        </div>
        <p className="mcp-purpose">{purpose || t('mcp.not_found', lang)}</p>
      </div>
    </div>
  );
}

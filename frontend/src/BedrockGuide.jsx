import { useEffect, useState } from 'react';
import { t } from './i18n';

export default function BedrockGuide({ open, onClose, lang }) {
  const [guide, setGuide] = useState(null);

  useEffect(() => {
    if (!open) return;
    fetch('/api/guide/bedrock')
      .then((r) => (r.ok ? r.json() : null))
      .then(setGuide)
      .catch(() => setGuide(null));
  }, [open]);

  if (!open) return null;

  const title = guide && (lang === 'en' ? guide.title_en : guide.title_ko);
  const sections =
    guide && (lang === 'en' ? guide.sections_en : guide.sections_ko) || [];

  return (
    <div className="guide-overlay" onClick={onClose}>
      <div className="guide-card" onClick={(e) => e.stopPropagation()}>
        <button className="guide-close" onClick={onClose} aria-label="Close">×</button>
        <div className="guide-head">
          <span className="guide-tag">☁ GUIDE · Bedrock</span>
          <h2>{title || t('guide.loading', lang)}</h2>
        </div>
        <div className="guide-body">
          {sections.map((s, i) => (
            <section key={i} className="guide-section">
              <h3>{s.h}</h3>
              <pre>{s.body}</pre>
            </section>
          ))}
        </div>
        <footer className="guide-foot">
          <a
            href="https://docs.anthropic.com/en/docs/claude-code/overview#third-party-apis"
            target="_blank"
            rel="noreferrer"
          >
            {t('guide.official_docs', lang)} ↗
          </a>
        </footer>
      </div>
    </div>
  );
}

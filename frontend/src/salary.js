// Per-model "salary" — token pricing in USD per million tokens.
// Source of truth for the agent detail panel's salary line.
// Kept as a plain constant (no external dep) so unit-test / DOM-scrape
// is trivial.
export const SALARY = {
  opus:   { in: 15.00, out: 75.00 },
  sonnet: { in:  3.00, out: 15.00 },
  haiku:  { in:  1.00, out:  5.00 },
};

const LABEL = {
  opus:   'Opus',
  sonnet: 'Sonnet',
  haiku:  'Haiku',
};

// Fallback when an agent lacks a model field. Matches the backend's
// `spec.get("model") or "sonnet"` default so the UI stays consistent.
const DEFAULT_MODEL = 'sonnet';

function fmtUsd(n) {
  return '$' + n.toFixed(2);
}

// formatSalary("opus", "ko") →
//   "💰 월급 · Opus · 입력 $15.00 / 출력 $75.00 /MTok"
// formatSalary("opus", "en") →
//   "💰 Salary · Opus · in $15.00 / out $75.00 per MTok"
export function formatSalary(model, lang = 'en') {
  const key = SALARY[model] ? model : DEFAULT_MODEL;
  const p = SALARY[key];
  const name = LABEL[key];
  if (lang === 'ko') {
    return `💰 월급 · ${name} · 입력 ${fmtUsd(p.in)} / 출력 ${fmtUsd(p.out)} /MTok`;
  }
  return `💰 Salary · ${name} · in ${fmtUsd(p.in)} / out ${fmtUsd(p.out)} per MTok`;
}

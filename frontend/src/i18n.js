// i18n.js — Korean + English translations for OmniHarness viewer
// No external deps. Importers use: `import { t, LANG_OPTIONS, TRANSLATIONS, DEFAULT_LANG } from './i18n'`.

export const DEFAULT_LANG = 'ko';

export const LANG_OPTIONS = [
  { code: 'ko', label: '한국어' },
  { code: 'en', label: 'English' },
];

export const TRANSLATIONS = {
  // HUD
  'hud.agents': { ko: '에이전트', en: 'AGENTS' },
  'hud.work': { ko: '작업중', en: 'WORK' },
  'hud.wait': { ko: '대기', en: 'WAIT' },
  'hud.idle': { ko: '대기중', en: 'IDLE' },
  'hud.cost': { ko: '누적비용', en: 'SPEND' },
  'hud.year': { ko: '연도', en: 'YEAR' },
  'hud.demo_on': { ko: 'DEMO 켜짐', en: 'DEMO ON' },
  'hud.demo_off': { ko: 'DEMO 꺼짐', en: 'DEMO OFF' },
  'hud.demo_toggle_title_on': {
    ko: '시뮬레이션 중 — 클릭해서 끄기',
    en: 'Simulating — click to stop',
  },
  'hud.demo_toggle_title_off': {
    ko: '실제 작업 대기 중 — 클릭해서 시뮬레이션',
    en: 'Waiting for real work — click to simulate',
  },
  'hud.lang': { ko: '언어', en: 'LANG' },

  // Awaiting bar
  'awaiting.title': { ko: '실제 작업 대기 중', en: 'Waiting for real work' },
  'awaiting.body': {
    ko: 'FabCanvas.ai 생성을 위하여 Claude Code 가 돌아가면 거기에 맞는 에이전트들이 활성화됩니다.',
    en: 'When Claude Code is running to build FabCanvas.ai, the relevant agents will light up here.',
  },
  'awaiting.hint': {
    ko: '또는 우측 DEMO 버튼으로 시뮬레이션을 확인',
    en: 'Or toggle DEMO on the right to see a simulation',
  },

  // Mission banner / modal
  'mission.label': { ko: '사훈', en: 'MISSION' },
  'mission.modal_title': { ko: '사훈 (Mission) 설정', en: 'Set Mission' },
  'mission.hint': {
    ko: '이 사훈은 모든 에이전트의 공통 목표가 됩니다. 업종 / 철학 / 목표를 적어주세요. 이후 상단 배너에서 언제든 수정 가능합니다.',
    en: "This mission becomes the shared goal of every agent. Fill in industry / philosophy / goal; you can edit later from the banner.",
  },
  'mission.industry': { ko: '업종', en: 'Industry' },
  'mission.industry_ph': {
    ko: '예: 반도체 Fab IT / 수율 분석 도구',
    en: 'e.g. Semiconductor Fab IT / yield-analysis tools',
  },
  'mission.philosophy': { ko: '철학', en: 'Philosophy' },
  'mission.philosophy_ph': {
    ko: '예: 현장 엔지니어가 바로 쓸 수 있게, 복잡도는 숨기고 결정은 빠르게',
    en: 'e.g. Usable by line engineers, hide complexity, decide fast',
  },
  'mission.goal': { ko: '목표', en: 'Goal' },
  'mission.goal_ph': {
    ko: '예: 3개월 내 SPC/Tracker 통합 + 대시보드 자동 생성',
    en: 'e.g. SPC/Tracker integration + auto dashboards within 3 months',
  },
  'mission.required': { ko: '필수', en: 'required' },
  'mission.save': { ko: '저장', en: 'Save' },
  'mission.cancel': { ko: '취소', en: 'Cancel' },
  'mission.edit_tooltip': { ko: '클릭해서 수정', en: 'Click to edit' },

  // Tabs
  'tab.activity': { ko: '활동', en: 'Activity' },
  'tab.questions': { ko: '질문', en: 'Questions' },
  'tab.reports': { ko: '보고서', en: 'Reports' },
  'tab.backlog': { ko: '백로그', en: 'Backlog' },
  'tab.requirements': { ko: '요구사항', en: 'Requirements' },

  // Activity log
  'activity.empty_title': { ko: '아직 기록이 없습니다.', en: 'No activity yet.' },
  'activity.empty_body': {
    ko: 'FabCanvas.ai 생성을 위하여 Claude Code 가 돌아가면 실시간 로그가 여기에 쌓입니다.',
    en: 'When Claude Code runs to build FabCanvas.ai, live logs accumulate here.',
  },
  'activity.empty_hint': {
    ko: '상단 우측 DEMO 토글로 시뮬레이션을 볼 수 있습니다.',
    en: 'Toggle DEMO on the right to see a simulation.',
  },

  // Questions
  'q.empty_title': { ko: '대기 중인 질문이 없습니다.', en: 'No questions waiting.' },
  'q.empty_body': {
    ko: '에이전트가 개발 중 모호한 결정을 만나면, 경영지원팀 lead가 이해하기 쉬운 언어로 풀어서 여기에 질문이 올라옵니다. 답변하면 앱 개발에 즉시 반영됩니다.',
    en: 'When an agent hits an ambiguous decision, mgmt-lead translates it into friendly language and surfaces it here. Your answer flows straight back into development.',
  },
  'q.status_pending_translation': {
    ko: '🔄 경영지원팀에서 풀어서 쓰는 중',
    en: '🔄 mgmt-lead is translating',
  },
  'q.status_pending_user': {
    ko: '💬 당신의 답변이 필요합니다',
    en: '💬 your answer is needed',
  },
  'q.status_answered': { ko: '✅ 답변 완료', en: '✅ answered' },
  'q.translating': {
    ko: '경영지원팀이 번역 중입니다…',
    en: 'mgmt-lead is translating…',
  },
  'q.raw_summary': {
    ko: '원문 (에이전트가 쓴 기술적 설명)',
    en: 'Raw (technical wording from the agent)',
  },
  'q.answer_ph': {
    ko: "답변을 적으세요. 간단해도 됩니다. (예: A, 또는 '기본값 7일로 가시죠')",
    en: "Write your answer. Short is fine (e.g. 'A', or 'let's default to 7 days')",
  },
  'q.send': { ko: '답변 보내기', en: 'Send answer' },
  'q.sending': { ko: '전송 중…', en: 'Sending…' },
  'q.my_answer': { ko: '내 답변:', en: 'My answer:' },

  // Reports
  'rep.empty_title': { ko: '발행된 보고서가 없습니다.', en: 'No reports yet.' },
  'rep.empty_body': {
    ko: '의미있는 변경점이 모이면 경영지원팀 보고원이 자동으로 보기 좋은 한국어 요약 보고서를 발행합니다.',
    en: 'When meaningful changes accumulate, reporter publishes a polished summary automatically.',
  },
  'rep.select_hint': {
    ko: '왼쪽에서 보고서를 선택하세요.',
    en: 'Pick a report on the left.',
  },

  // Requirements (new)
  'req.title': {
    ko: 'Orchestrator 에게 요구사항 전달',
    en: 'Send a Requirement to Orchestrator',
  },
  'req.hint': {
    ko: '사훈 범위 안에서 이 앱에 무엇이 필요한지 자유롭게 적어주세요. 총괄이 적절한 팀으로 할당합니다.',
    en: "Within the mission's scope, describe what this app needs. The orchestrator will assign it to the right team.",
  },
  'req.placeholder': {
    ko: '예: 대시보드에 부서별 수율 비교 차트 추가해주세요.',
    en: 'e.g. Please add a department-level yield comparison chart on the dashboard.',
  },
  'req.send': { ko: '전달', en: 'Send' },
  'req.sending': { ko: '전달 중…', en: 'Sending…' },
  'req.recent': { ko: '최근 요구사항', en: 'Recent requirements' },
  'req.empty': {
    ko: '아직 전달된 요구사항이 없습니다.',
    en: 'No requirements sent yet.',
  },
  'req.status.new': { ko: '신규', en: 'new' },
  'req.status.planning': { ko: '기획중', en: 'planning' },
  'req.status.in_progress': { ko: '진행중', en: 'in-progress' },
  'req.status.done': { ko: '완료', en: 'done' },
  'req.status.cancelled': { ko: '취소됨', en: 'cancelled' },
  'req.filter.all': { ko: '전체', en: 'All' },
  'req.filter.waiting': { ko: '대기', en: 'Waiting' },
  'req.filter.working': { ko: '진행중', en: 'In progress' },
  'req.filter.done': { ko: '완료', en: 'Done' },
  'req.filter.cancelled': { ko: '취소', en: 'Cancelled' },
  'req.cancel': { ko: '취소', en: 'Cancel' },
  'req.cancelling': { ko: '취소중…', en: 'Cancelling…' },
  'req.confirm_cancel': { ko: '이 요구사항을 취소하시겠습니까?', en: 'Cancel this requirement?' },
  'req.detail.close': { ko: '닫기', en: 'Close' },

  // Backlog (new)
  'bk.empty': { ko: '백로그가 비어있습니다.', en: 'Backlog is empty.' },
  'bk.hint': {
    ko: 'HR 과 팀 lead 들이 협의 후 승인한 예정 작업 목록입니다. 상위일수록 우선순위가 높습니다.',
    en: 'Upcoming work approved by HR and team leads. Top = higher priority.',
  },
  'bk.col.title': { ko: '제목', en: 'Title' },
  'bk.col.team': { ko: '팀', en: 'Team' },
  'bk.col.priority': { ko: '우선순위', en: 'Priority' },
  'bk.col.estimate': { ko: '추정', en: 'Est.' },
  'bk.col.status': { ko: '상태', en: 'Status' },

  // Legend (team labels)
  'team.top': { ko: '총괄', en: 'Orchestrator' },
  'team.leads': { ko: '팀 리드', en: 'Team Leads' },
  'team.backend': { ko: '개발1팀 Backend', en: 'Dev-1 Backend' },
  'team.frontend': { ko: '개발2팀 Frontend', en: 'Dev-2 Frontend' },
  'team.mgmt': { ko: '경영지원팀', en: 'Management Support' },
  'team.eval': { ko: '평가팀', en: 'Evaluation' },
  'team.kitchen': { ko: '키친 · MCP', en: 'Kitchen · MCP' },

  // AgentPanel
  'panel.click_hint': {
    ko: '캐릭터를 클릭하면 정보가 여기 표시됩니다.',
    en: 'Click a character to see its info here.',
  },
  'panel.tools': { ko: '도구', en: 'Tools' },
  'panel.system_prompt': { ko: '시스템 프롬프트', en: 'System prompt' },
  'panel.model': { ko: '모델', en: 'model' },
  'panel.team': { ko: '팀', en: 'team' },
  'panel.species': { ko: '종', en: 'species' },

  // Loading / errors
  'loading.app': { ko: 'OMNIHARNESS 로딩 중…', en: 'LOADING OMNIHARNESS…' },
  'loading.error': { ko: '오류', en: 'ERROR' },

  // Org chart (drill-down tab)
  'org.title': { ko: '조직도', en: 'Organization' },
  'org.back_to_teams': { ko: '팀 목록으로', en: 'Back to teams' },
  'org.back_to_team': { ko: '팀으로', en: 'Back to team' },
  'org.team_working': { ko: '작업중', en: 'working' },
  'org.no_members': { ko: '팀원이 없습니다.', en: 'No members.' },
  'org.tools': { ko: '도구', en: 'Tools' },
  'org.system_prompt': { ko: '시스템 프롬프트', en: 'System prompt' },
  'org.description_heading': { ko: '역할 설명', en: 'Role description' },
  'tab.org': { ko: '조직도', en: 'Org' },

  // MCP popup
  'mcp.title': { ko: 'MCP 도구', en: 'MCP Tool' },
  'mcp.close': { ko: '닫기', en: 'Close' },
  'mcp.not_found': { ko: '이 기능의 설명이 아직 없습니다.', en: 'No description available for this tool.' },

  // Zoom
  'zoom.in': { ko: '확대', en: 'Zoom in' },
  'zoom.out': { ko: '축소', en: 'Zoom out' },
  'zoom.reset': { ko: '원래 크기', en: 'Reset zoom' },

  // Mission — company field + helper text
  'mission.company': { ko: '회사 / 프로젝트 이름', en: 'Company / Project name' },
  'mission.company_ph': { ko: '예: FabCanvas · Acme Fab IT', en: 'e.g. FabCanvas · Acme Fab IT' },
  'mission.chip_company': { ko: '회사', en: 'Company' },

  // Guide (Bedrock)
  'guide.button': { ko: '가이드', en: 'GUIDE' },
  'guide.loading': { ko: '가이드 불러오는 중…', en: 'Loading guide…' },
  'guide.official_docs': { ko: '공식 문서 보기', en: 'Official docs' },

  // Teams (new roster — override the old backend/frontend labels)
  'team.dev': { ko: '개발팀', en: 'Dev Team' },
  'team.domain': { ko: '도메인 전문', en: 'Domain Specialists' },

  // Agent display names (ko: Korean, en: kebab English name)
  'agent.orchestrator':      { ko: '총괄', en: 'orchestrator' },
  'agent.dev-lead':          { ko: '개발 리드', en: 'dev-lead' },
  'agent.mgmt-lead':         { ko: '경영지원 리드', en: 'mgmt-lead' },
  'agent.eval-lead':         { ko: '평가 리드', en: 'eval-lead' },
  'agent.dev-dashboard':     { ko: '대시보드 개발', en: 'dev-dashboard' },
  'agent.dev-spc':           { ko: 'SPC 개발', en: 'dev-spc' },
  'agent.dev-wafer-map':     { ko: 'Wafer Map 개발', en: 'dev-wafer-map' },
  'agent.dev-ml':            { ko: 'ML 분석 개발', en: 'dev-ml' },
  'agent.dev-ettime':        { ko: 'ET 시간분석 개발', en: 'dev-ettime' },
  'agent.dev-tablemap':      { ko: 'Table Map 개발', en: 'dev-tablemap' },
  'agent.dev-tracker':       { ko: '트래커 개발', en: 'dev-tracker' },
  'agent.dev-filebrowser':   { ko: '파일 브라우저 개발', en: 'dev-filebrowser' },
  'agent.dev-admin':         { ko: 'Admin 개발', en: 'dev-admin' },
  'agent.dev-messages':      { ko: '메시지 개발', en: 'dev-messages' },
  'agent.process-tagger':    { ko: '공정영역 태거', en: 'process-tagger' },
  'agent.causal-analyst':    { ko: '인과 분석가', en: 'causal-analyst' },
  'agent.dvc-curator':       { ko: 'DVC 큐레이터', en: 'dvc-curator' },
  'agent.adapter-engineer':  { ko: '어댑터 엔지니어', en: 'adapter-engineer' },
  'agent.reporter':          { ko: '보고원', en: 'reporter' },
  'agent.hr':                { ko: '인사원', en: 'hr' },
  'agent.ux-reviewer':       { ko: 'UX 리뷰어', en: 'ux-reviewer' },
  'agent.dev-verifier':      { ko: '개발 검증', en: 'dev-verifier' },
  'agent.user-role-tester':  { ko: '유저 테스터', en: 'user-role-tester' },
  'agent.admin-role-tester': { ko: '관리자 테스터', en: 'admin-role-tester' },
  'agent.security-auditor':  { ko: '보안 감사', en: 'security-auditor' },
  'agent.domain-researcher': { ko: '도메인 조사', en: 'domain-researcher' },
};

export function t(key, lang = DEFAULT_LANG) {
  const useLang = lang === 'ko' || lang === 'en' ? lang : DEFAULT_LANG;
  const entry = TRANSLATIONS[key];
  if (!entry) return key;
  return entry[useLang] || entry[DEFAULT_LANG] || key;
}

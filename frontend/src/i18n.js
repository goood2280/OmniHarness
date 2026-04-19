// i18n.js — Korean + English translations for OmniHarness viewer.
// No external deps. Importers use: `import { t, LANG_OPTIONS, DEFAULT_LANG } from './i18n'`.

export const DEFAULT_LANG = 'en';

export const LANG_OPTIONS = [
  { code: 'ko', label: '한국어' },
  { code: 'en', label: 'English' },
];

export const TRANSLATIONS = {
  // HUD
  'hud.agents': { ko: '에이전트', en: 'AGENTS' },
  'hud.work':   { ko: '작업중', en: 'WORK' },
  'hud.wait':   { ko: '대기',   en: 'WAIT' },
  'hud.idle':   { ko: '대기중', en: 'IDLE' },
  'hud.cost':   { ko: '누적비용', en: 'SPEND' },
  'hud.lang':   { ko: '언어', en: 'LANG' },
  'hud.mode.project': { ko: '프로젝트', en: 'PROJECT' },
  'hud.mode.general': { ko: '제너럴', en: 'GENERAL' },
  'hud.mode.title':   { ko: '모드 전환', en: 'Switch mode' },
  'hud.switch_project': { ko: '프로젝트 전환', en: 'Switch project' },

  // Chat dock
  'chat.open':       { ko: '질문하기', en: 'Ask' },
  'chat.title':      { ko: 'Orchestrator 에게 질문', en: 'Ask the orchestrator' },
  'chat.empty':      {
    ko: '프로젝트 맥락에 맞춰 오케스트레이터가 답합니다. 필요 시 서브에이전트로 위임합니다.',
    en: 'The orchestrator answers in your project\'s context, delegating to subagents as needed.',
  },
  'chat.placeholder':{ ko: '질문을 입력하세요 (Ctrl/⌘+Enter 전송)', en: 'Ask anything (Ctrl/⌘+Enter sends)' },
  'chat.send':       { ko: '전송', en: 'Send' },
  'chat.sending':    { ko: '전송 중…', en: 'Sending…' },
  'chat.stub_warning': {
    ko: 'LLM API 가 연결되지 않아 STUB 응답입니다. HUD ☁ 가이드 → Bedrock 또는 Anthropic 설정을 참고하세요.',
    en: 'No LLM API connected — returning STUB responses. See the ☁ GUIDE for Bedrock / Anthropic setup.',
  },

  // Awaiting bar
  'awaiting.title': { ko: '실제 작업 대기 중', en: 'Waiting for real work' },
  'awaiting.body':  {
    ko: '{company} 프로젝트에서 Claude Code 가 돌아가면 해당하는 에이전트들의 책상 모니터가 켜집니다.',
    en: 'When Claude Code runs inside the {company} project, the matching agents\' monitors will light up.',
  },

  // Mission banner / modal
  'mission.label':         { ko: '사훈', en: 'MISSION' },
  'mission.modal_title':   { ko: '사훈 설정', en: 'Set Mission' },
  'mission.hint':          {
    ko: '이 사훈은 모든 에이전트의 공통 목표가 됩니다. 이후 상단 배너에서 언제든 수정 가능합니다.',
    en: 'This mission becomes the shared goal of every agent. You can edit it anytime from the banner.',
  },
  'mission.company':       { ko: '회사 / 프로젝트 이름', en: 'Company / Project name' },
  'mission.company_ph':    { ko: '예: Acme · MyShop · DataLab', en: 'e.g. Acme · MyShop · DataLab' },
  'mission.industry':      { ko: '업종 / 도메인', en: 'Industry / Domain' },
  'mission.industry_ph':   { ko: '예: 이커머스, 반도체 Fab IT, 데이터 분석', en: 'e.g. e-commerce, semiconductor fab IT, data analytics' },
  'mission.philosophy':    { ko: '철학', en: 'Philosophy' },
  'mission.philosophy_ph': { ko: '예: 현장에서 바로 쓰게, 복잡도는 숨기고 결정은 빠르게', en: 'e.g. Usable on day 1, hide complexity, decide fast' },
  'mission.goal':          { ko: '목표', en: 'Goal' },
  'mission.goal_ph':       { ko: '예: 3개월 내 v1 출시', en: 'e.g. Ship v1 within 3 months' },
  'mission.save':          { ko: '저장', en: 'Save' },
  'mission.cancel':        { ko: '취소', en: 'Cancel' },
  'mission.edit_tooltip':  { ko: '클릭해서 수정', en: 'Click to edit' },
  'mission.chip_company':  { ko: '회사', en: 'Company' },

  // Onboarding wizard
  'wiz.step1':     { ko: '사훈',   en: 'Mission' },
  'wiz.step2':     { ko: '팀 구성', en: 'Team' },
  'wiz.step3':     { ko: '확정',   en: 'Confirm' },
  'wiz.title1':    { ko: '프로젝트 사훈을 입력하세요', en: 'Tell us about this project' },
  'wiz.hint1':     {
    ko: '회사/프로젝트 이름, 업종, 철학, 목표를 적어주시면 오케스트레이터가 가장 적합한 에이전트 팀 구성을 제안합니다.',
    en: 'Enter the company/project name, domain, philosophy, and goal. The orchestrator will propose the most efficient team.',
  },
  'wiz.title2':    { ko: '오케스트레이터가 제안한 팀 구성', en: 'Proposed team structure' },
  'wiz.hint2':     {
    ko: '{company} 에 가장 효율적인 팀이에요. 원하는 대로 추가/제거할 수 있습니다. 기본 팀은 고정입니다.',
    en: 'This is the most efficient team for {company}. You can add or remove dynamic members. The base team is fixed.',
  },
  'wiz.title3':    { ko: '확정 — 이대로 운영합니다', en: 'Confirm — run with this roster' },
  'wiz.hint3':     {
    ko: '{company} 프로젝트의 Claude Code 가 돌기 시작하면, 아래 에이전트들이 책상에 앉아 작업합니다.',
    en: 'Once Claude Code starts running inside the {company} project, these agents will sit at desks and work.',
  },
  'wiz.reason':       { ko: '판단 근거', en: 'Reasoning' },
  'wiz.base_label':   { ko: '기본 팀 (고정)', en: 'Base team (fixed)' },
  'wiz.dev_label':    { ko: '개발팀', en: 'Dev team' },
  'wiz.dev_sub':      { ko: '기능 담당 개발자. 체크한 만큼 활성화됩니다.', en: 'Feature engineers — activate the ones you want.' },
  'wiz.domain_label': { ko: '도메인 전문가', en: 'Domain specialists' },
  'wiz.domain_sub':   { ko: '해당 업종의 지식 커스터디언. 없어도 동작합니다.', en: 'Knowledge custodians for this domain. Optional.' },
  'wiz.eval_team':    { ko: '평가팀', en: 'Eval team' },
  'wiz.none':         { ko: '(없음)', en: '(none)' },
  'wiz.next':         { ko: '다음 →', en: 'Next →' },
  'wiz.back':         { ko: '← 뒤로', en: '← Back' },
  'wiz.confirm':      { ko: '✓ 확인', en: '✓ Confirm' },
  'wiz.saving':       { ko: '저장 중…', en: 'Saving…' },
  'wiz.thinking':     { ko: '팀 구성 중…', en: 'Designing team…' },
  'wiz.roster_total': { ko: '총 에이전트', en: 'Total agents' },
  'wiz.base_count':   { ko: '기본', en: 'base' },
  'wiz.show_catalog': { ko: '＋ 전체 카탈로그에서 추가', en: '＋ Add from full catalog' },
  'wiz.hide_catalog': { ko: '− 추천 팀만 보기',          en: '− Show proposed only' },

  // Tabs
  'tab.activity':     { ko: '활동',       en: 'Activity' },
  'tab.questions':    { ko: '질문',       en: 'Questions' },
  'tab.reports':      { ko: '보고서',     en: 'Reports' },
  'tab.backlog':      { ko: '백로그',     en: 'Backlog' },
  'tab.requirements': { ko: '요구사항',   en: 'Requirements' },
  'tab.evolution':    { ko: '감사',       en: 'Audit' },
  'tab.knowledge':    { ko: '누적 지식',  en: 'Knowledge' },
  'tab.org':          { ko: '조직도',     en: 'Org' },

  // Activity log
  'activity.empty_title': { ko: '아직 기록이 없습니다.', en: 'No activity yet.' },
  'activity.empty_body':  {
    ko: '프로젝트에서 Claude Code 가 돌아가면 실시간 로그가 여기에 쌓입니다.',
    en: 'When Claude Code runs inside the project, live logs accumulate here.',
  },

  // Questions
  'q.empty_title':  { ko: '대기 중인 질문이 없습니다.', en: 'No questions waiting.' },
  'q.empty_body':   {
    ko: '에이전트가 모호한 결정을 만나면 오케스트레이터가 이해하기 쉬운 언어로 풀어서 여기에 질문이 올라오고, 당신 답변도 오케스트레이터가 적절히 변환해 에이전트에게 전달합니다.',
    en: 'When an agent hits an ambiguous decision, the orchestrator rewrites it in friendly language here. Your answer gets translated back into structured input for the agent.',
  },
  'q.status_pending_translation': { ko: '🔄 오케스트레이터가 질문을 풀어 쓰는 중', en: '🔄 orchestrator is rewriting' },
  'q.status_pending_user':        { ko: '💬 당신의 답변이 필요합니다', en: '💬 your answer is needed' },
  'q.status_pending_answer_translation': { ko: '🔁 오케스트레이터가 답변을 에이전트 언어로 변환 중', en: '🔁 orchestrator is restating your answer for the agent' },
  'q.status_answered':            { ko: '✅ 답변 전달 완료', en: '✅ delivered to agent' },
  'q.translating': { ko: '오케스트레이터가 풀어 쓰는 중…', en: 'orchestrator is rewriting…' },
  'q.raw_summary': { ko: '원문 (에이전트가 쓴 기술적 설명)', en: 'Raw (technical wording from the agent)' },
  'q.answer_ph':   {
    ko: '답변을 적으세요. 간단해도 됩니다. (예: A, 또는 "기본값 7일로 가시죠")',
    en: 'Write your answer. Short is fine (e.g. "A", or "let\'s default to 7 days").',
  },
  'q.send':        { ko: '답변 보내기', en: 'Send answer' },
  'q.sending':     { ko: '전송 중…', en: 'Sending…' },
  'q.my_answer':   { ko: '내 답변', en: 'My answer' },
  'q.structured':  { ko: '에이전트 전달용 변환', en: 'Structured for agent' },
  'q.chat_tip':    {
    ko: '💬 채팅에서 `fabCanvas 질문 Q003 답 : <텍스트>` 로 답변 가능',
    en: '💬 You can answer in chat with `fabCanvas question Q003 answer : <text>`',
  },
  'q.empty_chat_hint': {
    ko: '💡 채팅에서 `fabCanvas 요구사항 : <텍스트>` 로 요구사항 등록 · `fabCanvas 질문 Q003 답 : <텍스트>` 로 답변',
    en: '💡 In chat: `fabCanvas requirement : <text>` to add a requirement · `fabCanvas question Q003 answer : <text>` to reply',
  },
  'q.answer_ph_with_id': {
    ko: '답변 (short_id: {sid}). 간단해도 됩니다. (예: A, 또는 "기본값 7일로 가시죠")',
    en: 'Answer (short_id: {sid}). Short is fine (e.g. "A", or "default to 7 days").',
  },

  // Reports
  'rep.empty_title': { ko: '발행된 보고서가 없습니다.', en: 'No reports yet.' },
  'rep.empty_body':  {
    ko: '의미있는 변경점이 모이면 오케스트레이터가 자동으로 평어체 요약 보고서를 발행합니다. 요구사항을 올리면 초안 리포트도 여기에 먼저 뜹니다.',
    en: 'When meaningful changes accumulate, the orchestrator publishes a plain-language summary. New requirements land a draft report here first.',
  },
  'rep.select_hint': { ko: '왼쪽에서 보고서를 선택하세요.', en: 'Pick a report on the left.' },

  // Requirements
  'req.title':        { ko: '오케스트레이터에게 요구사항 전달', en: 'Send a Requirement to Orchestrator' },
  'req.hint':         {
    ko: '사훈 범위 안에서 이 프로젝트에 무엇이 필요한지 자유롭게 적어주세요. 총괄이 적절한 팀으로 할당합니다.',
    en: "Within the mission's scope, describe what this project needs. The orchestrator will assign it to the right team.",
  },
  'req.placeholder':  { ko: '예: 대시보드에 비교 차트 추가해주세요.', en: 'e.g. Add a comparison chart on the dashboard.' },
  'req.send':         { ko: '전달', en: 'Send' },
  'req.sending':      { ko: '전달 중…', en: 'Sending…' },
  'req.recent':       { ko: '최근 요구사항', en: 'Recent requirements' },
  'req.empty':        { ko: '아직 전달된 요구사항이 없습니다.', en: 'No requirements sent yet.' },
  'req.status.new':          { ko: '신규',   en: 'new' },
  'req.status.planning':     { ko: '기획중', en: 'planning' },
  'req.status.in_progress':  { ko: '진행중', en: 'in-progress' },
  'req.status.done':         { ko: '완료',   en: 'done' },
  'req.status.cancelled':    { ko: '취소됨', en: 'cancelled' },
  'req.filter.all':       { ko: '전체',   en: 'All' },
  'req.filter.waiting':   { ko: '대기',   en: 'Waiting' },
  'req.filter.working':   { ko: '진행중', en: 'In progress' },
  'req.filter.done':      { ko: '완료',   en: 'Done' },
  'req.filter.cancelled': { ko: '취소',   en: 'Cancelled' },
  'req.cancel':           { ko: '취소',   en: 'Cancel' },
  'req.cancelling':       { ko: '취소중…', en: 'Cancelling…' },
  'req.confirm_cancel':   { ko: '이 요구사항을 취소하시겠습니까?', en: 'Cancel this requirement?' },
  'req.detail.close':     { ko: '닫기', en: 'Close' },

  // Backlog
  'bk.empty': { ko: '백로그가 비어있습니다. Claude Code 가 돌면서 채워집니다.', en: 'Backlog is empty. It fills up as Claude Code runs.' },
  'bk.hint':  {
    ko: '팀 lead 들이 승인한 예정 작업 목록입니다. 상위일수록 우선순위가 높습니다.',
    en: 'Upcoming work approved by team leads. Top = higher priority.',
  },
  'bk.col.title':    { ko: '제목',     en: 'Title' },
  'bk.col.team':     { ko: '팀',       en: 'Team' },
  'bk.col.priority': { ko: '우선순위', en: 'Priority' },
  'bk.col.estimate': { ko: '추정',     en: 'Est.' },
  'bk.col.status':   { ko: '상태',     en: 'Status' },

  // Evolution → renamed "감사" (Audit). Auditor agent reviews whether
  // the team structure and active project still align with the mission
  // philosophy / goals and proposes changes (add/retire agents, refactor
  // teams, etc.) for the human to accept or reject.
  'evo.title':   { ko: '감사 제안', en: 'Audit proposals' },
  'evo.hint':    {
    ko: '감사원이 현재 조직 구조와 진행 중인 프로젝트가 사훈(철학·목표)에 맞는지 점검하고, 새 에이전트 추가·정리·리팩터링 등을 제안합니다. 당신은 수락/거절만 결정합니다.',
    en: 'The auditor reviews whether the current team structure and project still match the mission philosophy/goals and proposes changes (new/retired agents, refactors). You just accept or reject.',
  },
  'evo.empty':   { ko: '아직 감사 제안이 없습니다. 프로젝트가 충분히 진행되면 감사원이 자동으로 분석합니다.', en: 'No audit proposals yet. The auditor analyzes after the project has enough history.' },
  'evo.accept':  { ko: '수락',   en: 'Accept' },
  'evo.reject':  { ko: '거절',   en: 'Reject' },
  'evo.accepted':{ ko: '✓ 수락됨', en: '✓ accepted' },
  'evo.rejected':{ ko: '✕ 거절됨', en: '✕ rejected' },
  'evo.rationale': { ko: '근거', en: 'Rationale' },
  'evo.kind.new_agent':   { ko: '새 에이전트',   en: 'New agent' },
  'evo.kind.feature':     { ko: '기능 추가',     en: 'New feature' },
  'evo.kind.refactor':    { ko: '리팩터링',      en: 'Refactor' },
  'evo.kind.retire_agent':{ ko: '에이전트 정리', en: 'Retire agent' },
  'evo.kind.split_agent': { ko: '에이전트 분할', en: 'Split agent' },
  'evo.kind.parallelize': { ko: '병렬화',         en: 'Parallelize' },
  'evo.knowledge_tab':    { ko: '누적 지식', en: 'Knowledge base' },

  // Auto-audit section
  'audit.section_title': { ko: '🔎 자동 감사 (Auto audit)', en: '🔎 Auto audit' },
  'audit.progress': {
    ko: '{done}번째 코디네이터 완료 · 매 {every}회마다 감사 · 다음 감사: {next}번째 완료 시',
    en: '{done} coordinators completed · audit every {every} · next audit at {next}th',
  },
  'audit.run_now':  { ko: '🔎 지금 감사 실행', en: '🔎 Run audit now' },
  'audit.running':  { ko: '감사 실행 중…', en: 'Auditing…' },
  'audit.loading':  { ko: '감사 상태 불러오는 중…', en: 'Loading audit status…' },
  'audit.unknown':  { ko: '감사 상태 정보 없음', en: 'No audit status available' },
  'audit.origin_badge': { ko: '🔎 감사', en: '🔎 audit' },
  'audit.hud_chip': { ko: '🔎 감사', en: '🔎 audit' },

  // Legend (team labels). Post-slim the active teams are top / dev /
  // eval only; leads / mgmt / domain kept for backcompat but typically
  // won't render (backend filters empty rooms out of /api/topology).
  'team.top':        { ko: '총괄 (HQ)',    en: 'HQ' },
  'team.leads':      { ko: '팀 리드',       en: 'Team Leads' },
  'team.dev':        { ko: '개발',          en: 'Dev' },
  'team.domain':     { ko: '도메인 전문',   en: 'Domain Specialists' },
  'team.mgmt':       { ko: '경영지원팀',    en: 'Management Support' },
  'team.eval':       { ko: '리뷰어',        en: 'Reviewers' },
  'team.knowledge':  { ko: '지식 자료',     en: 'Knowledge' },
  'team.canteen':    { ko: '탕비실 · 도구', en: 'Canteen · Tools' },

  // AgentPanel
  'panel.click_hint':    { ko: '캐릭터를 클릭하면 정보가 여기 표시됩니다.', en: 'Click a character to see its info here.' },
  'panel.tools':         { ko: '도구', en: 'Tools' },
  'panel.system_prompt': { ko: '시스템 프롬프트', en: 'System prompt' },
  'panel.model':         { ko: '모델', en: 'model' },
  'panel.team':          { ko: '팀', en: 'team' },

  // Loading / errors
  'loading.app':   { ko: 'OMNIHARNESS 로딩 중…', en: 'LOADING OMNIHARNESS…' },
  'loading.error': { ko: '오류', en: 'ERROR' },

  // Org chart (drill-down tab)
  'org.title':            { ko: '조직도', en: 'Organization' },
  'org.back_to_teams':    { ko: '팀 목록으로', en: 'Back to teams' },
  'org.back_to_team':     { ko: '팀으로', en: 'Back to team' },
  'org.team_working':     { ko: '작업중', en: 'working' },
  'org.no_members':       { ko: '팀원이 없습니다.', en: 'No members.' },
  'org.tools':            { ko: '도구', en: 'Tools' },
  'org.system_prompt':    { ko: '시스템 프롬프트', en: 'System prompt' },
  'org.description_heading': { ko: '역할 설명', en: 'Role description' },

  // MCP / Canteen
  'mcp.title':     { ko: 'MCP 도구', en: 'MCP Tool' },
  'mcp.close':     { ko: '닫기', en: 'Close' },
  'mcp.not_found': { ko: '이 도구의 설명이 아직 없습니다.', en: 'No description available for this tool.' },
  'canteen.mcp_label':    { ko: 'MCP · 외부 가전', en: 'MCP · External appliances' },
  'canteen.skill_label':  { ko: '스킬 · 레시피북',  en: 'Skills · Recipe books' },
  'canteen.mcp_desc':     {
    ko: '외부 프로세스가 제공하는 실행 가능한 도구. 파일 읽기·쓰기, GitHub, DB, 브라우저 등 실제 동작을 수행합니다.',
    en: 'Executable tools from external processes — file I/O, GitHub, DB, browsers. They actually do things.',
  },
  'canteen.skill_desc':   {
    ko: '에이전트가 참조하는 절차/지식 문서. 실행은 에이전트가 하고, 스킬은 "어떻게" 를 알려줍니다.',
    en: 'Procedures and knowledge docs the agent references. The agent executes; the skill tells it how.',
  },

  // Zoom
  'zoom.in':    { ko: '확대', en: 'Zoom in' },
  'zoom.out':   { ko: '축소', en: 'Zoom out' },
  'zoom.reset': { ko: '원래 크기', en: 'Reset zoom' },
  'zoom.help':  {
    ko: '🖱️ 좌클릭+드래그 = 영역 확대 · 역방향 드래그 = 축소 · Shift+드래그 = 이동',
    en: '🖱️ left-drag = zoom into area · reverse-drag = zoom out · Shift+drag = pan',
  },

  // Guide (Bedrock)
  'guide.button':        { ko: '가이드', en: 'GUIDE' },
  'guide.loading':       { ko: '가이드 불러오는 중…', en: 'Loading guide…' },
  'guide.official_docs': { ko: '공식 문서 보기', en: 'Official docs' },

  // Provider Keys (HUD 🔑 button → modal)
  'keys.button':  { ko: '키', en: 'KEYS' },
  'keys.title':   { ko: 'LLM Provider API 키', en: 'LLM Provider API keys' },
  'keys.hint':    {
    ko: '환경변수(.env/shell export) 대신 여기서 직접 붙여넣을 수 있습니다. 저장 즉시 적용 · 재기동에도 보존(state.json). 빈 값으로 저장하면 삭제.',
    en: 'Paste keys here instead of setting env vars (.env/shell export). Applied immediately and persisted to state.json across restarts. Empty value clears the slot.',
  },
  'keys.paste':   { ko: '키 붙여넣기', en: 'Paste key' },
  'keys.replace': { ko: '새 값 붙여넣어 덮어쓰기', en: 'Paste to replace' },
  'keys.save':    { ko: '저장', en: 'Save' },
  'keys.reload':  { ko: '다시 불러오기', en: 'Reload' },
  'keys.saved':   { ko: '저장됨 · 즉시 적용', en: 'Saved · applied live' },
  'keys.cleared': { ko: '삭제됨', en: 'Cleared' },

  // Mode select (first-visit)
  'mode.hello':         { ko: '어떻게 시작할까요?', en: 'How would you like to start?' },
  'mode.general':       { ko: '제너럴 뷰어', en: 'General viewer' },
  'mode.general_desc':  {
    ko: '프로젝트 없이 현재 폴더에서 Claude Code 가 내부적으로 에이전트/서브에이전트 · 툴 · 스킬을 어떻게 쓰는지 트리로 시각화합니다.',
    en: 'No project. Just watch how Claude Code traces through agents · subagents · tools · skills inside the current directory.',
  },
  'mode.general_hint':  { ko: '실험 · 탐색 · 이해용', en: 'Exploration · experimenting · teaching' },
  'mode.custom':        { ko: '커스텀 프로젝트', en: 'Custom project' },
  'mode.custom_desc':   {
    ko: '사훈 · 팀 · 에이전트를 설정한 전용 프로젝트에서 Claude Code 를 돌립니다. 사무실 오피스에서 각 에이전트가 책상에 앉아 작업합니다.',
    en: 'Run Claude Code inside a dedicated project with a mission, a team, and named agents. Characters sit at desks in an office.',
  },
  'mode.custom_hint':   { ko: '실전 개발 · 운영용', en: 'Actual development · shipping' },

  // Project list
  'plist.title':           { ko: '프로젝트 선택 또는 신규 생성', en: 'Pick a project or start a new one' },
  'plist.sub':             {
    ko: '기존 프로젝트를 클릭하면 그 팀 구성으로 바로 들어가고, 신규 생성을 누르면 사훈/팀을 새로 셋업합니다.',
    en: 'Click an existing project to load its team, or press New to set up a fresh mission.',
  },
  'plist.new_title':       { ko: '새 프로젝트 만들기', en: 'Create a new project' },
  'plist.new_sub':         {
    ko: '회사명 · 업종 · 목표만 적으면 오케스트레이터가 맞춤 팀을 제안합니다.',
    en: 'Just enter the company / industry / goal — the orchestrator will propose a custom team.',
  },
  'plist.status.ready':    { ko: '✓ 준비됨', en: '✓ ready' },
  'plist.status.setup':    { ko: '⚙ 팀 설정 필요', en: '⚙ needs team setup' },
  'plist.back_to_mode':    { ko: '모드 선택으로', en: 'Back to mode select' },
  'plist.back_to_list':    { ko: '프로젝트 목록으로', en: 'Back to list' },
  'plist.create':          { ko: '프로젝트 생성', en: 'Create project' },
  'plist.delete':          { ko: '삭제', en: 'Delete' },
  'plist.confirm_delete':  { ko: "'{name}' 프로젝트를 삭제하시겠습니까? 되돌릴 수 없습니다.", en: "Delete project '{name}'? This cannot be undone." },

  // General mode (trace viewer)
  'gen.title':      { ko: '제너럴 모드 — Claude Code 흐름 뷰어', en: 'General mode — Claude Code flow viewer' },
  'gen.hint':       {
    ko: '프로젝트 팀 구성 없이, Claude Code 가 질문 하나를 처리하면서 호출하는 서브에이전트 · 도구 · 스킬 흐름을 보여줍니다. 기본적으로 메인 Claude 1개가 답하고, Task/Agent 툴을 쓰거나 로컬 `.claude/agents/` 가 있을 때만 가지가 생깁니다.',
    en: 'No project team. Just shows how Claude Code traces a single query — what subagents, tools, and skills it touches. By default, one main Claude answers; branches only form when the Task/Agent tool runs or local `.claude/agents/` is present.',
  },
  'gen.main_label': { ko: '메인 Claude', en: 'Main Claude' },
  'gen.main_desc':  {
    ko: '기본 동작에서는 메인 Claude 1개가 모든 툴 호출 (Read · Edit · Bash 등) 을 직접 수행하고 답변합니다. 가지가 없다면 단일 노드가 정상입니다.',
    en: 'By default, a single main Claude executes all tool calls (Read · Edit · Bash, etc.) and answers. No branches = expected.',
  },
  'gen.trace_empty': { ko: '아직 추적된 호출이 없습니다. Claude Code 가 돌면 여기에 가지가 자랍니다.', en: 'No traced calls yet. Branches grow here as Claude Code runs.' },
  'gen.count_suffix': { ko: '회 호출', en: 'calls' },
  'gen.demo_on':      { ko: '▶ 데모', en: '▶ Demo' },
  'gen.demo_off':     { ko: '■ 데모 중지', en: '■ Stop demo' },
  'gen.demo_hint':    { ko: '시뮬레이션만 화면에 보여집니다 — 실제 백엔드 호출 / 비용 누적 없음', en: 'Demo is fully client-side — no backend calls, no cost accrual.' },

  // Agent display names (human-readable labels) — generic, project-agnostic
  'agent.orchestrator':      { ko: '총괄',             en: 'orchestrator' },
  'agent.dev-lead':          { ko: '개발 리드',         en: 'dev-lead' },
  'agent.mgmt-lead':         { ko: '경영지원 리드',     en: 'mgmt-lead' },
  'agent.eval-lead':         { ko: '평가 리드',         en: 'eval-lead' },
  'agent.dev-dashboard':     { ko: '대시보드 개발',     en: 'dev-dashboard' },
  'agent.dev-spc':           { ko: '공정통계 (SPC) 개발', en: 'dev-spc' },
  'agent.dev-wafer-map':     { ko: '웨이퍼맵 개발',     en: 'dev-wafer-map' },
  'agent.dev-ml':            { ko: 'ML 분석 개발',      en: 'dev-ml' },
  'agent.dev-ettime':        { ko: '시간 분석 개발',    en: 'dev-ettime' },
  'agent.dev-tablemap':      { ko: '테이블맵 개발',     en: 'dev-tablemap' },
  'agent.dev-tracker':       { ko: '트래커 개발',       en: 'dev-tracker' },
  'agent.dev-filebrowser':   { ko: '파일 브라우저 개발', en: 'dev-filebrowser' },
  'agent.dev-admin':         { ko: 'Admin 개발',         en: 'dev-admin' },
  'agent.dev-messages':      { ko: '메시지 개발',       en: 'dev-messages' },
  'agent.process-tagger':    { ko: '공정 태거',         en: 'process-tagger' },
  'agent.causal-analyst':    { ko: '인과 분석가',       en: 'causal-analyst' },
  'agent.dvc-curator':       { ko: 'DVC 큐레이터',      en: 'dvc-curator' },
  'agent.adapter-engineer':  { ko: '어댑터 엔지니어',   en: 'adapter-engineer' },
  'agent.reporter':          { ko: '보고원',            en: 'reporter' },
  'agent.hr':                { ko: '인사원',            en: 'hr' },
  'agent.auditor':           { ko: '감사원',            en: 'auditor' },
  'agent.ux-reviewer':       { ko: 'UX 리뷰어',         en: 'ux-reviewer' },
  'agent.dev-verifier':      { ko: '개발 검증',          en: 'dev-verifier' },
  'agent.user-role-tester':  { ko: '유저 테스터',        en: 'user-role-tester' },
  'agent.admin-role-tester': { ko: '관리자 테스터',      en: 'admin-role-tester' },
  'agent.security-auditor':  { ko: '보안 감사',          en: 'security-auditor' },
  'agent.domain-researcher': { ko: '도메인 리서치',       en: 'domain-researcher' },
};

export function t(key, lang = DEFAULT_LANG) {
  const useLang = lang === 'ko' || lang === 'en' ? lang : DEFAULT_LANG;
  const entry = TRANSLATIONS[key];
  if (!entry) return key;
  return entry[useLang] || entry[DEFAULT_LANG] || key;
}

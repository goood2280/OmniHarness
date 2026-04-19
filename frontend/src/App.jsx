import { useEffect, useRef, useState } from 'react';
import OfficeScene from './OfficeScene';
import ProjectList from './ProjectList';
import Tutorial from './Tutorial';
import HUD from './HUD';
import AgentPanel from './AgentPanel';
import MissionBanner from './MissionBanner';
import Onboarding from './Onboarding';
import TabPanel from './TabPanel';
import McpPanel from './McpPanel';
import BedrockGuide from './BedrockGuide';
import ChatDock from './ChatDock';
import { t, DEFAULT_LANG } from './i18n';

const POLL_FAST_MS = 1500;
const POLL_SLOW_MS = 4000;
const LANG_KEY = 'omni.lang';

export default function App() {
  const [mode, setMode] = useState(null);          // null | 'general' | 'custom'
  const [modeLoading, setModeLoading] = useState(true);
  const [activeProject, setActiveProject] = useState(''); // slug

  const [topology, setTopology] = useState(null);
  const [activity, setActivity] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [reports, setReports] = useState([]);
  const [requirements, setRequirements] = useState([]);
  const [backlog, setBacklog] = useState([]);
  const [evolution, setEvolution] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [org, setOrg] = useState(null);
  const [mcps, setMcps] = useState([]);
  const [skills, setSkills] = useState([]);
  const [mission, setMission] = useState(null);
  const [selected, setSelected] = useState(null);
  const [selectedMcp, setSelectedMcp] = useState(null);
  const [guideOpen, setGuideOpen] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [err, setErr] = useState(null);
  const [lang, setLang] = useState(() => {
    try { return localStorage.getItem(LANG_KEY) || DEFAULT_LANG; }
    catch { return DEFAULT_LANG; }
  });

  const fastRef = useRef();
  const slowRef = useRef();

  useEffect(() => {
    try { localStorage.setItem(LANG_KEY, lang); } catch { /* ignore */ }
  }, [lang]);

  // Boot: force custom mode + resolve active project.
  // General mode is hidden — the project owner decided to focus custom.
  useEffect(() => {
    (async () => {
      try {
        const [mResp, p] = await Promise.all([
          fetch('/api/mode').then((r) => r.json()),
          fetch('/api/projects').then((r) => r.json()),
        ]);
        if (mResp.mode !== 'custom') {
          await fetch('/api/mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'custom' }),
          }).catch(() => {});
        }
        setMode('custom');
        setActiveProject(p.active || '');
      } finally {
        setModeLoading(false);
      }
    })();
  }, []);

  // Fast polling for topology (only when we have a reason to show it)
  useEffect(() => {
    if (!mode) return;
    let alive = true;
    const load = () =>
      fetch('/api/topology')
        .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
        .then((d) => {
          if (!alive) return;
          setTopology(d);
          setSelected((cur) =>
            cur ? d.agents.find((a) => a.name === cur.name) || cur : null
          );
        })
        .catch((e) => alive && setErr(String(e)));
    load();
    fastRef.current = setInterval(load, POLL_FAST_MS);
    return () => { alive = false; clearInterval(fastRef.current); };
  }, [mode, activeProject]);

  useEffect(() => {
    if (!mode) return;
    let alive = true;
    const loadAll = () => {
      fetch('/api/activity?limit=120').then((r) => r.json())
        .then((d) => alive && setActivity(d.events || []));
      fetch('/api/questions').then((r) => r.json())
        .then((d) => alive && setQuestions(d.questions || []));
      fetch('/api/reports').then((r) => r.json())
        .then((d) => alive && setReports(d.reports || []));
      fetch('/api/requirements').then((r) => r.ok ? r.json() : {})
        .then((d) => alive && setRequirements(d.requirements || d.items || []));
      fetch('/api/backlog').then((r) => r.ok ? r.json() : {})
        .then((d) => alive && setBacklog(d.items || d.backlog || []));
      fetch('/api/evolution').then((r) => r.ok ? r.json() : {})
        .then((d) => alive && setEvolution(d.items || []));
      fetch('/api/knowledge').then((r) => r.ok ? r.json() : {})
        .then((d) => alive && setKnowledge(d.items || []));
    };
    loadAll();
    slowRef.current = setInterval(loadAll, POLL_SLOW_MS);
    return () => { alive = false; clearInterval(slowRef.current); };
  }, [mode, activeProject]);

  useEffect(() => {
    if (!mode) return;
    fetch('/api/mission').then((r) => r.json()).then(setMission);
    fetch('/api/org').then((r) => r.ok ? r.json() : null).then(setOrg);
    fetch('/api/mcps').then((r) => r.ok ? r.json() : null)
      .then((d) => setMcps((d && (d.mcps || d.items)) || []));
    fetch('/api/skills').then((r) => r.ok ? r.json() : null)
      .then((d) => setSkills((d && (d.skills || d.items)) || []));
  }, [mode, activeProject]);

  const reloadQuestions = () =>
    fetch('/api/questions').then((r) => r.json())
      .then((d) => setQuestions(d.questions || []));
  const reloadReports = () =>
    fetch('/api/reports').then((r) => r.json())
      .then((d) => setReports(d.reports || []));
  const reloadRequirements = () =>
    fetch('/api/requirements').then((r) => r.json())
      .then((d) => setRequirements(d.requirements || d.items || []));
  const reloadEvolution = () =>
    fetch('/api/evolution').then((r) => r.json())
      .then((d) => setEvolution(d.items || []));

  const chooseMode = async (m, { resetProject = false } = {}) => {
    await fetch('/api/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: m }),
    });
    setMode(m);
    if (resetProject) setActiveProject('');
  };

  const exitToModeSelect = async () => {
    // Go back to the initial mode select screen.
    await fetch('/api/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: '' }),
    }).catch(() => {});
    setMode(null);
    setActiveProject('');
  };

  const openProject = async (slug) => {
    setActiveProject(slug);
    // Reset mission so the subsequent poll picks up the new project
    setMission(null);
    const m = await fetch('/api/mission').then((r) => r.json());
    setMission(m);
  };

  if (modeLoading) return <div className="loading">{t('loading.app', lang)}</div>;
  if (err) return <div className="loading">{t('loading.error', lang)}: {err}</div>;

  // ─── No active project → straight to list/create. General mode is
  //     disabled, so there's no "back to mode select" step.
  if (!activeProject) {
    return <ProjectList onOpen={openProject} onBack={null} lang={lang} setLang={setLang} />;
  }

  // After this point we need topology + mission loaded at least once.
  if (!topology || (mode === 'custom' && !mission)) {
    return <div className="loading">{t('loading.app', lang)}</div>;
  }

  const needsOnboarding =
    mode === 'custom' && activeProject &&
    (!mission || mission.placeholder || !mission.team_confirmed);

  if (needsOnboarding) {
    return <Onboarding mission={mission || {}} onSave={setMission} lang={lang} />;
  }

  const opus = topology.agents.filter((a) => a.model === 'opus').length;
  const sonnet = topology.agents.filter((a) => a.model === 'sonnet').length;
  const haiku = topology.agents.filter((a) => a.model === 'haiku').length;
  const working = topology.agents.filter((a) => a.state === 'working').length;
  const waiting = topology.agents.filter((a) => a.state === 'waiting').length;
  const idle = topology.agents.filter((a) => a.state === 'idle').length;

  const panelOpen = !!(selected || selectedMcp);

  return (
    <div className={`app${panelOpen ? ' app--panel-open' : ''}`}>
      {mode === 'custom' && mission && (
        <MissionBanner mission={mission} onEdit={() => setWizardOpen(true)} lang={lang} />
      )}
      <HUD
        agentCount={topology.total}
        opus={opus}
        sonnet={sonnet}
        haiku={haiku}
        working={working}
        waiting={waiting}
        idle={idle}
        cost={topology.cost_total}
        lang={lang}
        onLangChange={setLang}
        onGuideOpen={() => setGuideOpen(true)}
        mode={mode}
        onModeChange={async (m) => {
          await chooseMode(m);
          if (m === 'custom' && !activeProject) setActiveProject('');
        }}
        onSwitchProject={() => setActiveProject('')}
        hasActiveProject={!!activeProject && mode === 'custom'}
      />
      <OfficeScene
        topology={topology}
        onSelect={(a) => { setSelectedMcp(null); setSelected(a); }}
        selected={selected}
        lang={lang}
        mcps={mcps}
        skills={skills}
        backlog={backlog}
        reports={reports}
        activity={activity}
        onSelectMcp={(m) => { setSelected(null); setSelectedMcp(m); }}
        onSelectSkill={(m) => { setSelected(null); setSelectedMcp(m); }}
      />

      <TabPanel
        topology={topology}
        activity={activity}
        questions={questions}
        reports={reports}
        requirements={requirements}
        backlog={backlog}
        evolution={evolution}
        knowledge={knowledge}
        org={org}
        onReloadQuestions={reloadQuestions}
        onReloadReports={reloadReports}
        onReloadRequirements={reloadRequirements}
        onReloadEvolution={reloadEvolution}
        lang={lang}
        mode={mode}
      />
      <AgentPanel agent={selected} onClose={() => setSelected(null)} lang={lang} mode={mode} costByModel={topology.cost_by_model} />
      <McpPanel mcp={selectedMcp} onClose={() => setSelectedMcp(null)} lang={lang} />
      <BedrockGuide open={guideOpen} onClose={() => setGuideOpen(false)} lang={lang} />
      <Tutorial lang={lang} setLang={setLang} onDone={() => {}} />
      {wizardOpen && mission && (
        <Onboarding
          mission={{ ...mission, team_confirmed: false }}
          onSave={(m) => { setMission(m); setWizardOpen(false); }}
          onClose={() => setWizardOpen(false)}
          lang={lang}
        />
      )}
    </div>
  );
}

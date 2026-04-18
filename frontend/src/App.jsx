import { useEffect, useRef, useState } from 'react';
import OrgTree from './OrgTree';
import HUD from './HUD';
import AgentPanel from './AgentPanel';
import MissionBanner from './MissionBanner';
import TabPanel from './TabPanel';
import McpPanel from './McpPanel';
import BedrockGuide from './BedrockGuide';
import { t, DEFAULT_LANG } from './i18n';

const POLL_FAST_MS = 1500;
const POLL_SLOW_MS = 4000;
const LANG_KEY = 'omni.lang';

export default function App() {
  const [topology, setTopology] = useState(null);
  const [activity, setActivity] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [reports, setReports] = useState([]);
  const [requirements, setRequirements] = useState([]);
  const [backlog, setBacklog] = useState([]);
  const [org, setOrg] = useState(null);
  const [mcps, setMcps] = useState([]);
  const [mission, setMission] = useState(null);
  const [selected, setSelected] = useState(null);
  const [selectedMcp, setSelectedMcp] = useState(null);
  const [guideOpen, setGuideOpen] = useState(false);
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

  useEffect(() => {
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
  }, []);

  useEffect(() => {
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
    };
    loadAll();
    slowRef.current = setInterval(loadAll, POLL_SLOW_MS);
    return () => { alive = false; clearInterval(slowRef.current); };
  }, []);

  useEffect(() => {
    fetch('/api/mission').then((r) => r.json()).then(setMission);
    fetch('/api/org').then((r) => r.ok ? r.json() : null).then(setOrg);
    fetch('/api/mcps').then((r) => r.ok ? r.json() : null)
      .then((d) => setMcps((d && (d.mcps || d.items)) || []));
  }, []);

  const reloadQuestions = () =>
    fetch('/api/questions').then((r) => r.json())
      .then((d) => setQuestions(d.questions || []));
  const reloadReports = () =>
    fetch('/api/reports').then((r) => r.json())
      .then((d) => setReports(d.reports || []));
  const reloadRequirements = () =>
    fetch('/api/requirements').then((r) => r.json())
      .then((d) => setRequirements(d.requirements || d.items || []));

  if (err) return <div className="loading">{t('loading.error', lang)}: {err}</div>;
  if (!topology || !mission) return <div className="loading">{t('loading.app', lang)}</div>;

  const opus = topology.agents.filter((a) => a.model === 'opus').length;
  const sonnet = topology.agents.filter((a) => a.model === 'sonnet').length;
  const haiku = topology.agents.filter((a) => a.model === 'haiku').length;
  const working = topology.agents.filter((a) => a.state === 'working').length;
  const waiting = topology.agents.filter((a) => a.state === 'waiting').length;
  const idle = topology.agents.filter((a) => a.state === 'idle').length;

  return (
    <div className="app">
      <MissionBanner mission={mission} onSave={setMission} lang={lang} />
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
      />
      {working === 0 && (
        <div className="awaiting-bar">
          <span className="awaiting-title">{t('awaiting.title', lang)}</span>
          <span className="awaiting-body">
            {mission.company || 'FabCanvas'} 생성을 위하여 Claude Code 가 돌아가면 거기에 맞는 에이전트들이 활성화됩니다.
          </span>
        </div>
      )}
      <OrgTree
        topology={topology}
        org={org}
        onSelect={setSelected}
        selected={selected}
        lang={lang}
        mission={mission}
      />
      <TabPanel
        topology={topology}
        activity={activity}
        questions={questions}
        reports={reports}
        requirements={requirements}
        backlog={backlog}
        org={org}
        onReloadQuestions={reloadQuestions}
        onReloadReports={reloadReports}
        onReloadRequirements={reloadRequirements}
        lang={lang}
      />
      <AgentPanel agent={selected} onClose={() => setSelected(null)} lang={lang} />
      <McpPanel mcp={selectedMcp} onClose={() => setSelectedMcp(null)} lang={lang} />
      <BedrockGuide open={guideOpen} onClose={() => setGuideOpen(false)} lang={lang} />
    </div>
  );
}

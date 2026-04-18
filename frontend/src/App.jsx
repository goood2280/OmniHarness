import { useEffect, useRef, useState } from 'react';
import PixelOffice from './PixelOffice';
import HUD from './HUD';
import AgentPanel from './AgentPanel';
import MissionBanner from './MissionBanner';
import TabPanel from './TabPanel';

const POLL_FAST_MS = 1500;
const POLL_SLOW_MS = 4000;

export default function App() {
  const [topology, setTopology] = useState(null);
  const [activity, setActivity] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [reports, setReports] = useState([]);
  const [mission, setMission] = useState(null);
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState(null);

  const fastRef = useRef();
  const slowRef = useRef();

  // Fast poll: topology (agent states + counters)
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
    return () => {
      alive = false;
      clearInterval(fastRef.current);
    };
  }, []);

  // Slow poll: activity + questions + reports
  useEffect(() => {
    let alive = true;
    const loadAll = () => {
      fetch('/api/activity?limit=120').then((r) => r.json())
        .then((d) => alive && setActivity(d.events || []));
      fetch('/api/questions').then((r) => r.json())
        .then((d) => alive && setQuestions(d.questions || []));
      fetch('/api/reports').then((r) => r.json())
        .then((d) => alive && setReports(d.reports || []));
    };
    loadAll();
    slowRef.current = setInterval(loadAll, POLL_SLOW_MS);
    return () => {
      alive = false;
      clearInterval(slowRef.current);
    };
  }, []);

  // Mission: initial load
  useEffect(() => {
    fetch('/api/mission').then((r) => r.json()).then(setMission);
  }, []);

  const reloadQuestions = () => {
    fetch('/api/questions').then((r) => r.json())
      .then((d) => setQuestions(d.questions || []));
  };
  const reloadReports = () => {
    fetch('/api/reports').then((r) => r.json())
      .then((d) => setReports(d.reports || []));
  };

  const toggleDemo = async (enabled) => {
    await fetch('/api/demo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    });
  };

  if (err) return <div className="loading">ERROR: {err}</div>;
  if (!topology || !mission) return <div className="loading">LOADING OMNIHARNESS...</div>;

  const opus = topology.agents.filter((a) => a.model === 'opus').length;
  const sonnet = topology.agents.filter((a) => a.model === 'sonnet').length;
  const haiku = topology.agents.filter((a) => a.model === 'haiku').length;
  const working = topology.agents.filter((a) => a.state === 'working').length;
  const waiting = topology.agents.filter((a) => a.state === 'waiting').length;
  const idle = topology.agents.filter((a) => a.state === 'idle').length;
  const morale = Math.round(
    ((opus * 100 + sonnet * 85 + haiku * 70) / Math.max(topology.total, 1)) || 0
  );

  return (
    <div className="app">
      <MissionBanner mission={mission} onSave={setMission} />
      <HUD
        agentCount={topology.total}
        morale={morale}
        opus={opus}
        sonnet={sonnet}
        haiku={haiku}
        working={working}
        waiting={waiting}
        idle={idle}
        demo={topology.demo}
        cost={topology.cost_total}
        onToggleDemo={toggleDemo}
      />
      {!topology.demo && working === 0 && (
        <div className="awaiting-bar">
          실제 작업 대기 중 — FabCanvas.ai 에서 Claude Code 로 작업을 시작하면
          해당 에이전트들이 활성화됩니다.
          <span className="muted"> (또는 우측 <b>DEMO</b> 버튼으로 시뮬레이션 확인)</span>
        </div>
      )}
      <PixelOffice topology={topology} onSelect={setSelected} selected={selected} />
      <Legend teams={topology.teams} agents={topology.agents} />
      <TabPanel
        topology={topology}
        activity={activity}
        questions={questions}
        reports={reports}
        onReloadQuestions={reloadQuestions}
        onReloadReports={reloadReports}
      />
      <AgentPanel agent={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function Legend({ teams, agents }) {
  const byTeam = (id) => agents.filter((a) => a.team === id);
  return (
    <div className="legend">
      {teams.map((t) => {
        const members = byTeam(t.id);
        const working = members.filter((a) => a.state === 'working').length;
        return (
          <div key={t.id} className="legend-team">
            <span className="legend-title">{t.label}</span>
            <span className="legend-stats">
              <span className="legend-count">{members.length}</span>
              {working > 0 && <span className="legend-working">⚡{working}</span>}
            </span>
          </div>
        );
      })}
    </div>
  );
}

import { useState } from 'react';
import Sprite, { POSE } from './Sprite';
import { t } from './i18n';

// IDLE (seated at desk) pose works as a clean head-and-shoulders
// thumbnail for every sheet — Nano Banana sometimes draws the
// off-desk poses (waving / walking) extending past the panel edge,
// which crops weirdly when downsized to a 56-px square.
function poseFor(agent) {
  if (agent?.state === 'working') return agent.model === 'opus' ? POSE.WORK_OPUS : POSE.WORK_SONNET;
  return POSE.IDLE;
}

function stateLabel(state, lang) {
  if (state === 'working') return t('hud.work', lang);
  if (state === 'waiting') return t('hud.wait', lang);
  return t('hud.idle', lang);
}

function deriveHierarchy(topology) {
  const agents = (topology && topology.agents) || [];
  const teams = (topology && topology.teams) || [];
  // topology.teams items look like {id, label, members:[...]}
  return teams.map((team) => ({
    id: team.id,
    label_ko: team.label || null,
    label_en: null,
    members:
      Array.isArray(team.members) && team.members.length
        ? team.members
        : agents.filter((a) => a.team === team.id).map((a) => a.name),
  }));
}

export default function OrgChart({ topology, org, lang }) {
  const [view, setView] = useState('teams');
  const [selectedTeamId, setSelectedTeamId] = useState(null);
  const [selectedAgentName, setSelectedAgentName] = useState(null);

  const agents = (topology && topology.agents) || [];
  const hierarchy =
    org && Array.isArray(org.hierarchy) && org.hierarchy.length > 0
      ? org.hierarchy
      : deriveHierarchy(topology);

  const agentByName = {};
  for (const a of agents) agentByName[a.name] = a;

  const teamLabel = (team) => {
    if (!team) return '';
    const fromI18n = t(`team.${team.id}`, lang);
    if (fromI18n && fromI18n !== `team.${team.id}`) return fromI18n;
    return lang === 'ko' ? team.label_ko || team.id : team.label_en || team.id;
  };

  const selectedTeam =
    selectedTeamId != null
      ? hierarchy.find((t) => t.id === selectedTeamId)
      : null;
  const selectedAgent =
    selectedAgentName != null ? agentByName[selectedAgentName] : null;

  const goTeams = () => {
    setView('teams');
    setSelectedTeamId(null);
    setSelectedAgentName(null);
  };
  const goTeam = (teamId) => {
    setSelectedTeamId(teamId);
    setSelectedAgentName(null);
    setView('team');
  };
  const goAgent = (name) => {
    setSelectedAgentName(name);
    setView('agent');
  };
  const backToTeam = () => {
    setSelectedAgentName(null);
    setView('team');
  };

  return (
    <div className="org">
      <div className="org-bar">
        {view === 'teams' && (
          <span className="org-crumb">{t('org.title', lang)}</span>
        )}
        {view === 'team' && selectedTeam && (
          <>
            <button className="org-back" onClick={goTeams}>
              ← {t('org.back_to_teams', lang)}
            </button>
            <span className="org-crumb">{teamLabel(selectedTeam)}</span>
          </>
        )}
        {view === 'agent' && selectedTeam && selectedAgent && (
          <>
            <button className="org-back" onClick={backToTeam}>
              ← {t('org.back_to_team', lang)}
            </button>
            <span className="org-crumb">
              {teamLabel(selectedTeam)} → {selectedAgent.name}
            </span>
          </>
        )}
      </div>

      {view === 'teams' && (
        <div className="org-teams-grid">
          {hierarchy.map((team) => {
            const members = (team.members || [])
              .map((n) => agentByName[n])
              .filter(Boolean);
            const total = members.length;
            const workingCount = members.filter(
              (m) => m.state === 'working'
            ).length;
            return (
              <button
                key={team.id}
                className="org-team-tile"
                onClick={() => goTeam(team.id)}
              >
                <div className="org-team-faces">
                  {members.slice(0, 4).map((m) => (
                    <div key={m.name} className="org-team-face">
                      <Sprite agent={m} pose={poseFor(m)} size={72} />
                    </div>
                  ))}
                  {members.length > 4 && (
                    <div className="org-team-face org-team-face-more">+{members.length - 4}</div>
                  )}
                </div>
                <div className="org-team-name">{teamLabel(team)}</div>
                <div className="org-team-count">{total}</div>
                {workingCount > 0 && (
                  <div className="org-team-working">
                    {t('org.team_working', lang)}: {workingCount}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}

      {view === 'team' && selectedTeam && (
        <div className="org-members">
          {(() => {
            const members = (selectedTeam.members || [])
              .map((n) => agentByName[n])
              .filter(Boolean);
            if (members.length === 0) {
              return <div>{t('org.no_members', lang)}</div>;
            }
            return members.map((agent) => {
              const st = agent.state || 'idle';
              const desc = (agent.description || '').slice(0, 80);
              const displayName = t(`agent.${agent.name}`, lang) || agent.name;
              return (
                <div
                  key={agent.name}
                  className={`org-member-card state-${st}`}
                  onClick={() => goAgent(agent.name)}
                >
                  <div className="org-member-sprite">
                    <Sprite agent={agent} pose={poseFor(agent)} size={110} />
                  </div>
                  <span className="org-member-name">{displayName}</span>
                  <span className={`pill pill-${agent.model}`}>
                    {agent.model}
                  </span>
                  <span className={`org-state-${st}`}>
                    {stateLabel(st, lang)}
                  </span>
                  <span className="org-member-desc">{desc}</span>
                </div>
              );
            });
          })()}
        </div>
      )}

      {view === 'agent' && selectedAgent && (
        <div className="org-agent-view">
          <div className="org-agent-head">
            <div className="org-member-sprite org-member-sprite-lg">
              <Sprite agent={selectedAgent} pose={poseFor(selectedAgent)} size={160} />
            </div>
            <span className="org-member-name">{t(`agent.${selectedAgent.name}`, lang) || selectedAgent.name}</span>
            <span className={`pill pill-${selectedAgent.model}`}>
              {selectedAgent.model}
            </span>
            {selectedTeam && (
              <span className="chip">{teamLabel(selectedTeam)}</span>
            )}
            <span className={`org-state-${selectedAgent.state || 'idle'}`}>
              {stateLabel(selectedAgent.state || 'idle', lang)}
            </span>
          </div>

          <div className="org-agent-body">
            <h3>{t('org.description_heading', lang)}</h3>
            <p>{selectedAgent.description}</p>

            <h3>{t('org.tools', lang)}</h3>
            <ul className="org-tools">
              {(selectedAgent.tools || []).map((tool) => (
                <li key={tool}>{tool}</li>
              ))}
            </ul>

            <details className="org-prompt">
              <summary>{t('org.system_prompt', lang)}</summary>
              <pre>{selectedAgent.body}</pre>
            </details>
          </div>
        </div>
      )}
    </div>
  );
}

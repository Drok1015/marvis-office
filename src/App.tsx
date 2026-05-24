import { useEffect, useMemo, useState } from 'react';
import './App.css';
import { PonyAvatar, type IdleVariant, type PetTheme } from './components/PonyAvatar';
import { TokenBar } from './components/TokenBar';
import { AGENT_DEFS, buildInitialAgents, type AgentState, type AgentStatus } from './data/agents';
import { useAgentEvents } from './hooks/useAgentEvents';

const PHASE_ONE_STATUSES: AgentStatus[] = ['idle', 'working', 'done'];
const IDLE_VARIANTS: IdleVariant[] = ['sleeping', 'coffee', 'workout', 'bathroom', 'wandering'];
const NON_PUBLIC_IDLE_VARIANTS: IdleVariant[] = ['sleeping', 'wandering'];
const MAX_PUBLIC_ZONE_OCCUPANCY = 2;
const PUBLIC_ZONE_Y_OFFSET = 2.2;

const DESK_SPOTS: Record<string, { x: number; y: number }> = {
  'main-agent': { x: 48, y: 20 },
  'file-agent': { x: 75, y: 20 },
  'computer-agent': { x: 48, y: 50 },
  'app-agent': { x: 75, y: 50 },
  'browser-agent': { x: 48, y: 80 },
  'search-agent': { x: 75, y: 80 },
};

const PUBLIC_SPOTS = {
  coffee: { x: 14, y: 19 },
  workout: { x: 14, y: 49 },
  bathroom: { x: 14, y: 79 },
};
type PublicZoneKey = keyof typeof PUBLIC_SPOTS;

const AGENT_PET_THEME: Record<string, PetTheme> = {
  'main-agent': 'panda',
  'file-agent': 'fox',
  'computer-agent': 'horse',
  'app-agent': 'rabbit',
  'browser-agent': 'dog',
  'search-agent': 'pig',
};

const ZONE_LAYOUT: Record<
  PublicZoneKey,
  {
    perRow: number;
    xGap: number;
    yGap: number;
  }
> = {
  coffee: { perRow: 2, xGap: 10.4, yGap: 6.8 },
  workout: { perRow: 2, xGap: 10.8, yGap: 6.9 },
  bathroom: { perRow: 2, xGap: 11.2, yGap: 7.1 },
};

type AvatarPosition = {
  x: number;
  y: number;
  idleVariant: IdleVariant;
};

function randomIdleVariant() {
  const idx = Math.floor(Math.random() * IDLE_VARIANTS.length);
  return IDLE_VARIANTS[idx];
}

function pickRandomVariant<T>(items: readonly T[]): T {
  const idx = Math.floor(Math.random() * items.length);
  return items[idx];
}

function isPublicZoneVariant(variant: IdleVariant): variant is PublicZoneKey {
  return variant === 'coffee' || variant === 'workout' || variant === 'bathroom';
}

function assignControlledIdleVariants(
  agents: AgentState[],
  source: Record<string, IdleVariant>,
  randomize = false,
): Record<string, IdleVariant> {
  const next: Record<string, IdleVariant> = { ...source };
  const counts: Record<PublicZoneKey, number> = { coffee: 0, workout: 0, bathroom: 0 };
  const idleAgents = agents.filter((agent) => agent.status === 'idle');
  const idleOrder = randomize ? [...idleAgents].sort(() => Math.random() - 0.5) : idleAgents;

  for (const agent of idleOrder) {
    const candidate = randomize ? randomIdleVariant() : (source[agent.name] ?? randomIdleVariant());
    if (isPublicZoneVariant(candidate)) {
      if (counts[candidate] < MAX_PUBLIC_ZONE_OCCUPANCY) {
        counts[candidate] += 1;
        next[agent.name] = candidate;
      } else {
        next[agent.name] = pickRandomVariant(NON_PUBLIC_IDLE_VARIANTS);
      }
      continue;
    }
    next[agent.name] = candidate;
  }

  for (const agent of agents) {
    if (agent.status !== 'idle' && !next[agent.name]) {
      next[agent.name] = source[agent.name] ?? randomIdleVariant();
    }
  }

  const changed = AGENT_DEFS.some((agent) => next[agent.name] !== source[agent.name]);
  return changed ? next : source;
}

function App() {
  const [manualAgents, setManualAgents] = useState<AgentState[]>(() => buildInitialAgents());
  const [userRequest, setUserRequest] = useState('请整理当前项目并给出后续开发建议');
  const [submitting, setSubmitting] = useState(false);
  const [banner, setBanner] = useState('');
  const [idleVariants, setIdleVariants] = useState<Record<string, IdleVariant>>(() =>
    Object.fromEntries(AGENT_DEFS.map((agent) => [agent.name, randomIdleVariant()])),
  );

  const { streamAgents, taskLog, totalTokens, connected, pendingConfirmation } = useAgentEvents();

  const liveAgents = useMemo(() => {
    if (streamAgents.size === 0) return manualAgents;
    return manualAgents.map((agent) => streamAgents.get(agent.name) ?? agent);
  }, [manualAgents, streamAgents]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setIdleVariants((prev) => assignControlledIdleVariants(liveAgents, prev, true));
    }, 18000);

    return () => window.clearInterval(timer);
  }, [liveAgents]);
  const controlledIdleVariants = useMemo(
    () => assignControlledIdleVariants(liveAgents, idleVariants, false),
    [liveAgents, idleVariants],
  );

  const cycleStatus = (targetName: string) => {
    setManualAgents((prev) =>
      prev.map((agent) => {
        if (agent.name !== targetName) return agent;

        const current = PHASE_ONE_STATUSES.indexOf(agent.status);
        const nextStatus = PHASE_ONE_STATUSES[(current + 1) % PHASE_ONE_STATUSES.length];
        const messageMap: Record<AgentStatus, string> = {
          idle: '等待新任务',
          dispatching: '正在分配任务',
          thinking: '正在分析任务',
          working: '处理任务中',
          done: '任务完成',
          error: '执行失败',
          paused: '等待确认',
        };

        return {
          ...agent,
          status: nextStatus,
          message: messageMap[nextStatus],
          progress: nextStatus === 'working' ? { current_step: 2, total_steps: 5, step_name: '执行中' } : undefined,
        };
      }),
    );
  };

  const resetManual = () => setManualAgents(buildInitialAgents());

  const startTask = async () => {
    if (!userRequest.trim()) {
      setBanner('请输入任务内容');
      return;
    }

    setSubmitting(true);
    setBanner('');
    try {
      const response = await fetch('/api/task/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_request: userRequest.trim() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || '启动失败');
      setBanner(`真实任务已启动: ${data.task_id ?? ''}`);
    } catch (error) {
      setBanner(error instanceof Error ? error.message : '任务启动失败');
    } finally {
      setSubmitting(false);
    }
  };

  const triggerSimulation = async () => {
    setSubmitting(true);
    setBanner('');
    try {
      const response = await fetch('/api/simulate/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_request: '模拟执行：分析项目并输出建议' }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || '启动失败');
      setBanner(`模拟任务已启动: ${data.task_id ?? ''}`);
    } catch (error) {
      setBanner(error instanceof Error ? error.message : '模拟任务启动失败');
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    const scopedWindow = window as Window & { __marvis_auto_sim_started__?: boolean };
    if (scopedWindow.__marvis_auto_sim_started__) return;
    scopedWindow.__marvis_auto_sim_started__ = true;

    const runInitialSimulation = async () => {
      setSubmitting(true);
      setBanner('');
      try {
        const response = await fetch('/api/simulate/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_request: '模拟执行：分析项目并输出建议' }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data?.detail || '启动失败');
        setBanner(`已自动启动模拟任务: ${data.task_id ?? ''}`);
      } catch (error) {
        setBanner(error instanceof Error ? error.message : '模拟任务启动失败');
      } finally {
        setSubmitting(false);
      }
    };

    void runInitialSimulation();
  }, []);

  const resolveConfirmation = async (approved: boolean) => {
    if (!pendingConfirmation) return;
    setSubmitting(true);
    try {
      await fetch('/api/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: pendingConfirmation.confirmationId, approved }),
      });
      setBanner(approved ? '已确认继续执行' : '已拒绝执行');
    } catch {
      setBanner('确认提交失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  const runningCount = liveAgents.filter((agent) => ['dispatching', 'thinking', 'working'].includes(agent.status)).length;
  const doneCount = liveAgents.filter((agent) => agent.status === 'done').length;
  const avatarPositions = useMemo(() => {
    const baseTargets: Record<string, { x: number; y: number; zone: string; idleVariant: IdleVariant }> = {};
    const publicZoneGroups: Record<PublicZoneKey, string[]> = {
      coffee: [],
      workout: [],
      bathroom: [],
    };

    for (const agent of liveAgents) {
      const idleVariant = controlledIdleVariants[agent.name] ?? 'sleeping';
      const deskTarget = DESK_SPOTS[agent.name] ?? { x: 50, y: 50 };
      let target = deskTarget;
      let zone = `desk:${agent.name}`;

      if (agent.status === 'idle') {
        if (idleVariant === 'coffee') {
          target = PUBLIC_SPOTS.coffee;
          zone = 'coffee';
          publicZoneGroups.coffee.push(agent.name);
        } else if (idleVariant === 'workout') {
          target = PUBLIC_SPOTS.workout;
          zone = 'workout';
          publicZoneGroups.workout.push(agent.name);
        } else if (idleVariant === 'bathroom') {
          target = PUBLIC_SPOTS.bathroom;
          zone = 'bathroom';
          publicZoneGroups.bathroom.push(agent.name);
        }
      }

      baseTargets[agent.name] = { ...target, zone, idleVariant };
    }

    const output: Record<string, AvatarPosition> = {};
    const zoneKeys = Object.keys(publicZoneGroups) as PublicZoneKey[];
    for (const zone of zoneKeys) {
      const agentNames = publicZoneGroups[zone];
      const layout = ZONE_LAYOUT[zone];
      agentNames.forEach((agentName, idx) => {
        const row = Math.floor(idx / layout.perRow);
        const col = idx % layout.perRow;
        const itemsInRow = Math.min(layout.perRow, agentNames.length - row * layout.perRow);
        const colOffset = (col - (itemsInRow - 1) / 2) * layout.xGap;
        const rowOffset = row * layout.yGap;
        const base = baseTargets[agentName];
        output[agentName] = {
          x: base.x + colOffset,
          y: base.y + rowOffset + PUBLIC_ZONE_Y_OFFSET,
          idleVariant: base.idleVariant,
        };
      });
    }

    for (const agent of liveAgents) {
      if (output[agent.name]) continue;
      const base = baseTargets[agent.name];
      output[agent.name] = { x: base.x, y: base.y, idleVariant: base.idleVariant };
    }

    return output;
  }, [liveAgents, controlledIdleVariants]);

  return (
    <main className="office-page">
      <header className="page-header">
        <h1>Drvis办公室</h1>
        <span className={connected ? 'conn connected' : 'conn'}>{connected ? '在线' : '断线'}</span>
      </header>

      <div className="layout">
        <section className="office-scene">
          <div className="public-zone coffee">
            <h3>咖啡区</h3>
            <div className="zone-props coffee-props" aria-hidden="true">
              <span className="prop-emoji">☕</span>
              <span className="prop-emoji">☕</span>
              <span className="prop-emoji">🫘</span>
            </div>
          </div>
          <div className="public-zone gym">
            <h3>健身区</h3>
            <div className="zone-props gym-props" aria-hidden="true">
              <div className="treadmill">
                <span className="belt" />
                <span className="post" />
              </div>
              <span className="prop-emoji">🏋️</span>
            </div>
          </div>
          <div className="public-zone restroom">
            <h3>卫生间</h3>
            <div className="zone-props restroom-props" aria-hidden="true">
              <span className="prop-emoji">🚽</span>
              <span className="sink" />
            </div>
          </div>

          {liveAgents.map((agent) => {
            const desk = DESK_SPOTS[agent.name] ?? { x: 50, y: 50 };
            return (
              <div className="desk" key={`desk-${agent.name}`} style={{ left: `${desk.x}%`, top: `${desk.y}%` }}>
                <div className="desk-screen" />
                <div className="desk-table" />
                <button type="button" className="desk-mini-btn" onClick={() => cycleStatus(agent.name)}>
                  切换
                </button>
              </div>
            );
          })}

          <div className="avatars-layer">
            {liveAgents.map((agent) => {
              const position = avatarPositions[agent.name] ?? { x: 50, y: 50, idleVariant: 'sleeping' };
              const statusText = agent.message || agent.status;
              const showStatusText = statusText !== '等待新任务';

              return (
                <div
                  className={`pony-node is-${agent.status}`}
                  key={agent.name}
                  style={{ left: `${position.x}%`, top: `${position.y}%` }}
                >
                  <div className="pony-name">{agent.displayName}</div>
                  <PonyAvatar
                    status={agent.status}
                    idleVariant={position.idleVariant}
                    petTheme={AGENT_PET_THEME[agent.name] ?? 'horse'}
                  />
                  {showStatusText ? <div className="pony-status">{statusText}</div> : null}
                </div>
              );
            })}
          </div>
        </section>

        <aside className="side-panel">
          <section className="task-panel">
            <textarea
              value={userRequest}
              onChange={(event) => setUserRequest(event.target.value)}
              placeholder="输入要交给多 Agent 的任务..."
              rows={3}
            />
            <div className="control-panel">
              <button type="button" onClick={startTask} disabled={submitting}>
                启动真实任务
              </button>
              <button type="button" onClick={triggerSimulation} disabled={submitting}>
                启动模拟任务
              </button>
              <button type="button" onClick={resetManual}>
                重置
              </button>
            </div>
            {banner ? <p className="banner">{banner}</p> : null}
          </section>

          <TokenBar totalTokens={totalTokens} />

          <div className="stats-box">
            <div>
              <strong>{runningCount}</strong>
              <span>进行中</span>
            </div>
            <div>
              <strong>{doneCount}</strong>
              <span>已完成</span>
            </div>
            <div>
              <strong>{liveAgents.length}</strong>
              <span>总计</span>
            </div>
          </div>

          {pendingConfirmation ? (
            <section className="confirm-box">
              <h3>敏感操作确认</h3>
              <p>
                <strong>{pendingConfirmation.agentDisplayName}</strong> 请求执行: {pendingConfirmation.action}
              </p>
              <pre>{JSON.stringify(pendingConfirmation.detail, null, 2)}</pre>
              <div className="confirm-actions">
                <button type="button" onClick={() => resolveConfirmation(true)} disabled={submitting}>
                  允许继续
                </button>
                <button type="button" onClick={() => resolveConfirmation(false)} disabled={submitting}>
                  拒绝执行
                </button>
              </div>
            </section>
          ) : null}

          <section className="task-log">
            <h3>任务日志</h3>
            <ul>
              {taskLog.length === 0 ? <li>等待任务...</li> : null}
              {[...taskLog].reverse().slice(0, 24).map((line, index) => (
                <li key={`${line}-${index}`}>{line}</li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </main>
  );
}

export default App;

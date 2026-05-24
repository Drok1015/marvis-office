export type AgentStatus = 'idle' | 'dispatching' | 'thinking' | 'working' | 'done' | 'error' | 'paused';

export type AgentDef = {
  id: string;
  name: string;
  displayName: string;
  role: string;
};

export type AgentProgress = {
  current_step: number;
  total_steps: number;
  step_name?: string;
};

export type AgentState = AgentDef & {
  status: AgentStatus;
  message: string;
  tokenUsed: number;
  progress?: AgentProgress;
};

export type PendingConfirmation = {
  confirmationId: string;
  agentName: string;
  agentDisplayName: string;
  action: string;
  detail: Record<string, unknown>;
};

export const AGENT_DEFS: AgentDef[] = [
  { id: 'main-agent', name: 'main-agent', displayName: 'Main Agent', role: 'PM / 调度者' },
  { id: 'file-agent', name: 'file-agent', displayName: 'File Agent', role: '文件处理' },
  { id: 'computer-agent', name: 'computer-agent', displayName: 'Computer Agent', role: '系统操作' },
  { id: 'app-agent', name: 'app-agent', displayName: 'App Agent', role: '应用操作' },
  { id: 'browser-agent', name: 'browser-agent', displayName: 'Browser Agent', role: '网页交互' },
  { id: 'search-agent', name: 'search-agent', displayName: 'Search Agent', role: '联网检索' },
];

export const STATUS_LABELS: Record<AgentStatus, string> = {
  idle: '摸鱼中...',
  dispatching: '正在分配任务...',
  thinking: '思考中...',
  working: '正在搬砖...',
  done: '任务完成！',
  error: '出错了',
  paused: '等你确认...',
};

export function buildInitialAgents(): AgentState[] {
  return AGENT_DEFS.map((agent) => ({
    ...agent,
    status: 'idle',
    message: '等待新任务',
    tokenUsed: 0,
  }));
}

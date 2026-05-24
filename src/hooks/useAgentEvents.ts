import { useEffect, useMemo, useState } from 'react';
import { AGENT_DEFS, type AgentProgress, type AgentState, type AgentStatus, type PendingConfirmation } from '../data/agents';

type RawEvent = {
  event_type: string;
  event_id?: string;
  agent_name?: string;
  agent_display_name?: string;
  status?: AgentStatus;
  message?: string;
  progress?: AgentProgress;
  token_used?: number;
  total_token_used?: number;
  result_summary?: string;
  task_summary?: string;
  to_agent?: string;
  detail?: {
    confirmation_id?: string;
    action?: string;
    detail?: Record<string, unknown>;
    approved?: boolean;
  };
};

export function useAgentEvents() {
  const [agents, setAgents] = useState<Map<string, AgentState>>(new Map());
  const [taskLog, setTaskLog] = useState<string[]>([]);
  const [totalTokens, setTotalTokens] = useState(0);
  const [connected, setConnected] = useState(false);
  const [pendingConfirmation, setPendingConfirmation] = useState<PendingConfirmation | null>(null);

  useEffect(() => {
    const source = new EventSource('/api/events/stream');

    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);

    source.onmessage = (event) => {
      try {
        const data: RawEvent = JSON.parse(event.data);

        if (data.event_type === 'agent_status_change' && data.agent_name && data.status) {
          const agentName = data.agent_name;
          const status = data.status;
          setAgents((prev) => {
            const next = new Map(prev);
            const found = AGENT_DEFS.find((item) => item.name === agentName);
            if (!found) return prev;

            next.set(agentName, {
              ...found,
              status,
              message: data.message ?? '',
              progress: data.progress,
              tokenUsed: data.token_used ?? 0,
            });
            return next;
          });

          setTaskLog((prev) => [
            ...prev.slice(-69),
            `[${data.agent_display_name ?? data.agent_name}] ${status} ${data.message ?? ''}`,
          ]);
        }

        if (data.event_type === 'task_dispatched') {
          setTaskLog((prev) => [...prev.slice(-69), `任务派发: ${data.to_agent ?? '-'} -> ${data.task_summary ?? ''}`]);
        }

        if (data.event_type === 'token_update') {
          setTotalTokens((prev) => data.token_used ?? prev);
        }

        if (data.event_type === 'confirmation_required' && data.agent_name && data.agent_display_name) {
          const id = data.detail?.confirmation_id;
          if (!id) return;
          setPendingConfirmation({
            confirmationId: id,
            agentName: data.agent_name,
            agentDisplayName: data.agent_display_name,
            action: data.detail?.action ?? '敏感操作确认',
            detail: data.detail?.detail ?? {},
          });
          setTaskLog((prev) => [...prev.slice(-69), `[${data.agent_display_name}] 需要确认: ${data.detail?.action ?? ''}`]);
        }

        if (data.event_type === 'confirmation_resolved') {
          const resolvedId = data.detail?.confirmation_id;
          setPendingConfirmation((prev) => (prev && prev.confirmationId === resolvedId ? null : prev));
          setTaskLog((prev) => [...prev.slice(-69), data.message ?? '确认状态已更新']);
        }

        if (data.event_type === 'task_completed') {
          setTotalTokens((prev) => data.total_token_used ?? data.token_used ?? prev);
          setTaskLog((prev) => [
            ...prev.slice(-69),
            `全部任务完成: ${data.result_summary ?? data.message ?? '已完成'}`,
          ]);
        }

        if (data.event_type === 'agent_error') {
          setTaskLog((prev) => [...prev.slice(-69), `[错误] ${data.message ?? 'Agent 执行失败'}`]);
        }
      } catch {
        // ignore invalid event
      }
    };

    return () => source.close();
  }, []);

  const streamAgents = useMemo(() => agents, [agents]);
  return { streamAgents, taskLog, totalTokens, connected, pendingConfirmation };
}

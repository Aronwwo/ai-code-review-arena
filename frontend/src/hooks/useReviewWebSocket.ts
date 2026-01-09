import { useEffect, useState, useCallback, useRef } from 'react';

export interface ReviewWebSocketEvent {
  type: 'review_started' | 'agent_started' | 'agent_completed' | 'review_completed' | 'review_failed';
  review_id: number;
  agent_roles?: string[];
  agent_role?: string;
  issue_count?: number;
  parsed_successfully?: boolean;
  total_issues?: number;
  status?: string;
  error?: string;
}

interface UseReviewWebSocketOptions {
  reviewId: number | null;
  enabled?: boolean;
  onEvent?: (event: ReviewWebSocketEvent) => void;
}

interface UseReviewWebSocketReturn {
  isConnected: boolean;
  lastEvent: ReviewWebSocketEvent | null;
  agentProgress: Map<string, 'pending' | 'running' | 'completed' | 'failed'>;
  reviewStatus: 'pending' | 'running' | 'completed' | 'failed';
  totalIssues: number;
}

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export function useReviewWebSocket({
  reviewId,
  enabled = true,
  onEvent,
}: UseReviewWebSocketOptions): UseReviewWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<ReviewWebSocketEvent | null>(null);
  const [agentProgress, setAgentProgress] = useState<Map<string, 'pending' | 'running' | 'completed' | 'failed'>>(new Map());
  const [reviewStatus, setReviewStatus] = useState<'pending' | 'running' | 'completed' | 'failed'>('pending');
  const [totalIssues, setTotalIssues] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const connect = useCallback(() => {
    if (!reviewId || !enabled) return;

    const token = localStorage.getItem('token');
    if (!token) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_URL}/ws/reviews/${reviewId}?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      // Start ping interval to keep connection alive
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      if (event.data === 'pong') return;

      try {
        const data: ReviewWebSocketEvent = JSON.parse(event.data);
        setLastEvent(data);

        // Update state based on event type
        switch (data.type) {
          case 'review_started':
            setReviewStatus('running');
            if (data.agent_roles) {
              const newProgress = new Map<string, 'pending' | 'running' | 'completed' | 'failed'>();
              data.agent_roles.forEach((role) => newProgress.set(role, 'pending'));
              setAgentProgress(newProgress);
            }
            break;

          case 'agent_started':
            if (data.agent_role) {
              setAgentProgress((prev) => {
                const newMap = new Map(prev);
                newMap.set(data.agent_role!, 'running');
                return newMap;
              });
            }
            break;

          case 'agent_completed':
            if (data.agent_role) {
              setAgentProgress((prev) => {
                const newMap = new Map(prev);
                newMap.set(data.agent_role!, data.parsed_successfully ? 'completed' : 'failed');
                return newMap;
              });
              if (data.issue_count) {
                setTotalIssues((prev) => prev + data.issue_count!);
              }
            }
            break;

          case 'review_completed':
            setReviewStatus('completed');
            if (data.total_issues !== undefined) {
              setTotalIssues(data.total_issues);
            }
            break;

          case 'review_failed':
            setReviewStatus('failed');
            break;
        }

        // Call custom event handler
        if (onEvent) {
          onEvent(data);
        }
      } catch (e) {
        // Failed to parse message - ignore malformed messages
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }

      // Reconnect if review is still running
      if (reviewStatus === 'running' && enabled) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      }
    };

    ws.onerror = () => {
      // WebSocket error - will attempt reconnect on close
    };
  }, [reviewId, enabled, onEvent, reviewStatus]);

  // Connect when reviewId changes
  useEffect(() => {
    if (reviewId && enabled) {
      connect();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    };
  }, [reviewId, enabled, connect]);

  return {
    isConnected,
    lastEvent,
    agentProgress,
    reviewStatus,
    totalIssues,
  };
}

import { useState, useEffect, useRef } from 'react';
import { resolveSimulationSocketUrl } from '../services/api';

export interface SimulationEvent {
  event: string;
  message?: string | null;
  data?: Record<string, unknown> | null;
}

const defaultSocketUrl = resolveSimulationSocketUrl;

export function useSimulationSocket(url?: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SimulationEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let disposed = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let retryMs = 1000;

    const connect = () => {
      if (disposed) return;
      const ws = new WebSocket(url || defaultSocketUrl());
      wsRef.current = ws;
      ws.onopen = () => {
        retryMs = 1000;
        setIsConnected(true);
      };
      ws.onerror = () => ws.close();
      ws.onclose = () => {
        setIsConnected(false);
        if (!disposed) {
          retryTimer = setTimeout(connect, retryMs);
          retryMs = Math.min(retryMs * 2, 30000);
        }
      };
      ws.onmessage = (message) => {
        try {
          const frame = JSON.parse(message.data) as SimulationEvent;
          if (typeof frame.event === 'string') setLastEvent(frame);
        } catch {
          console.warn('Ignored malformed simulation event');
        }
      };
    };

    connect();
    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [url]);

  return { isConnected, lastEvent };
}

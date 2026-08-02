import { useState, useEffect, useRef } from 'react';

interface LogMessage {
  type: 'log' | 'status' | 'error';
  message: string;
}

export function useSimulationSocket(url = 'ws://localhost:5001/ws') {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onerror = (error) => console.error('WebSocket error:', error);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as LogMessage;
        if (data.type === 'error') {
          console.error('[Simulation Error]', data.message);
        } else if (data.type === 'status') {
          console.info('[Simulation Status]', data.message);
        } else {
          console.log('[Simulation Log]', data.message);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message', event.data);
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [url]);

  return { isConnected };
}

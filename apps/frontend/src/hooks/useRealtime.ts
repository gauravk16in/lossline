import { useState, useEffect, useRef } from 'react';

type ConnectionStatus = 'connecting' | 'live' | 'reconnecting';

interface UseRealtimeResult {
  status: ConnectionStatus;
}

export function useRealtime(onMessage: () => void): UseRealtimeResult {
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | undefined;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
      const wsUrl = `${protocol}://${location.host}/api/v1/ws`;
      try {
        socket = new WebSocket(wsUrl);
      } catch {
        setStatus('reconnecting');
        if (!stopped) retryTimer = setTimeout(connect, 2000);
        return;
      }

      socket.onopen = () => {
        if (!stopped) setStatus('live');
      };

      socket.onmessage = () => {
        if (!stopped) onMessageRef.current();
      };

      socket.onclose = () => {
        if (!stopped) {
          setStatus('reconnecting');
          retryTimer = setTimeout(connect, 1500);
        }
      };

      socket.onerror = () => {
        if (!stopped) setStatus('reconnecting');
      };
    };

    connect();

    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, []);

  return { status };
}

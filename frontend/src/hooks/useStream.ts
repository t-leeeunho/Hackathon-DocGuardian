import { useEffect, useRef } from 'react';
import { api } from '../lib/api';
import type { StreamEvent } from '../lib/types';

/**
 * Subscribe to the backend `WS /stream` live event feed. Calls `onEvent` for each
 * event (ingest/graph/metrics/proposal). Auto-reconnects with backoff and is a
 * no-op fallback in demo mode (the socket just keeps retrying quietly).
 */
export function useStream(onEvent: (event: StreamEvent) => void): void {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let retry = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (closed) return;
      try {
        ws = new WebSocket(api.streamUrl());
      } catch {
        schedule();
        return;
      }
      ws.onopen = () => {
        retry = 0;
      };
      ws.onmessage = (e) => {
        try {
          handlerRef.current(JSON.parse(e.data) as StreamEvent);
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        if (!closed) schedule();
      };
      ws.onerror = () => {
        ws?.close();
      };
    };

    const schedule = () => {
      retry = Math.min(retry + 1, 6);
      const delay = 500 * 2 ** (retry - 1); // 0.5s → up to ~16s
      timer = setTimeout(connect, delay);
    };

    connect();
    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      ws?.close();
    };
  }, []);
}

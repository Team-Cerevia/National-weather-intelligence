"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { WS_URL } from "../lib/api";
import type { Incident, StreamEvent } from "../lib/types";

interface UseRealtimeStreamReturn {
  connected: boolean;
  lastIncident: Incident | null;
  lastEventAt: Date | null;
}

export function useRealtimeStream(
  onIncident?: (incident: Incident) => void
): UseRealtimeStreamReturn {
  const [connected, setConnected] = useState(false);
  const [lastIncident, setLastIncident] = useState<Incident | null>(null);
  const [lastEventAt, setLastEventAt] = useState<Date | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
      };

      ws.onmessage = (ev) => {
        if (!mountedRef.current) return;
        try {
          const event: StreamEvent = JSON.parse(ev.data as string);
          if (event.event === "incident_update" && event.incident) {
            setLastIncident(event.incident);
            setLastEventAt(new Date());
            onIncident?.(event.incident);
          }
        } catch {
          // malformed frame — ignore
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        // Auto-reconnect after 3 seconds
        reconnectTimer.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // WebSocket unavailable (SSR or network) — retry later
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, [onIncident]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected, lastIncident, lastEventAt };
}

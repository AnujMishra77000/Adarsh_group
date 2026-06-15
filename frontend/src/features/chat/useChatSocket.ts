import { useEffect, useRef } from "react";

import { buildChatWebSocketUrl } from "@/features/chat/api";
import type { ChatSocketEvent } from "@/types/chat";

type UseChatSocketParams = {
  enabled: boolean;
  onEvent: (event: ChatSocketEvent) => void;
};

export function useChatSocket({ enabled, onEvent }: UseChatSocketParams) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const socketUrl = buildChatWebSocketUrl();
    if (!socketUrl) {
      return;
    }

    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let shouldReconnect = true;

    const connect = () => {
      socket = new WebSocket(socketUrl);

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as ChatSocketEvent;
          onEventRef.current(parsed);
        } catch {
          // Ignore malformed payloads from network noise.
        }
      };

      socket.onclose = () => {
        if (!shouldReconnect) {
          return;
        }
        reconnectTimer = window.setTimeout(connect, 2000);
      };
    };

    connect();

    return () => {
      shouldReconnect = false;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [enabled]);
}

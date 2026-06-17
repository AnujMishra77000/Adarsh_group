import apiClient from "@/lib/api";
import { getAccessToken, getActiveAuthRole } from "@/features/auth/store";
import type { ChatMessage, ChatMessageListResponse } from "@/types/chat";

export async function listChatMessages(params?: { limit?: number; before_id?: number }): Promise<ChatMessageListResponse> {
  const response = await apiClient.get<ChatMessageListResponse>("/chat/messages", { params });
  return response.data;
}

export async function sendTextChatMessage(messageText: string): Promise<ChatMessage> {
  const response = await apiClient.post<ChatMessage>("/chat/messages", {
    message_text: messageText
  });
  return response.data;
}

export async function sendFileChatMessage(file: File, messageText?: string): Promise<ChatMessage> {
  const formData = new FormData();
  formData.append("file", file);
  if (messageText && messageText.trim()) {
    formData.append("message_text", messageText.trim());
  }

  const response = await apiClient.post<ChatMessage>("/chat/messages/file", formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });
  return response.data;
}

export async function downloadChatAttachment(messageId: number, preferredFileName?: string): Promise<void> {
  const response = await apiClient.get(`/chat/messages/${messageId}/download`, {
    responseType: "blob"
  });
  const blob = response.data as Blob;
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = preferredFileName ?? `chat-file-${messageId}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export function buildChatWebSocketUrl(): string | null {
  const activeRole = getActiveAuthRole();
  const accessToken = getAccessToken(activeRole ?? undefined);
  if (!accessToken) {
    return null;
  }

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
  const normalizedHttpOrigin = apiBaseUrl.replace(/\/api\/v1\/?$/, "");
  const websocketOrigin = normalizedHttpOrigin.replace(/^http/i, "ws");

  return `${websocketOrigin}/api/v1/chat/ws?token=${encodeURIComponent(accessToken)}`;
}

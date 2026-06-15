import { useMutation, useQuery } from "@tanstack/react-query";
import { Paperclip, Send } from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { useCurrentUser } from "@/features/auth/useCurrentUser";
import { downloadChatAttachment, listChatMessages, sendFileChatMessage, sendTextChatMessage } from "@/features/chat/api";
import { useChatSocket } from "@/features/chat/useChatSocket";
import { getErrorMessage } from "@/lib/errors";
import type { ChatMessage, ChatSocketEvent } from "@/types/chat";

function formatDateTime(isoValue: string): string {
  const parsed = new Date(isoValue);
  if (Number.isNaN(parsed.getTime())) {
    return isoValue;
  }
  return parsed.toLocaleString();
}

function formatBytes(bytes: number | null): string {
  if (!bytes || bytes <= 0) {
    return "-";
  }
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function upsertMessages(existing: ChatMessage[], incoming: ChatMessage): ChatMessage[] {
  const byId = new Map<number, ChatMessage>();
  for (const item of existing) {
    byId.set(item.id, item);
  }
  byId.set(incoming.id, incoming);
  return Array.from(byId.values()).sort((a, b) => a.id - b.id);
}

export function SharedChatPage() {
  const currentUserQuery = useCurrentUser();
  const currentUser = currentUserQuery.data;
  const [messageText, setMessageText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const messagesQuery = useQuery({
    queryKey: ["shared-chat", "messages"],
    queryFn: () => listChatMessages({ limit: 80 })
  });

  useEffect(() => {
    if (messagesQuery.data?.items) {
      setMessages(messagesQuery.data.items);
    }
  }, [messagesQuery.data?.items]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  useChatSocket({
    enabled: Boolean(currentUser),
    onEvent: (event: ChatSocketEvent) => {
      if (event.event === "chat.message.created") {
        setMessages((existing) => upsertMessages(existing, event.data));
      }
    }
  });

  const sendMessageMutation = useMutation({
    mutationFn: async () => {
      const normalizedText = messageText.trim();
      if (selectedFile) {
        return sendFileChatMessage(selectedFile, normalizedText || undefined);
      }
      return sendTextChatMessage(normalizedText);
    },
    onSuccess: (message) => {
      setMessages((existing) => upsertMessages(existing, message));
      setMessageText("");
      setSelectedFile(null);
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    }
  });

  const canSend = useMemo(() => messageText.trim().length > 0 || selectedFile !== null, [messageText, selectedFile]);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSend || sendMessageMutation.isPending) {
      return;
    }
    sendMessageMutation.mutate();
  };

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-pink-300/25 bg-matte-850/90 p-4 shadow-neon-ring sm:p-5">
        <h2 className="text-xl font-semibold text-slate-100">Shared Inter-Shop Chat</h2>
        <p className="mt-1 text-sm text-slate-300">
          Live chat shared by all three shops. Send text, PDFs, prescriptions, bills, or other files.
          Compressible files are optimized automatically to keep storage light.
        </p>
      </section>

      <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-3 shadow-neon-ring sm:p-4">
        <div className="h-[54vh] overflow-y-auto rounded-xl border border-pink-300/20 bg-matte-900/50 p-3 sm:h-[58vh]">
          {messagesQuery.isLoading ? (
            <p className="text-sm text-slate-300">Loading messages...</p>
          ) : messages.length === 0 ? (
            <p className="text-sm text-slate-300">No messages yet. Start the first conversation.</p>
          ) : (
            <div className="space-y-3">
              {messages.map((message) => {
                const isOwn = currentUser?.id === message.sender_user_id;
                return (
                  <article
                    key={message.id}
                    className={
                      "rounded-xl border px-3 py-2 " +
                      (isOwn
                        ? "border-fuchsia-300/40 bg-fuchsia-500/15"
                        : "border-pink-300/25 bg-matte-800/75")
                    }
                  >
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
                      <span className="font-semibold text-slate-100">{message.sender_name}</span>
                      <span className="rounded-md border border-pink-300/35 bg-pink-500/10 px-1.5 py-0.5 text-[10px] text-pink-100">
                        {message.sender_role}
                      </span>
                      <span className="text-[11px] text-slate-300">{message.sender_shop_name}</span>
                      <span className="ml-auto text-[11px] text-slate-400">{formatDateTime(message.created_at)}</span>
                    </div>

                    {message.message_text && <p className="mt-2 whitespace-pre-wrap break-words text-sm text-slate-100">{message.message_text}</p>}

                    {message.has_attachment && message.attachment_original_name && (
                      <div className="mt-2 rounded-lg border border-pink-300/30 bg-pink-500/10 px-2.5 py-2 text-xs">
                        <p className="truncate font-medium text-pink-100">{message.attachment_original_name}</p>
                        <p className="mt-0.5 text-[11px] text-slate-300">
                          {message.attachment_content_type || "application/octet-stream"} • {formatBytes(message.attachment_size_bytes)}
                        </p>
                        <button
                          type="button"
                          onClick={() => void downloadChatAttachment(message.id, message.attachment_original_name ?? undefined)}
                          className="mt-2 rounded-md border border-pink-300/45 bg-pink-500/15 px-2.5 py-1 text-[11px] font-medium text-pink-100"
                        >
                          Download File
                        </button>
                      </div>
                    )}
                  </article>
                );
              })}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <form className="mt-3 space-y-3" onSubmit={onSubmit}>
          <textarea
            value={messageText}
            onChange={(event) => setMessageText(event.target.value)}
            rows={3}
            placeholder="Type your message here..."
            maxLength={4000}
            className="w-full"
          />

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-pink-300/45 bg-pink-500/10 px-3 py-2 text-xs font-medium text-pink-100">
              <Paperclip size={14} />
              <span>{selectedFile ? selectedFile.name : "Attach File"}</span>
              <input
                type="file"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setSelectedFile(file);
                }}
              />
            </label>

            <button
              type="submit"
              disabled={!canSend || sendMessageMutation.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-pink-300/45 bg-pink-500/15 px-4 py-2 text-sm font-semibold text-pink-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Send size={14} />
              {sendMessageMutation.isPending ? "Sending..." : "Send"}
            </button>
          </div>

          <p className="text-[11px] text-slate-400">
            Max upload size is 12 MB per file. Large image/text files are auto-optimized where possible.
          </p>
        </form>
      </section>
    </div>
  );
}

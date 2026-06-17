export type ChatMessage = {
  id: number;
  sender_user_id: number | null;
  sender_name: string;
  sender_role: "admin" | "staff" | string;
  sender_shop_key: string;
  sender_shop_name: string;
  message_text: string | null;
  attachment_original_name: string | null;
  attachment_content_type: string | null;
  attachment_size_bytes: number | null;
  attachment_stored_bytes: number | null;
  is_attachment_compressed: boolean;
  has_attachment: boolean;
  created_at: string;
  updated_at: string;
};

export type ChatMessageListResponse = {
  items: ChatMessage[];
  has_more: boolean;
};

export type ChatSocketEvent =
  | {
      event: "chat.message.created";
      data: ChatMessage;
    }
  | {
      event: "chat.connected" | "chat.pong";
      data?: Record<string, unknown>;
    };

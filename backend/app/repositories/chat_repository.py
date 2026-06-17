from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.shop_scope import assign_shop_scope, shop_filter
from app.models.chat_message import ChatMessage


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_recent(self, limit: int, shop_key: str, before_id: int | None = None) -> list[ChatMessage]:
        query = self.db.query(ChatMessage).filter(
            shop_filter(self.db, ChatMessage, shop_key, legacy_attr="sender_shop_key")
        )
        if before_id is not None:
            query = query.filter(ChatMessage.id < before_id)

        return (
            query.order_by(ChatMessage.id.desc())
            .limit(limit)
            .all()
        )

    def get_by_id(self, message_id: int, shop_key: str) -> ChatMessage | None:
        return (
            self.db.query(ChatMessage)
            .filter(
                ChatMessage.id == message_id,
                shop_filter(self.db, ChatMessage, shop_key, legacy_attr="sender_shop_key"),
            )
            .first()
        )

    def create(self, message: ChatMessage) -> ChatMessage:
        assign_shop_scope(message, self.db, message.sender_shop_key, legacy_attr="sender_shop_key")
        self.db.add(message)
        self.db.flush()
        return message

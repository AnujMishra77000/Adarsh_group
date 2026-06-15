from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_recent(self, limit: int, before_id: int | None = None) -> list[ChatMessage]:
        query = self.db.query(ChatMessage)
        if before_id is not None:
            query = query.filter(ChatMessage.id < before_id)

        return (
            query.order_by(ChatMessage.id.desc())
            .limit(limit)
            .all()
        )

    def get_by_id(self, message_id: int) -> ChatMessage | None:
        return self.db.query(ChatMessage).filter(ChatMessage.id == message_id).first()

    def create(self, message: ChatMessage) -> ChatMessage:
        self.db.add(message)
        self.db.flush()
        return message

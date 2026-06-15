from __future__ import annotations

import gzip
import hashlib
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.shops import get_shop_name
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatMessageRead

_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_COMPRESSIBLE_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "application/javascript",
    "text/plain",
    "text/csv",
    "text/xml",
    "text/html",
}


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ChatRepository(db)
        self.storage_root = settings.chat_storage_root_path
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def list_messages(self, limit: int, before_id: int | None = None) -> tuple[list[ChatMessageRead], bool]:
        safe_limit = max(1, min(limit, 100))
        rows = self.repo.list_recent(limit=safe_limit + 1, before_id=before_id)
        has_more = len(rows) > safe_limit
        visible_rows = rows[:safe_limit]

        # Query is DESC by id; UI needs ASC for chat timeline.
        items = [self._to_read_schema(row) for row in reversed(visible_rows)]
        return items, has_more

    def create_text_message(self, message_text: str, actor: User) -> ChatMessageRead:
        normalized_text = message_text.strip()
        if not normalized_text:
            raise AppException(status_code=422, code="chat_message_empty", message="Message text cannot be empty")

        message = ChatMessage(
            sender_user_id=actor.id,
            sender_name=self._sender_name(actor),
            sender_role=actor.role.value,
            sender_shop_key=actor.shop_key,
            message_text=normalized_text,
        )

        self.repo.create(message)
        self.db.commit()
        self.db.refresh(message)
        return self._to_read_schema(message)

    def create_file_message(
        self,
        *,
        file_name: str,
        content_type: str | None,
        file_bytes: bytes,
        message_text: str | None,
        actor: User,
    ) -> ChatMessageRead:
        if len(file_bytes) == 0:
            raise AppException(status_code=422, code="chat_file_empty", message="File is empty")

        max_size_bytes = settings.chat_max_file_size_mb * 1024 * 1024
        if len(file_bytes) > max_size_bytes:
            raise AppException(
                status_code=413,
                code="chat_file_too_large",
                message=f"File too large. Max allowed size is {settings.chat_max_file_size_mb} MB",
            )

        normalized_text = (message_text or "").strip() or None
        normalized_original_name = self._normalize_filename(file_name)
        normalized_content_type = (content_type or "application/octet-stream").strip().lower()

        storage_name = self._build_storage_name(normalized_original_name)
        payload_to_store = file_bytes
        is_compressed = False

        if self._is_compressible(normalized_content_type):
            compressed_payload = gzip.compress(file_bytes, compresslevel=6)
            if len(compressed_payload) + 64 < len(file_bytes):
                payload_to_store = compressed_payload
                is_compressed = True
                storage_name = f"{storage_name}.gz"

        destination = self.storage_root / storage_name
        destination.write_bytes(payload_to_store)

        message = ChatMessage(
            sender_user_id=actor.id,
            sender_name=self._sender_name(actor),
            sender_role=actor.role.value,
            sender_shop_key=actor.shop_key,
            message_text=normalized_text,
            attachment_original_name=normalized_original_name,
            attachment_storage_name=storage_name,
            attachment_content_type=normalized_content_type,
            attachment_size_bytes=len(file_bytes),
            attachment_stored_bytes=len(payload_to_store),
            attachment_sha256=hashlib.sha256(file_bytes).hexdigest(),
            is_attachment_compressed=is_compressed,
        )

        self.repo.create(message)
        self.db.commit()
        self.db.refresh(message)
        return self._to_read_schema(message)

    def get_attachment_for_download(self, message_id: int) -> tuple[ChatMessage, bytes, str]:
        message = self.repo.get_by_id(message_id)
        if message is None:
            raise AppException(status_code=404, code="chat_message_not_found", message="Chat message not found")

        if not message.attachment_storage_name or not message.attachment_original_name:
            raise AppException(
                status_code=404,
                code="chat_attachment_not_found",
                message="This chat message does not contain an attachment",
            )

        file_path = self.storage_root / message.attachment_storage_name
        if not file_path.exists() or not file_path.is_file():
            raise AppException(status_code=404, code="chat_file_not_found", message="Attachment file not found on server")

        raw_payload = file_path.read_bytes()
        if message.is_attachment_compressed:
            payload = gzip.decompress(raw_payload)
        else:
            payload = raw_payload

        media_type = message.attachment_content_type or "application/octet-stream"
        return message, payload, media_type

    def _to_read_schema(self, row: ChatMessage) -> ChatMessageRead:
        return ChatMessageRead(
            id=row.id,
            sender_user_id=row.sender_user_id,
            sender_name=row.sender_name,
            sender_role=row.sender_role,
            sender_shop_key=row.sender_shop_key,
            sender_shop_name=get_shop_name(row.sender_shop_key),
            message_text=row.message_text,
            attachment_original_name=row.attachment_original_name,
            attachment_content_type=row.attachment_content_type,
            attachment_size_bytes=row.attachment_size_bytes,
            attachment_stored_bytes=row.attachment_stored_bytes,
            is_attachment_compressed=row.is_attachment_compressed,
            has_attachment=bool(row.attachment_storage_name),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def build_created_event(message: ChatMessageRead) -> dict[str, object]:
        return {
            "event": "chat.message.created",
            "data": message.model_dump(mode="json"),
        }

    @staticmethod
    def _is_compressible(content_type: str) -> bool:
        if content_type.startswith("text/"):
            return True
        return content_type in _COMPRESSIBLE_CONTENT_TYPES

    @staticmethod
    def _sender_name(actor: User) -> str:
        if actor.full_name and actor.full_name.strip():
            return actor.full_name.strip()
        return actor.email

    @staticmethod
    def _normalize_filename(raw_file_name: str) -> str:
        candidate = Path(raw_file_name or "").name.strip()
        if not candidate:
            candidate = "attachment"
        candidate = _SAFE_FILENAME_PATTERN.sub("_", candidate)
        candidate = candidate.strip("._")
        if not candidate:
            candidate = "attachment"
        return candidate[:180]

    @staticmethod
    def _build_storage_name(original_name: str) -> str:
        stem = Path(original_name).stem[:80] or "file"
        suffix = Path(original_name).suffix[:20]
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        token = secrets.token_hex(6)
        return f"{timestamp}-{token}-{stem}{suffix}"

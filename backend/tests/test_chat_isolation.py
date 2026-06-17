from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import AppException
from app.db.base import Base
from app.models.enums import UserRole
from app.models.user import User
from app.services.chat_realtime_gateway import ChatRealtimeGateway
from app.services.chat_service import ChatService


SHOP_ONE = "adarsh-optical-centre"
SHOP_TWO = "adarsh-eye-boutique"


class ChatIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.storage_root = Path(self.temp_dir.name)
        self.storage_patcher = patch.object(settings, "chat_storage_root", str(self.storage_root))
        self.storage_patcher.start()
        self.addCleanup(self.storage_patcher.stop)

        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db: Session = self.SessionLocal()
        self.addCleanup(self.db.close)

        self.actor_one = self._create_user("one@example.com", SHOP_ONE)
        self.actor_two = self._create_user("two@example.com", SHOP_TWO)

    def _create_user(self, email: str, shop_key: str) -> User:
        user = User(
            email=email,
            full_name=email.split("@")[0],
            password_hash="not-used",
            role=UserRole.ADMIN,
            shop_key=shop_key,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_list_messages_only_returns_current_shop_messages(self) -> None:
        service = ChatService(self.db)
        service.create_text_message(message_text="shop one", actor=self.actor_one)
        service.create_text_message(message_text="shop two", actor=self.actor_two)

        messages, has_more = service.list_messages(limit=20, actor=self.actor_one)

        self.assertFalse(has_more)
        self.assertEqual([message.message_text for message in messages], ["shop one"])
        self.assertEqual({message.sender_shop_key for message in messages}, {SHOP_ONE})

    def test_cross_shop_attachment_download_is_not_available(self) -> None:
        service = ChatService(self.db)
        message = service.create_file_message(
            file_name="secret.pdf",
            content_type="application/pdf",
            file_bytes=b"%PDF-1.4\nprivate",
            message_text="private file",
            actor=self.actor_one,
        )

        with self.assertRaises(AppException) as raised:
            service.get_attachment_for_download(message_id=message.id, actor=self.actor_two)

        self.assertEqual(raised.exception.status_code, 404)

    def test_uploaded_files_are_stored_under_shop_subdirectory(self) -> None:
        service = ChatService(self.db)
        message = service.create_file_message(
            file_name="lens-order.txt",
            content_type="text/plain",
            file_bytes=b"lens order",
            message_text=None,
            actor=self.actor_one,
        )

        stored_path = self.storage_root / SHOP_ONE / Path(message.attachment_original_name or "").name
        matching_files = list((self.storage_root / SHOP_ONE).glob("*lens-order.txt*"))

        self.assertTrue((self.storage_root / SHOP_ONE).is_dir())
        self.assertFalse(stored_path.exists())
        self.assertEqual(len(matching_files), 1)


class _FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.sent_text: list[str] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, payload: str) -> None:
        self.sent_text.append(payload)


class ChatRealtimeGatewayIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_created_message_events_only_broadcast_to_matching_shop(self) -> None:
        gateway = ChatRealtimeGateway(redis_url="redis://localhost:6379/0", channel="test")
        shop_one_socket = _FakeWebSocket()
        shop_two_socket = _FakeWebSocket()

        await gateway.connect(shop_one_socket, shop_key=SHOP_ONE)
        await gateway.connect(shop_two_socket, shop_key=SHOP_TWO)

        await gateway.publish_event(
            {
                "event": "chat.message.created",
                "data": {
                    "id": 1,
                    "sender_shop_key": SHOP_ONE,
                    "message_text": "shop one only",
                },
            }
        )

        self.assertEqual(len(shop_one_socket.sent_text), 1)
        self.assertEqual(shop_two_socket.sent_text, [])


if __name__ == "__main__":
    unittest.main()

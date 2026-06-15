from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.exceptions import AppException
from app.core.security import TokenDecodeError, decode_jwt_token
from app.db.session import get_db
from app.db.tenant import tenant_db_manager
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.chat import ChatMessageCreate, ChatMessageListResponse, ChatMessageRead
from app.services.chat_realtime_gateway import ChatRealtimeGateway
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def _gateway_from_state(websocket: WebSocket) -> ChatRealtimeGateway:
    gateway = getattr(websocket.app.state, "chat_gateway", None)
    if gateway is None:
        raise RuntimeError("Chat gateway is not initialized")
    return gateway


def _authenticate_websocket_user(token: str) -> User:
    try:
        payload = decode_jwt_token(token)
    except TokenDecodeError as exc:
        raise AppException(status_code=401, code="invalid_access_token", message="Invalid access token") from exc

    if payload.get("type") != "access":
        raise AppException(status_code=401, code="invalid_token_type", message="Invalid token type")

    subject = payload.get("sub")
    if subject is None:
        raise AppException(status_code=401, code="malformed_token", message="Malformed token payload")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise AppException(status_code=401, code="malformed_token", message="Malformed token subject") from exc

    shop_code = str(payload.get("shop_code") or "").strip().lower()
    if not shop_code:
        raise AppException(status_code=401, code="missing_shop_context", message="Missing shop context in token")

    with tenant_db_manager.session_scope(shop_code) as db:
        user = UserRepository(db).get_by_id(user_id)
        if not user or not user.is_active:
            raise AppException(status_code=401, code="user_not_active", message="User account not active")

        db.expunge(user)
        return user


@router.get("/messages", response_model=ChatMessageListResponse)
def list_chat_messages(
    limit: int = Query(default=50, ge=1, le=100),
    before_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> ChatMessageListResponse:
    _ = current_user
    service = ChatService(db)
    items, has_more = service.list_messages(limit=limit, before_id=before_id)
    return ChatMessageListResponse(items=items, has_more=has_more)


@router.post("/messages", response_model=ChatMessageRead, status_code=status.HTTP_201_CREATED)
async def create_text_chat_message(
    payload: ChatMessageCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> ChatMessageRead:
    service = ChatService(db)
    message = service.create_text_message(message_text=payload.message_text, actor=current_user)
    gateway = getattr(request.app.state, "chat_gateway", None)
    if gateway is not None:
        await gateway.publish_event(service.build_created_event(message))
    return message


@router.post("/messages/file", response_model=ChatMessageRead, status_code=status.HTTP_201_CREATED)
async def create_file_chat_message(
    request: Request,
    file: UploadFile = File(...),
    message_text: str | None = Form(default=None, max_length=4000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> ChatMessageRead:
    file_bytes = await file.read()
    service = ChatService(db)
    message = service.create_file_message(
        file_name=file.filename or "attachment",
        content_type=file.content_type,
        file_bytes=file_bytes,
        message_text=message_text,
        actor=current_user,
    )
    gateway = getattr(request.app.state, "chat_gateway", None)
    if gateway is not None:
        await gateway.publish_event(service.build_created_event(message))
    return message


@router.get("/messages/{message_id}/download")
def download_chat_attachment(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> Response:
    _ = current_user
    service = ChatService(db)
    message, payload, media_type = service.get_attachment_for_download(message_id=message_id)
    headers = {
        "Content-Disposition": f'attachment; filename="{message.attachment_original_name}"',
    }
    return Response(content=payload, media_type=media_type, headers=headers)


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Missing token")
        return

    try:
        user = _authenticate_websocket_user(token)
    except AppException as exc:
        await websocket.close(code=4401, reason=exc.message)
        return

    gateway = _gateway_from_state(websocket)
    await gateway.connect(websocket)

    await websocket.send_text(
        json.dumps(
            {
                "event": "chat.connected",
                "data": {
                    "user_id": user.id,
                    "sender_name": user.full_name or user.email,
                    "sender_role": user.role.value,
                    "sender_shop_key": user.shop_key,
                },
            }
        )
    )

    try:
        while True:
            raw_data = await websocket.receive_text()
            if not raw_data:
                continue
            try:
                payload = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            if payload.get("type") == "ping":
                await websocket.send_text(json.dumps({"event": "chat.pong"}))
    except WebSocketDisconnect:
        await gateway.disconnect(websocket)
    except Exception:
        await gateway.disconnect(websocket)
        raise

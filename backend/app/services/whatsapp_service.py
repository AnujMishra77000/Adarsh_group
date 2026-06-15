from __future__ import annotations

import mimetypes
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.enums import WhatsAppMessageType, WhatsAppModuleType, WhatsAppStatus
from app.models.whatsapp_log import WhatsAppLog
from app.repositories.whatsapp_log_repository import WhatsAppLogRepository

logger = structlog.get_logger(__name__)


@dataclass
class WhatsAppSendResult:
    status: WhatsAppStatus
    provider_message_id: str | None = None
    media_id: str | None = None
    error_message: str | None = None
    response_payload: dict[str, Any] | None = None
    whatsapp_log_id: int | None = None


class WhatsAppService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WhatsAppLogRepository(db)

    def _require_configuration(self) -> None:
        if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
            raise AppException(
                status_code=503,
                code="whatsapp_not_configured",
                message="WhatsApp integration is not configured",
            )

    @staticmethod
    def _json_or_text(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            return {"value": payload}
        except ValueError:
            return {"raw": response.text}

    @staticmethod
    def normalize_phone_number(raw_number: str) -> str:
        cleaned = re.sub(r"[^0-9+]", "", raw_number.strip())
        if not cleaned:
            raise AppException(status_code=422, code="invalid_phone_number", message="Recipient WhatsApp number is invalid")

        if cleaned.startswith("+"):
            digits = cleaned[1:]
        else:
            digits = cleaned

        if digits.startswith("00"):
            digits = digits[2:]

        if len(digits) == 10:
            digits = f"{settings.whatsapp_default_country_code}{digits}"

        if not digits.isdigit() or len(digits) < 8:
            raise AppException(status_code=422, code="invalid_phone_number", message="Recipient WhatsApp number is invalid")

        return f"+{digits}"

    @staticmethod
    def _should_retry(response: httpx.Response) -> bool:
        return response.status_code == 429 or response.status_code >= 500

    @property
    def _base_url(self) -> str:
        return f"{settings.whatsapp_api_base_url.rstrip('/')}/{settings.whatsapp_api_version}"

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.whatsapp_access_token}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_configuration()

        attempts = max(1, settings.whatsapp_retry_attempts)
        url = f"{self._base_url}/{path.lstrip('/')}"

        for attempt in range(1, attempts + 1):
            try:
                with httpx.Client(timeout=settings.whatsapp_request_timeout_seconds) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        headers=self._auth_headers,
                        json=json_payload,
                        data=form_data,
                        files=files,
                    )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                is_retryable = attempt < attempts
                logger.warning(
                    "whatsapp.request_transport_failure",
                    attempt=attempt,
                    retrying=is_retryable,
                    error=str(exc),
                    url=url,
                )
                if is_retryable:
                    time.sleep(0.5 * attempt)
                    continue
                raise AppException(
                    status_code=502,
                    code="whatsapp_transport_error",
                    message="Unable to reach WhatsApp provider",
                ) from exc

            payload = self._json_or_text(response)
            if response.status_code < 400:
                return payload

            is_retryable = self._should_retry(response) and attempt < attempts
            logger.warning(
                "whatsapp.request_failed",
                attempt=attempt,
                retrying=is_retryable,
                status_code=response.status_code,
                url=url,
                response_payload=payload,
            )

            if is_retryable:
                time.sleep(0.5 * attempt)
                continue

            raise AppException(
                status_code=502,
                code="whatsapp_api_error",
                message=f"WhatsApp provider rejected request (HTTP {response.status_code})",
            )

        raise AppException(status_code=500, code="whatsapp_request_failed", message="WhatsApp request failed")

    def log_whatsapp_event(
        self,
        *,
        module_type: WhatsAppModuleType,
        reference_id: int,
        recipient_no: str,
        message_type: WhatsAppMessageType,
        status: WhatsAppStatus,
        payload_json: dict[str, Any],
        customer_id: int | None = None,
        vendor_id: int | None = None,
        template_name: str | None = None,
        media_id: str | None = None,
        provider_message_id: str | None = None,
        error_message: str | None = None,
    ) -> WhatsAppLog:
        log_row = WhatsAppLog(
            module_type=module_type,
            reference_id=reference_id,
            customer_id=customer_id,
            vendor_id=vendor_id,
            recipient_no=recipient_no,
            message_type=message_type,
            template_name=template_name,
            media_id=media_id,
            provider_message_id=provider_message_id,
            status=status,
            error_message=error_message,
            payload_json=payload_json,
        )
        return self.repo.create(log_row)

    def upload_media(self, file_path: str | Path) -> str:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise AppException(status_code=404, code="media_file_not_found", message="File for upload does not exist")

        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        response_payload = self._request(
            "POST",
            f"{settings.whatsapp_phone_number_id}/media",
            form_data={
                "messaging_product": "whatsapp",
                "type": mime_type,
            },
            files={"file": (path.name, path.read_bytes(), mime_type)},
        )

        media_id = response_payload.get("id")
        if not isinstance(media_id, str) or not media_id:
            raise AppException(status_code=502, code="whatsapp_media_upload_failed", message="Media upload failed")

        return media_id

    @staticmethod
    def _extract_message_id(payload: dict[str, Any]) -> str | None:
        messages = payload.get("messages")
        if isinstance(messages, list) and messages:
            first = messages[0]
            if isinstance(first, dict):
                message_id = first.get("id")
                if isinstance(message_id, str) and message_id:
                    return message_id
        return None

    def send_text_message(
        self,
        *,
        module_type: WhatsAppModuleType,
        reference_id: int,
        recipient_no: str,
        message_body: str,
        customer_id: int | None = None,
        vendor_id: int | None = None,
        raise_on_error: bool = True,
    ) -> WhatsAppSendResult:
        normalized_no = self.normalize_phone_number(recipient_no)
        payload = {
            "messaging_product": "whatsapp",
            "to": normalized_no,
            "type": "text",
            "text": {"body": message_body},
        }

        try:
            response_payload = self._request("POST", f"{settings.whatsapp_phone_number_id}/messages", json_payload=payload)
            provider_message_id = self._extract_message_id(response_payload)
            status = WhatsAppStatus.SENT if provider_message_id else WhatsAppStatus.FAILED
            error_message = None if provider_message_id else "Provider message ID missing in response"

            log_row = self.log_whatsapp_event(
                module_type=module_type,
                reference_id=reference_id,
                customer_id=customer_id,
                vendor_id=vendor_id,
                recipient_no=normalized_no,
                message_type=WhatsAppMessageType.TEXT,
                status=status,
                provider_message_id=provider_message_id,
                payload_json={"request": payload, "response": response_payload},
                error_message=error_message,
            )

            if status == WhatsAppStatus.FAILED and raise_on_error:
                raise AppException(
                    status_code=502,
                    code="whatsapp_provider_message_id_missing",
                    message="WhatsApp provider did not confirm message delivery",
                )

            return WhatsAppSendResult(
                status=status,
                provider_message_id=provider_message_id,
                response_payload=response_payload,
                whatsapp_log_id=log_row.id,
                error_message=error_message,
            )

        except AppException as exc:
            log_row = self.log_whatsapp_event(
                module_type=module_type,
                reference_id=reference_id,
                customer_id=customer_id,
                vendor_id=vendor_id,
                recipient_no=normalized_no,
                message_type=WhatsAppMessageType.TEXT,
                status=WhatsAppStatus.FAILED,
                payload_json={"request": payload, "error": exc.message},
                error_message=exc.message,
            )
            if raise_on_error:
                raise
            return WhatsAppSendResult(
                status=WhatsAppStatus.FAILED,
                error_message=exc.message,
                whatsapp_log_id=log_row.id,
            )

    def send_template_message(
        self,
        *,
        module_type: WhatsAppModuleType,
        reference_id: int,
        recipient_no: str,
        template_name: str,
        language_code: str = "en",
        components: list[dict[str, Any]] | None = None,
        customer_id: int | None = None,
        vendor_id: int | None = None,
        raise_on_error: bool = True,
    ) -> WhatsAppSendResult:
        normalized_no = self.normalize_phone_number(recipient_no)
        template_payload: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template_payload["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "to": normalized_no,
            "type": "template",
            "template": template_payload,
        }

        try:
            response_payload = self._request("POST", f"{settings.whatsapp_phone_number_id}/messages", json_payload=payload)
            provider_message_id = self._extract_message_id(response_payload)
            status = WhatsAppStatus.SENT if provider_message_id else WhatsAppStatus.FAILED
            error_message = None if provider_message_id else "Provider message ID missing in response"

            log_row = self.log_whatsapp_event(
                module_type=module_type,
                reference_id=reference_id,
                customer_id=customer_id,
                vendor_id=vendor_id,
                recipient_no=normalized_no,
                message_type=WhatsAppMessageType.TEMPLATE,
                template_name=template_name,
                status=status,
                provider_message_id=provider_message_id,
                payload_json={"request": payload, "response": response_payload},
                error_message=error_message,
            )

            if status == WhatsAppStatus.FAILED and raise_on_error:
                raise AppException(
                    status_code=502,
                    code="whatsapp_provider_message_id_missing",
                    message="WhatsApp provider did not confirm message delivery",
                )

            return WhatsAppSendResult(
                status=status,
                provider_message_id=provider_message_id,
                response_payload=response_payload,
                whatsapp_log_id=log_row.id,
                error_message=error_message,
            )
        except AppException as exc:
            log_row = self.log_whatsapp_event(
                module_type=module_type,
                reference_id=reference_id,
                customer_id=customer_id,
                vendor_id=vendor_id,
                recipient_no=normalized_no,
                message_type=WhatsAppMessageType.TEMPLATE,
                template_name=template_name,
                status=WhatsAppStatus.FAILED,
                payload_json={"request": payload, "error": exc.message},
                error_message=exc.message,
            )
            if raise_on_error:
                raise
            return WhatsAppSendResult(
                status=WhatsAppStatus.FAILED,
                error_message=exc.message,
                whatsapp_log_id=log_row.id,
            )

    def send_document_message(
        self,
        *,
        module_type: WhatsAppModuleType,
        reference_id: int,
        recipient_no: str,
        document_name: str,
        caption: str | None = None,
        customer_id: int | None = None,
        vendor_id: int | None = None,
        media_id: str | None = None,
        document_link: str | None = None,
        raise_on_error: bool = True,
    ) -> WhatsAppSendResult:
        if not media_id and not document_link:
            raise AppException(
                status_code=422,
                code="missing_document_reference",
                message="Either media_id or document_link must be provided",
            )

        normalized_no = self.normalize_phone_number(recipient_no)
        document_payload: dict[str, Any] = {
            "filename": document_name,
        }
        if caption:
            document_payload["caption"] = caption
        if media_id:
            document_payload["id"] = media_id
        elif document_link:
            document_payload["link"] = document_link

        payload = {
            "messaging_product": "whatsapp",
            "to": normalized_no,
            "type": "document",
            "document": document_payload,
        }

        try:
            response_payload = self._request("POST", f"{settings.whatsapp_phone_number_id}/messages", json_payload=payload)
            provider_message_id = self._extract_message_id(response_payload)
            status = WhatsAppStatus.SENT if provider_message_id else WhatsAppStatus.FAILED
            error_message = None if provider_message_id else "Provider message ID missing in response"

            log_row = self.log_whatsapp_event(
                module_type=module_type,
                reference_id=reference_id,
                customer_id=customer_id,
                vendor_id=vendor_id,
                recipient_no=normalized_no,
                message_type=WhatsAppMessageType.DOCUMENT,
                status=status,
                media_id=media_id,
                provider_message_id=provider_message_id,
                payload_json={"request": payload, "response": response_payload},
                error_message=error_message,
            )

            if status == WhatsAppStatus.FAILED and raise_on_error:
                raise AppException(
                    status_code=502,
                    code="whatsapp_provider_message_id_missing",
                    message="WhatsApp provider did not confirm document delivery",
                )

            return WhatsAppSendResult(
                status=status,
                provider_message_id=provider_message_id,
                media_id=media_id,
                response_payload=response_payload,
                whatsapp_log_id=log_row.id,
                error_message=error_message,
            )
        except AppException as exc:
            log_row = self.log_whatsapp_event(
                module_type=module_type,
                reference_id=reference_id,
                customer_id=customer_id,
                vendor_id=vendor_id,
                recipient_no=normalized_no,
                message_type=WhatsAppMessageType.DOCUMENT,
                status=WhatsAppStatus.FAILED,
                media_id=media_id,
                payload_json={"request": payload, "error": exc.message},
                error_message=exc.message,
            )
            if raise_on_error:
                raise
            return WhatsAppSendResult(
                status=WhatsAppStatus.FAILED,
                media_id=media_id,
                error_message=exc.message,
                whatsapp_log_id=log_row.id,
            )

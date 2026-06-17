from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings
from app.core.exceptions import AppException


def build_media_file_reference(file_path: Path) -> str:
    media_root = settings.media_root_path.resolve()
    try:
        return file_path.resolve().relative_to(media_root).as_posix()
    except ValueError as exc:
        raise AppException(
            status_code=500,
            code="document_file_outside_media_root",
            message="Generated document file is outside the configured media root",
        ) from exc


def resolve_media_file_reference(
    file_reference: str | None,
    *,
    allowed_dir: Path,
    invalid_code: str,
    missing_code: str,
    missing_message: str,
) -> Path:
    if not file_reference or not file_reference.strip():
        raise AppException(status_code=422, code=missing_code, message=missing_message)

    relative_reference = _normalize_file_reference(file_reference)
    candidate = (settings.media_root_path / relative_reference).resolve()
    allowed_root = allowed_dir.resolve()

    try:
        candidate.relative_to(allowed_root)
    except ValueError as exc:
        raise AppException(status_code=422, code=invalid_code, message="Document file reference is invalid") from exc

    if not candidate.exists() or not candidate.is_file():
        raise AppException(status_code=404, code=missing_code, message=missing_message)

    return candidate


def _normalize_file_reference(file_reference: str) -> str:
    raw_reference = file_reference.strip()
    parsed = urlparse(raw_reference)
    path_value = parsed.path if parsed.scheme else raw_reference

    if path_value.startswith(settings.media_url_prefix):
        path_value = path_value[len(settings.media_url_prefix) :].lstrip("/")

    if path_value.startswith("/") or path_value.startswith("\\"):
        raise AppException(
            status_code=422,
            code="invalid_document_file_reference",
            message="Document file reference is invalid",
        )

    return path_value

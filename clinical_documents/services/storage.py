"""Almacenamiento privado de archivos clínicos (ADR-026, Stage 3).

Nunca sirve un archivo bajo una ruta pública fija (no usa `MEDIA_ROOT`/
`MEDIA_URL` — ver `TeCuidoApp.settings.CLINICAL_DOCUMENTS_STORAGE_ROOT`).
`storage_key` se genera siempre en servidor (UUID) — el nombre original
suministrado por el cliente nunca participa en la ruta física, lo cual
hace la path traversal estructuralmente imposible (no hay entrada de
usuario en la ruta), en vez de depender de sanitizar ese nombre.

MIME real verificado por contenido (magic bytes, vía `filetype` — pura
Python, sin dependencia de `libmagic` a nivel de sistema operativo) nunca
solo por el header `Content-Type`/la extensión declarada por el cliente
(`phase-4-security-and-privacy.md` §3).
"""

import uuid
from pathlib import Path

import filetype
from django.conf import settings
from django.utils import timezone as dj_timezone

from medical_records.services.exceptions import DocumentStorageError, DocumentValidationError

# Fase 4 §9.1 (phase-4-documents.md) — tipos permitidos inicialmente: PDF
# e imágenes comunes. Mapa mime→extensiones válidas (nunca se confía en
# una sola sin la otra).
ALLOWED_MIME_TO_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}

DEFAULT_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _storage_root() -> Path:
    root = Path(settings.CLINICAL_DOCUMENTS_STORAGE_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    return root


def max_size_bytes() -> int:
    return getattr(settings, "CLINICAL_DOCUMENTS_MAX_UPLOAD_SIZE_BYTES", DEFAULT_MAX_SIZE_BYTES)


def validate_and_detect_mime(*, content: bytes, declared_filename: str) -> str:
    """Valida tamaño, extensión declarada y contenido real; devuelve el
    MIME real verificado (nunca el declarado por el cliente).

    `DocumentValidationError` — mapeado por la API a 413 (tamaño) o 415
    (tipo no soportado) según corresponda (Stage 4)."""
    if not content:
        raise DocumentValidationError("El archivo está vacío.")
    if len(content) > max_size_bytes():
        raise DocumentValidationError("El archivo excede el tamaño máximo permitido.")

    declared_ext = Path(declared_filename or "").suffix.lower()
    kind = filetype.guess(content)
    real_mime = kind.mime if kind is not None else None

    if real_mime not in ALLOWED_MIME_TO_EXTENSIONS:
        raise DocumentValidationError(f"Tipo de archivo no soportado: {real_mime!r}")
    if declared_ext not in ALLOWED_MIME_TO_EXTENSIONS[real_mime]:
        # FL-004/SEC-Upload — la extensión declarada debe corresponder al
        # contenido real; un .pdf que en realidad es un ejecutable con
        # extensión falsificada se rechaza aquí.
        raise DocumentValidationError(
            f"La extensión '{declared_ext}' no corresponde al contenido real ({real_mime})."
        )
    return real_mime


def build_storage_key(*, mime_type: str) -> str:
    """Ruta segura, particionada por fecha, nunca derivada del nombre del
    cliente. Único punto de generación — ver docstring del módulo."""
    ext = next(iter(ALLOWED_MIME_TO_EXTENSIONS[mime_type]))
    now = dj_timezone.now()
    return f"{now:%Y/%m/%d}/{uuid.uuid4().hex}{ext}"


def save(*, storage_key: str, content: bytes) -> None:
    """Escribe el archivo en almacenamiento privado. No participa de
    ninguna transacción de base de datos (ADR-027) — se invoca siempre
    ANTES de abrir la transacción que crea el `ClinicalDocument`."""
    path = _storage_root() / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_bytes(content)
    except OSError as exc:
        raise DocumentStorageError(str(exc)) from exc


def read(*, storage_key: str) -> bytes:
    path = _storage_root() / storage_key
    try:
        return path.read_bytes()
    except OSError as exc:
        raise DocumentStorageError(str(exc)) from exc


def delete_best_effort(*, storage_key: str) -> None:
    """Compensación síncrona (ADR-027 §6): mejor esfuerzo, nunca lanza —
    un archivo huérfano que sobrevive no es un riesgo de seguridad (nunca
    referenciado por ningún `ClinicalDocument`)."""
    path = _storage_root() / storage_key
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.config import Settings, get_settings
from src.utils import normalize_storage_key


@dataclass(frozen=True, slots=True)
class StoredDocument:
    storage_key: str
    path: Path
    size_bytes: int


class DocumentStorage(Protocol):
    def save(self, storage_key: str, content: bytes) -> StoredDocument: ...

    def read(self, storage_key: str) -> bytes: ...

    def delete(self, storage_key: str) -> None: ...


class LocalDocumentStorage:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.root = Path(self.settings.document_storage_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, storage_key: str) -> Path:
        relative_path = normalize_storage_key(storage_key)
        resolved = (self.root / relative_path).resolve()
        root = self.root.resolve()
        if root not in resolved.parents and resolved != root:
            raise ValueError("Storage key escapes the configured storage root.")
        return resolved

    def save(self, storage_key: str, content: bytes) -> StoredDocument:
        path = self._resolve(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredDocument(
            storage_key=storage_key,
            path=path,
            size_bytes=len(content),
        )

    def read(self, storage_key: str) -> bytes:
        path = self._resolve(storage_key)
        return path.read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)
        if path.exists():
            path.unlink()

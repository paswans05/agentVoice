"""Abstract StorageProvider interface for agentVoice.

Business logic depends only on this interface so JSON/JSONL (default),
SQLite (optional), and PostgreSQL (future) remain interchangeable.
"""

from abc import ABC, abstractmethod
from typing import Any


class StorageProvider(ABC):
    """Abstract storage interface."""

    @abstractmethod
    def ensure_initialized(self) -> None:
        """Ensure required storage directories/structures exist."""

    @abstractmethod
    def is_writable(self) -> bool:
        """Return True if the storage backend can accept writes."""

    @abstractmethod
    def read_json(self, relative_path: str, default: Any = None) -> Any:
        """Read a JSON document at relative_path, returning default if missing."""

    @abstractmethod
    def write_json(self, relative_path: str, payload: Any) -> None:
        """Atomically write a JSON-serializable payload to relative_path."""

    @abstractmethod
    def delete_file(self, relative_path: str) -> bool:
        """Delete a stored file if it exists. Returns True if deleted."""

    @abstractmethod
    def list_files(self, relative_dir: str, suffix: str = ".json") -> list[str]:
        """List relative paths of files in a directory matching suffix."""

    @abstractmethod
    def append_jsonl(self, relative_path: str, record: dict[str, Any]) -> None:
        """Append a single JSON record as a line to a JSONL file."""

    @abstractmethod
    def read_jsonl(self, relative_path: str) -> list[dict[str, Any]]:
        """Read all valid records from a JSONL file."""

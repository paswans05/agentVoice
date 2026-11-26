"""Default local-first JSON/JSONL storage provider.

Features:
- Path traversal protection
- Atomic writes via temporary file + os.replace
- Cross-platform file locking for JSONL appends
- Interrupted-write recovery (ignores trailing incomplete JSONL line or leftover .tmp files)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .base import StorageProvider

logger = logging.getLogger(__name__)

DEFAULT_SUBDIRS = (
    "config",
    "agents",
    "leads",
    "conversations",
    "campaigns",
    "calls",
    "knowledge",
    "models",
    "logs",
    "backups",
)


class StoragePathError(ValueError):
    """Raised when a storage path escapes the configured data directory."""


class JSONStorageProvider(StorageProvider):
    """File-based JSON and JSONL storage provider."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir).resolve()
        self._thread_lock = threading.RLock()

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve relative_path inside base_dir, rejecting traversal attempts."""
        candidate = (self.base_dir / relative_path).resolve()
        try:
            candidate.relative_to(self.base_dir)
        except ValueError as exc:
            raise StoragePathError(f"Unsafe storage path: {relative_path}") from exc
        return candidate

    @contextmanager
    def _file_lock(self, lock_path: Path) -> Iterator[None]:
        """Cross-platform advisory file lock paired with an in-process RLock."""
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._thread_lock:
            with open(lock_path, "a+", encoding="utf-8") as lock_file:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                    try:
                        yield
                    finally:
                        lock_file.seek(0)
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def ensure_initialized(self) -> None:
        """Create base directory, subdirectories, and default config files if absent."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for subdir in DEFAULT_SUBDIRS:
            (self.base_dir / subdir).mkdir(parents=True, exist_ok=True)

        app_config_path = "config/app.json"
        if not self._resolve_safe_path(app_config_path).exists():
            self.write_json(
                app_config_path,
                {
                    "name": "agentVoice",
                    "version": "0.1.0",
                    "initialized_at": datetime.now(timezone.utc).isoformat(),
                    "storage_backend": "json",
                },
            )

    def is_writable(self) -> bool:
        """Check whether base_dir is writable by performing a quick temp file check."""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=self.base_dir, prefix=".health_", suffix=".tmp")
            os.close(fd)
            os.unlink(tmp_path)
            return True
        except OSError as exc:
            logger.warning("Storage writability check failed: %s", exc)
            return False

    def read_json(self, relative_path: str, default: Any = None) -> Any:
        target = self._resolve_safe_path(relative_path)
        if not target.exists():
            return default
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_json(self, relative_path: str, payload: Any) -> None:
        target = self._resolve_safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        lock_path = target.with_suffix(target.suffix + ".lock")

        with self._file_lock(lock_path):
            fd, tmp_name = tempfile.mkstemp(
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
            )
            tmp_path = Path(tmp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                    json.dump(payload, tmp_file, indent=2, ensure_ascii=False)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())
                os.replace(tmp_path, target)
            except Exception:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                raise

    def delete_file(self, relative_path: str) -> bool:
        target = self._resolve_safe_path(relative_path)
        if target.exists() and target.is_file():
            target.unlink()
            return True
        return False

    def list_files(self, relative_dir: str, suffix: str = ".json") -> list[str]:
        target_dir = self._resolve_safe_path(relative_dir)
        if not target_dir.exists() or not target_dir.is_dir():
            return []
        results: list[str] = []
        for entry in sorted(target_dir.iterdir()):
            if entry.is_file() and entry.name.endswith(suffix) and not entry.name.startswith("."):
                results.append(entry.relative_to(self.base_dir).as_posix())
        return results

    def append_jsonl(self, relative_path: str, record: dict[str, Any]) -> None:
        target = self._resolve_safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        lock_path = target.with_suffix(target.suffix + ".lock")
        line = json.dumps(record, ensure_ascii=False) + "\n"

        with self._file_lock(lock_path):
            with open(target, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())

    def read_jsonl(self, relative_path: str) -> list[dict[str, Any]]:
        target = self._resolve_safe_path(relative_path)
        if not target.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(target, "r", encoding="utf-8") as f:
            for idx, raw_line in enumerate(f, start=1):
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    records.append(json.loads(stripped))
                except json.JSONDecodeError:
                    logger.warning(
                        "Skipping malformed JSONL line %d in %s (interrupted write recovery)",
                        idx,
                        relative_path,
                    )
        return records

    def create_backup(self, label: str = "manual") -> Path:
        """Create a timestamped zip backup of data subdirectories (excluding backups/)."""
        self.ensure_initialized()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_label = "".join(c for c in label if c.isalnum() or c in ("-", "_")) or "manual"
        archive_base = self.base_dir / "backups" / f"agentvoice-{safe_label}-{timestamp}"
        staging_dir = Path(tempfile.mkdtemp(prefix="agentvoice_backup_"))
        try:
            for subdir in DEFAULT_SUBDIRS:
                if subdir == "backups":
                    continue
                src = self.base_dir / subdir
                if src.exists():
                    shutil.copytree(src, staging_dir / subdir)
            archive_path = shutil.make_archive(str(archive_base), "zip", root_dir=staging_dir)
            return Path(archive_path)
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

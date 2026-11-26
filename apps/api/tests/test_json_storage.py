"""Tests for JSONStorageProvider atomic writes, locking, and recovery."""

from pathlib import Path
import zipfile

import pytest

from app.providers.storage import JSONStorageProvider, StoragePathError


def test_initialize_creates_structure(tmp_path: Path) -> None:
    storage = JSONStorageProvider(tmp_path)
    storage.ensure_initialized()

    assert (tmp_path / "config" / "app.json").exists()
    assert (tmp_path / "agents").is_dir()
    assert (tmp_path / "leads").is_dir()
    assert (tmp_path / "backups").is_dir()
    assert storage.is_writable() is True


def test_atomic_json_write_read_list_delete(tmp_path: Path) -> None:
    storage = JSONStorageProvider(tmp_path)
    storage.ensure_initialized()

    payload = {"id": "agent_001", "name": "Asha", "language": "hinglish"}
    storage.write_json("agents/agent_001.json", payload)

    assert storage.read_json("agents/agent_001.json") == payload
    assert storage.list_files("agents") == ["agents/agent_001.json"]
    assert storage.delete_file("agents/agent_001.json") is True
    assert storage.read_json("agents/agent_001.json", default=None) is None


def test_jsonl_append_and_interrupted_write_recovery(tmp_path: Path) -> None:
    storage = JSONStorageProvider(tmp_path)
    storage.ensure_initialized()

    storage.append_jsonl("leads/leads.jsonl", {"id": "lead_1", "name": "Rohan"})
    # Simulate an interrupted trailing line
    with open(tmp_path / "leads" / "leads.jsonl", "a", encoding="utf-8") as f:
        f.write('{"id": "lead_broken", "name": \n')
    storage.append_jsonl("leads/leads.jsonl", {"id": "lead_2", "name": "Priya"})

    records = storage.read_jsonl("leads/leads.jsonl")
    assert len(records) == 2
    assert records[0]["id"] == "lead_1"
    assert records[1]["id"] == "lead_2"


def test_path_traversal_rejected(tmp_path: Path) -> None:
    storage = JSONStorageProvider(tmp_path)
    storage.ensure_initialized()

    with pytest.raises(StoragePathError):
        storage.write_json("../escape.json", {"bad": True})

    with pytest.raises(StoragePathError):
        storage.read_json("../../secret.json")


def test_create_backup_zip(tmp_path: Path) -> None:
    storage = JSONStorageProvider(tmp_path)
    storage.ensure_initialized()
    storage.write_json("agents/agent_001.json", {"id": "agent_001"})

    archive_path = storage.create_backup("test")
    assert archive_path.exists()
    with zipfile.ZipFile(archive_path, "r") as zf:
        names = zf.namelist()
        assert "agents/agent_001.json" in names
        assert "config/app.json" in names

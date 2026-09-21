import sqlite3
from pathlib import Path

import pytest
from src.pipeline import load_to_db


def record_database(path: Path, count: int) -> None:
    with sqlite3.connect(path / "chroma.sqlite3") as connection:
        connection.execute("CREATE TABLE embeddings (id INTEGER PRIMARY KEY)")
        connection.executemany("INSERT INTO embeddings VALUES (?)", ((i,) for i in range(count)))
        connection.execute("CREATE TABLE embeddings_queue (seq_id INTEGER PRIMARY KEY)")
        connection.executemany(
            "INSERT INTO embeddings_queue VALUES (?)", ((i,) for i in range(count))
        )


def test_retained_replay_logs_do_not_block_persisted_records(tmp_path, monkeypatch):
    record_database(tmp_path, 4)
    monkeypatch.setattr(
        load_to_db.time, "sleep", lambda _: pytest.fail("must not wait for WAL purge")
    )
    load_to_db._wait_for_persisted_records(tmp_path, expected_count=4)
    with sqlite3.connect(tmp_path / "chroma.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM embeddings_queue").fetchone()[0] == 4


def test_waits_until_expected_records_are_durable(tmp_path, monkeypatch):
    record_database(tmp_path, 3)
    waits = []

    def persist(_):
        waits.append(True)
        with sqlite3.connect(tmp_path / "chroma.sqlite3") as connection:
            connection.execute("INSERT INTO embeddings VALUES (3)")

    monkeypatch.setattr(load_to_db.time, "sleep", persist)
    load_to_db._wait_for_persisted_records(tmp_path, expected_count=4)
    assert len(waits) == 1


@pytest.mark.parametrize("count", [0, 3, 5])
def test_missing_or_extra_records_fail_closed(tmp_path, count):
    record_database(tmp_path, count)
    with pytest.raises(load_to_db.PipelineError, match="expected=4"):
        load_to_db._wait_for_persisted_records(tmp_path, expected_count=4, timeout_seconds=0)


@pytest.mark.parametrize("corrupt", [False, True])
def test_missing_or_unreadable_database_does_not_pass(tmp_path, corrupt):
    if corrupt:
        (tmp_path / "chroma.sqlite3").write_text("not a database", encoding="utf-8")
    with pytest.raises(load_to_db.PipelineError, match="持久化记录等待超时"):
        load_to_db._wait_for_persisted_records(tmp_path, expected_count=4, timeout_seconds=0)

import gzip
import importlib.util
import os
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "db_backup", Path(__file__).resolve().parent.parent / "scripts" / "db_backup.py"
)
db_backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db_backup)


class FakeStdout:
    def __init__(self, chunks=b"", returncode=0):
        self.chunks = chunks
        self.returncode = returncode
        self.written = b""
        self.closed = False

    def write(self, data):
        self.written += data

    def close(self):
        self.closed = True


class FakeProc:
    def __init__(self, stdout=None, returncode=0, stdin=None):
        self.stdout = stdout
        self.stdin = stdin
        self.returncode = returncode

    def wait(self):
        return self.returncode


class TestResolveOutDir:
    def test_defaults_to_home_backups(self):
        assert db_backup.resolve_out_dir() == Path.home() / "backups"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("BACKUP_DIR", "/tmp/env_backups")
        assert db_backup.resolve_out_dir() == Path("/tmp/env_backups")

    def test_explicit_arg_wins(self, monkeypatch, tmp_path):
        monkeypatch.setenv("BACKUP_DIR", "/tmp/env_backups")
        assert db_backup.resolve_out_dir(tmp_path) == tmp_path


class TestDefaultContainer:
    def test_explicit_arg_wins(self):
        assert db_backup.default_container("my-pg") == "my-pg"

    def test_env_var_wins_over_detection(self, monkeypatch):
        monkeypatch.setattr(db_backup, "_running_containers", lambda: {"dev-pg"})
        monkeypatch.setenv("PG_CONTAINER", "env-pg")
        assert db_backup.default_container() == "env-pg"

    def test_detects_dev_pg(self, monkeypatch):
        monkeypatch.setattr(db_backup, "_running_containers", lambda: {"dev-pg"})
        monkeypatch.setattr(db_backup, "_compose_services", lambda: {"postgres"})
        assert db_backup.default_container() == "dev-pg"

    def test_detects_compose_postgres(self, monkeypatch):
        monkeypatch.setattr(db_backup, "_running_containers", lambda: set())
        monkeypatch.setattr(db_backup, "_compose_services", lambda: {"postgres"})
        assert db_backup.default_container() == "compose:postgres"

    def test_raises_when_none_running(self, monkeypatch):
        monkeypatch.setattr(db_backup, "_running_containers", lambda: set())
        monkeypatch.setattr(db_backup, "_compose_services", lambda: set())
        with pytest.raises(RuntimeError):
            db_backup.default_container()


class TestCommands:
    def test_pg_dump_dev_container(self):
        assert db_backup.pg_dump_command("dev-pg") == [
            "docker",
            "exec",
            "dev-pg",
            "pg_dump",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "--no-owner",
        ]

    def test_pg_dump_compose(self):
        assert db_backup.pg_dump_command("compose:postgres")[:4] == [
            "docker",
            "compose",
            "exec",
            "-T",
        ]

    def test_psql_dev_container_uses_stdin(self):
        assert "exec" in db_backup.psql_command("dev-pg")
        assert "-i" in db_backup.psql_command("dev-pg")

    def test_psql_compose_uses_stdin(self):
        assert "exec" in db_backup.psql_command("compose:postgres")
        assert "-T" in db_backup.psql_command("compose:postgres")


class TestBackup:
    def test_creates_gzipped_dump(self, tmp_path, monkeypatch):
        proc = FakeProc(stdout=[b"line1\n", b"line2\n"], returncode=0)
        monkeypatch.setattr(db_backup.subprocess, "Popen", lambda *a, **k: proc)

        path = db_backup.backup("dev-pg", tmp_path)

        assert path.startswith(str(tmp_path))
        assert path.endswith(".sql.gz")
        with gzip.open(path, "rb") as f:
            assert f.read() == b"line1\nline2\n"

    def test_unlinks_partial_dump_on_failure(self, tmp_path, monkeypatch):
        proc = FakeProc(stdout=[b"partial"], returncode=1)
        monkeypatch.setattr(db_backup.subprocess, "Popen", lambda *a, **k: proc)

        with pytest.raises(RuntimeError):
            db_backup.backup("dev-pg", tmp_path)

        assert list(tmp_path.iterdir()) == []


class TestRestore:
    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            db_backup.restore("dev-pg", "/nonexistent/dump.sql")

    def test_streams_plain_dump(self, tmp_path, monkeypatch):
        dump = tmp_path / "dump.sql"
        dump.write_bytes(b"SELECT 1;\n")
        stdin = FakeStdout()
        monkeypatch.setattr(
            db_backup.subprocess,
            "Popen",
            lambda *a, **k: FakeProc(stdin=stdin, returncode=0),
        )

        db_backup.restore("dev-pg", dump)

        assert stdin.written == b"SELECT 1;\n"
        assert stdin.closed

    def test_gunzips_dump(self, tmp_path, monkeypatch):
        dump = tmp_path / "dump.sql.gz"
        with gzip.open(dump, "wb") as f:
            f.write(b"SELECT 2;\n")
        stdin = FakeStdout()
        monkeypatch.setattr(
            db_backup.subprocess,
            "Popen",
            lambda *a, **k: FakeProc(stdin=stdin, returncode=0),
        )

        db_backup.restore("dev-pg", dump)

        assert stdin.written == b"SELECT 2;\n"

    def test_raises_on_psql_failure(self, tmp_path, monkeypatch):
        dump = tmp_path / "dump.sql"
        dump.write_bytes(b"SELECT 1;\n")
        monkeypatch.setattr(
            db_backup.subprocess,
            "Popen",
            lambda *a, **k: FakeProc(stdin=FakeStdout(), returncode=1),
        )

        with pytest.raises(RuntimeError):
            db_backup.restore("dev-pg", dump)


class TestListBackups:
    def test_returns_empty_for_missing_dir(self, tmp_path):
        assert db_backup.list_backups(tmp_path / "nope") == []

    def test_returns_sorted_entries(self, tmp_path):
        (tmp_path / "trading_db_20260805_160000.sql.gz").touch()
        (tmp_path / "trading_db_20260805_150000.sql.gz").touch()
        (tmp_path / "other.sql.gz").touch()

        entries = db_backup.list_backups(tmp_path)

        assert [entry[0] for entry in entries] == [
            "trading_db_20260805_150000.sql.gz",
            "trading_db_20260805_160000.sql.gz",
        ]
        assert all(len(entry) == 3 for entry in entries)


class TestMain:
    def test_list_command_returns_zero(self, tmp_path, monkeypatch):
        assert db_backup.main(["list", "--out-dir", str(tmp_path)]) == 0

    def test_backup_command_returns_zero(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_backup, "default_container", lambda *a, **k: "dev-pg")
        proc = FakeProc(stdout=[b"data"], returncode=0)
        monkeypatch.setattr(db_backup.subprocess, "Popen", lambda *a, **k: proc)
        assert db_backup.main(["backup", "--out-dir", str(tmp_path)]) == 0

    def test_restore_missing_file_returns_one(self, tmp_path):
        assert db_backup.main(["restore", str(tmp_path / "nope.sql")]) == 1

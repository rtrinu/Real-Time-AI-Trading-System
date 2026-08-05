#!/usr/bin/env python3
"""Create and restore PostgreSQL backups for the trading system.

Targets either a local dev container (dev-pg) or a docker compose `postgres`
service, auto-detecting which one is running. Python stdlib only.
"""

import argparse
import datetime
import gzip
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_OUT_DIR = Path.home() / "backups"
PGUSER = "postgres"
PGDATABASE = "postgres"
BACKUP_PREFIX = "trading_db"
TIMESTAMP_FMT = "%Y%m%d_%H%M%S"


def resolve_out_dir(out_dir=None):
    """Backup directory: explicit arg, BACKUP_DIR env, or ~/backups."""
    return Path(out_dir or os.environ.get("BACKUP_DIR") or DEFAULT_OUT_DIR)


def _running_containers():
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return {name.strip() for name in result.stdout.splitlines() if name.strip()}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()


def _compose_services():
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--services", "--status", "running"],
            capture_output=True,
            text=True,
            check=True,
        )
        return {name.strip() for name in result.stdout.splitlines() if name.strip()}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()


def default_container(container=None):
    """Resolve the Postgres target: explicit arg, PG_CONTAINER env, dev-pg, or compose postgres."""
    if container:
        return container
    if os.environ.get("PG_CONTAINER"):
        return os.environ["PG_CONTAINER"]
    if "dev-pg" in _running_containers():
        return "dev-pg"
    if "postgres" in _compose_services():
        return "compose:postgres"
    raise RuntimeError(
        "No PostgreSQL container detected. Start dev-pg or the compose postgres "
        "service, or pass --container."
    )


def pg_dump_command(container):
    base = (
        ["docker", "compose", "exec", "-T", container.split(":", 1)[1]]
        if container.startswith("compose:")
        else ["docker", "exec", container]
    )
    return base + ["pg_dump", "-U", PGUSER, "-d", PGDATABASE, "--no-owner"]


def psql_command(container):
    base = (
        ["docker", "compose", "exec", "-T", container.split(":", 1)[1]]
        if container.startswith("compose:")
        else ["docker", "exec", "-i", container]
    )
    return base + ["psql", "-U", PGUSER, "-d", PGDATABASE]


def backup(container, out_dir=None):
    """Create a timestamped gzipped SQL dump; returns the file path."""
    out_dir = resolve_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime(TIMESTAMP_FMT)
    path = out_dir / f"{BACKUP_PREFIX}_{timestamp}.sql.gz"
    try:
        proc = subprocess.Popen(pg_dump_command(container), stdout=subprocess.PIPE)
        with gzip.open(path, "wb") as f:
            for chunk in proc.stdout:
                f.write(chunk)
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"pg_dump failed with exit code {proc.returncode}")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return str(path)


def restore(container, dump_path):
    """Plain re-load of a .sql or .sql.gz dump into the target database."""
    path = Path(dump_path)
    if not path.is_file():
        raise FileNotFoundError(f"Backup file not found: {path}")
    proc = subprocess.Popen(psql_command(container), stdin=subprocess.PIPE)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as f:
        for chunk in f:
            proc.stdin.write(chunk)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"psql restore failed with exit code {proc.returncode}")


def list_backups(out_dir=None):
    out_dir = resolve_out_dir(out_dir)
    if not out_dir.is_dir():
        return []
    entries = []
    for path in sorted(out_dir.glob(f"{BACKUP_PREFIX}_*.sql*")):
        stat = path.stat()
        modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime(TIMESTAMP_FMT)
        entries.append((path.name, stat.st_size, modified))
    return entries


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--container",
        help="Container name, or 'compose:<service>' (default: auto-detect).",
    )
    common.add_argument(
        "--out-dir",
        help=f"Backup directory (default: {DEFAULT_OUT_DIR}).",
    )
    parser = argparse.ArgumentParser(
        prog="db_backup",
        description="Create and restore PostgreSQL backups for the trading system.",
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("backup", parents=[common], help="Create a timestamped gzipped SQL dump.")
    p_restore = sub.add_parser(
        "restore", parents=[common], help="Restore from a .sql or .sql.gz dump."
    )
    p_restore.add_argument("dump_file", help="Path to the dump file.")
    sub.add_parser("list", parents=[common], help="List existing backups.")

    args = parser.parse_args(argv)

    try:
        if args.command == "backup":
            container = default_container(args.container)
            print(f"Backup created: {backup(container, args.out_dir)}")
        elif args.command == "restore":
            container = default_container(args.container)
            restore(container, args.dump_file)
            print(f"Restored: {args.dump_file}")
        elif args.command == "list":
            for name, size, modified in list_backups(args.out_dir):
                print(f"{modified}  {size:>10,}  {name}")
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

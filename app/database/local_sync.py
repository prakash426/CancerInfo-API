"""Preserving, explicit PostgreSQL-to-local-SQLite synchronization.

No source writes, no reseeding and no deletion of local-only rows or tables.
Prepare and validate a migrated working copy before replacing SQLite pages.
"""
from datetime import date, datetime
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time

from alembic import command
from sqlalchemy import Column, MetaData, Table, create_engine, inspect, select
from sqlalchemy.dialects.sqlite import insert

from app.database.migration_check import get_alembic_config, set_alembic_url_safe, verify_database_schema_at_head
from app.database.model_tables import CURRENT_MODEL_TABLES


def normalize(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [normalize(v) for v in value]
    return value


def sqlite_digest(connection):
    return hashlib.sha256("\n".join(connection.iterdump()).encode()).hexdigest()


def capture_live_rows(source_engine):
    """One read-only consistent snapshot, without connection details in output."""
    if source_engine.dialect.name != "postgresql":
        raise ValueError("The source must be PostgreSQL")
    with source_engine.connect().execution_options(isolation_level="REPEATABLE READ") as source:
        with source.begin():
            source.exec_driver_sql("SET TRANSACTION READ ONLY")
            metadata = MetaData()
            metadata.reflect(bind=source, schema="public")
            tables = {}
            rows = {}
            for table in metadata.sorted_tables:
                if table.name == "alembic_version":
                    continue
                if not table.primary_key.columns:
                    raise ValueError(f"Source table requires a primary key: {table.name}")
                tables[table.name] = table
                rows[table.name] = [dict(r) for r in source.execute(
                    select(table).order_by(*table.primary_key.columns)).mappings()]
    return tables, rows


def sync_local_database(source_engine, local_path, backup_path):
    local_path, backup_path = Path(local_path).resolve(), Path(backup_path).resolve()
    if local_path == backup_path or backup_path.exists():
        raise ValueError("Use a new, separate backup path")
    if not local_path.is_file():
        raise ValueError("Select an existing local SQLite file explicitly")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(local_path.as_uri() + "?mode=ro", uri=True)) as original:
        initial_digest = sqlite_digest(original)
        with closing(sqlite3.connect(backup_path)) as backup:
            original.backup(backup)
    backup_path.chmod(0o600)
    source_tables, source_rows = capture_live_rows(source_engine)
    result = {"source_counts": {name: len(rows) for name, rows in source_rows.items()},
              "local_only_rows_preserved": {}, "backup_created": True}
    with tempfile.TemporaryDirectory(prefix="ciapi-local-sync-", dir=local_path.parent) as folder:
        working_path = Path(folder) / "working.db"
        shutil.copyfile(backup_path, working_path)
        cfg = get_alembic_config()
        set_alembic_url_safe(cfg, "sqlite:///" + str(working_path))
        command.upgrade(cfg, "head")
        working = create_engine("sqlite:///" + str(working_path))
        try:
            # Some recovered 0003 SQLite corpora retain the earlier NOT NULL
            # country column despite the baseline model allowing NULL. Repair
            # this known permissive schema difference only in the working copy.
            country = next(c for c in inspect(working).get_columns("content_records") if c["name"] == "country_code")
            if not country["nullable"]:
                from alembic.migration import MigrationContext
                from alembic.operations import Operations
                with working.begin() as connection:
                    operations = Operations(MigrationContext.configure(connection))
                    with operations.batch_alter_table("content_records") as batch:
                        batch.alter_column("country_code", existing_type=country["type"], nullable=True)
            metadata = MetaData()
            metadata.reflect(bind=working)
            with working.begin() as target:
                for name, source_table in source_tables.items():
                    if name not in metadata.tables:
                        if name in CURRENT_MODEL_TABLES:
                            raise ValueError("Managed table missing after migration")
                        table = Table(name, metadata, *[
                            Column(column.name, column.type.as_generic(),
                                   primary_key=column.primary_key, nullable=column.nullable)
                            for column in source_table.columns])
                        table.create(target)
                    table = metadata.tables[name]
                    if not set(source_table.columns.keys()) <= set(table.columns.keys()):
                        raise ValueError(f"Local table has incompatible columns: {name}")
                    keys = [col.name for col in table.primary_key.columns]
                    if keys != [col.name for col in source_table.primary_key.columns]:
                        raise ValueError(f"Local table has incompatible primary key: {name}")
                    existing = {tuple(r) for r in target.execute(select(*(table.c[k] for k in keys)))}
                    incoming = {tuple(row[k] for k in keys) for row in source_rows[name]}
                    result["local_only_rows_preserved"][name] = len(existing - incoming)
                    # Source values are complete. Local-only columns and rows survive.
                    if source_rows[name]:
                        statement = insert(table)
                        updates = {c: statement.excluded[c] for c in source_table.columns.keys() if c not in keys}
                        if updates:
                            statement = statement.on_conflict_do_update(index_elements=keys, set_=updates)
                        else:
                            statement = statement.on_conflict_do_nothing(index_elements=keys)
                        target.execute(statement, source_rows[name])
                if target.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("Local foreign-key validation failed")
            verify_database_schema_at_head(working)
            # Compare every source value using typed JSON/boolean/date decoding.
            with working.connect() as target:
                for name, source_table in source_tables.items():
                    table = metadata.tables[name]
                    keys = [c.name for c in table.primary_key.columns]
                    actual = {tuple(r[k] for k in keys): dict(r) for r in target.execute(select(table)).mappings()}
                    for row in source_rows[name]:
                        stored = actual[tuple(row[k] for k in keys)]
                        for column, value in row.items():
                            if normalize(value) != normalize(stored[column]):
                                raise ValueError(f"Replica value comparison failed: {name}.{column}")
        finally:
            working.dispose()
        # Hold an exclusive destination lock and refuse intervening local edits.
        # SQLite backup replaces pages on the same inode, preserving open readers'
        # normal database change detection instead of swapping the database file.
        with closing(sqlite3.connect(local_path, timeout=5)) as target:
            target.execute("PRAGMA locking_mode=EXCLUSIVE")
            target.execute("BEGIN EXCLUSIVE")
            if sqlite_digest(target) != initial_digest:
                target.rollback()
                raise ValueError("Local data changed during preparation; refusing to overwrite")
            target.commit()
            deadline = time.monotonic() + 30
            def progress(status, remaining, total):
                if time.monotonic() > deadline:
                    raise TimeoutError("Local sync lock timed out")
            with closing(sqlite3.connect(working_path.as_uri() + "?mode=ro", uri=True)) as prepared:
                prepared.backup(target, pages=128, progress=progress, sleep=0.05)
    result["verified"] = True
    return result

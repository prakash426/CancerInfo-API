"""
Current-Model Manifest Module (CIAPI-L003)

Captures and compares exact ordered manifests for all 11 current-model tables:
- sources
- source_health
- cancers
- cancer_aliases
- source_documents
- content_records
- content_sources
- content_versions
- ingestion_jobs
- consensus_facts
- consensus_fact_sources

Includes primary keys, foreign-key values, aliases, citation fields,
content hashes, version numbers, created/updated timestamps, consensus
facts, and consensus source relationships.
"""
import hashlib
import json
from datetime import date, datetime
from typing import Any, Dict, List
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

CURRENT_MODEL_TABLES = [
    "sources",
    "source_health",
    "cancers",
    "cancer_aliases",
    "source_documents",
    "content_records",
    "content_sources",
    "content_versions",
    "ingestion_jobs",
    "consensus_facts",
    "consensus_fact_sources",
]


def _serialize_value(val: Any) -> Any:
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


def capture_current_model_manifest(engine: Engine) -> Dict[str, Any]:
    """
    Captures an exact, deterministic manifest of all current-model tables.
    Returns:
        dict containing:
        - tables: Dict[table_name, List[Dict[column_name, column_value]]]
        - row_counts: Dict[table_name, int]
        - total_rows: int
        - deterministic_digest: SHA-256 hex digest of serialized tables
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    missing = set(CURRENT_MODEL_TABLES) - existing_tables
    if missing:
        raise RuntimeError(f"Cannot capture complete manifest; missing tables: {sorted(missing)}")

    manifest_tables: Dict[str, List[Dict[str, Any]]] = {}
    row_counts: Dict[str, int] = {}
    total_rows = 0

    with engine.connect() as conn:
        for tbl in CURRENT_MODEL_TABLES:
            # Query all columns ordered by primary key id
            result = conn.execute(text(f"SELECT * FROM {tbl} ORDER BY id"))
            columns = list(result.keys())
            table_rows: List[Dict[str, Any]] = []

            for raw_row in result.fetchall():
                row_dict = {}
                for col_name, val in zip(columns, raw_row):
                    row_dict[col_name] = _serialize_value(val)
                table_rows.append(row_dict)

            manifest_tables[tbl] = table_rows
            row_counts[tbl] = len(table_rows)
            total_rows += len(table_rows)

    serialized = json.dumps(manifest_tables, sort_keys=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    return {
        "tables": manifest_tables,
        "row_counts": row_counts,
        "total_rows": total_rows,
        "deterministic_digest": digest,
    }


def compare_current_model_manifests(
    manifest_a: Dict[str, Any],
    manifest_b: Dict[str, Any],
    label_a: str = "Manifest A",
    label_b: str = "Manifest B",
) -> None:
    """
    Asserts exact equality of two manifests across all current-model tables,
    columns, foreign keys, timestamps, hashes, and relationships.
    """
    assert manifest_a["total_rows"] == manifest_b["total_rows"], (
        f"Total row count changed: {label_a}={manifest_a['total_rows']} vs {label_b}={manifest_b['total_rows']}"
    )

    for tbl in CURRENT_MODEL_TABLES:
        rows_a = manifest_a["tables"].get(tbl, [])
        rows_b = manifest_b["tables"].get(tbl, [])
        assert len(rows_a) == len(rows_b), (
            f"Table '{tbl}' row count mismatch: {label_a}={len(rows_a)} vs {label_b}={len(rows_b)}"
        )
        assert rows_a == rows_b, (
            f"Table '{tbl}' contents mismatch between {label_a} and {label_b}!"
        )

    assert manifest_a["deterministic_digest"] == manifest_b["deterministic_digest"], (
        f"Manifest digest mismatch! {label_a}={manifest_a['deterministic_digest']} vs {label_b}={manifest_b['deterministic_digest']}"
    )


def verify_foreign_key_integrity(engine: Engine) -> Dict[str, Any]:
    """
    Verifies foreign-key integrity across all 11 current-model tables.
    Asserts that zero orphaned foreign-key references exist in the database.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    missing = set(CURRENT_MODEL_TABLES) - existing_tables
    if missing:
        raise RuntimeError(f"Cannot verify integrity; missing tables: {sorted(missing)}")
    fks_checked = 0
    violations: List[str] = []

    with engine.connect() as conn:
        for tbl in CURRENT_MODEL_TABLES:
            if tbl not in existing_tables:
                continue
            for fk in inspector.get_foreign_keys(tbl):
                fks_checked += 1
                child_cols = fk["constrained_columns"]
                parent_tbl = fk["referred_table"]
                parent_cols = fk.get("referred_columns") or ["id"]
                if not child_cols or not parent_cols or len(child_cols) != len(parent_cols):
                    continue
                if parent_tbl not in existing_tables:
                    continue

                join_conditions = " AND ".join(
                    f"c.{c_col} = p.{p_col}" for c_col, p_col in zip(child_cols, parent_cols)
                )
                not_null_cond = " AND ".join(f"c.{c_col} IS NOT NULL" for c_col in child_cols)
                query = text(f"""
                    SELECT COUNT(*) FROM {tbl} c
                    WHERE {not_null_cond}
                      AND NOT EXISTS (
                          SELECT 1 FROM {parent_tbl} p WHERE {join_conditions}
                      )
                """)
                orphan_count = conn.execute(query).scalar() or 0
                if orphan_count > 0:
                    violations.append(
                        f"Table '{tbl}' has {orphan_count} orphan row(s) referencing missing parent in '{parent_tbl}' on {child_cols} -> {parent_cols}"
                    )

    if violations:
        raise AssertionError("Foreign-key integrity check failed:\n  - " + "\n  - ".join(violations))

    return {
        "status": "VALID",
        "foreign_keys_checked": fks_checked,
        "violations": 0,
    }

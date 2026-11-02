"""
Legacy cancer_content Table Auditing Module (CIAPI-L003)

Provides comprehensive structural and data integrity auditing for the
legacy 'cancer_content' table (5,628 rows, 22 columns) to guarantee
zero corruption, schema drift, or silent modification during migrations,
bootstrap operations, or application restarts.
"""
import hashlib
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


EXPECTED_LEGACY_COLUMNS = [
    "id",
    "content_id",
    "page_group_id",
    "cancer_name",
    "category",
    "normalized_category",
    "page_title",
    "page_slug",
    "content_title",
    "parent_heading",
    "section_path",
    "heading_path_level",
    "content",
    "source_url",
    "source_domain",
    "page_depth",
    "heading_level",
    "sequence_order",
    "matched_keyword",
    "is_exact_match",
    "scraped_at",
    "content_hash",
]


def audit_legacy_cancer_content(engine: Engine) -> Dict[str, Any]:
    """
    Captures an exact, deterministic structural and cryptographic audit
    of the legacy 'cancer_content' table.

    Returns:
        dict containing:
        - exists: bool
        - column_count: int (must be 22)
        - column_definitions: sorted list of column specs (name, type, nullable, default)
        - primary_key_columns: list of PK columns
        - indexes: sorted list of index definitions
        - row_count: total rows in table
        - null_hash_count: rows where content_hash IS NULL
        - primary_key_set: exact ordered list of primary key IDs
        - ordered_tuples: exact ordered tuples of (id, content_id, content_hash, scraped_at)
        - deterministic_digest: SHA-256 hex digest of serialized ordered tuples
    """
    inspector = inspect(engine)
    if "cancer_content" not in inspector.get_table_names():
        return {
            "exists": False,
            "column_count": 0,
            "column_definitions": [],
            "primary_key_columns": [],
            "indexes": [],
            "row_count": 0,
            "null_hash_count": 0,
            "primary_key_set": [],
            "ordered_tuples": [],
            "deterministic_digest": None,
        }

    # 1. 22 Column definitions
    columns_raw = inspector.get_columns("cancer_content")
    col_defs = [
        {
            "name": col["name"],
            "type": str(col["type"]).upper(),
            "nullable": col["nullable"],
            "default": str(col.get("default")),
        }
        for col in sorted(columns_raw, key=lambda c: c["name"])
    ]

    # 2. Primary key constraint
    pk_info = inspector.get_pk_constraint("cancer_content")
    pk_cols = pk_info.get("constrained_columns", [])

    # 3. Index definitions
    indexes_raw = inspector.get_indexes("cancer_content")
    idx_defs = [
        {
            "name": idx["name"],
            "column_names": idx.get("column_names", []),
            "unique": idx.get("unique", False),
        }
        for idx in sorted(indexes_raw, key=lambda i: i["name"] or "")
    ]

    # 4. Data inspection
    with engine.connect() as conn:
        row_count = conn.execute(text("SELECT COUNT(*) FROM cancer_content")).scalar() or 0
        null_hash_count = conn.execute(
            text("SELECT COUNT(*) FROM cancer_content WHERE content_hash IS NULL")
        ).scalar() or 0

        # Ordered primary key set
        pk_rows = conn.execute(text("SELECT id FROM cancer_content ORDER BY id")).fetchall()
        pk_set = [r[0] for r in pk_rows]

        # Exact ordered records across ALL 22 legacy columns
        cols_sql = ", ".join(EXPECTED_LEGACY_COLUMNS)
        tuple_rows = conn.execute(
            text(f"SELECT {cols_sql} FROM cancer_content ORDER BY id")
        ).fetchall()

        ordered_tuples: List[List[Any]] = []
        for r in tuple_rows:
            row_vals = []
            for val in r:
                if isinstance(val, (datetime, date)):
                    row_vals.append(val.isoformat())
                else:
                    row_vals.append(val)
            ordered_tuples.append(row_vals)

    # 5. Deterministic digest of all rows across all 22 columns
    serialized = json.dumps(ordered_tuples, sort_keys=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    return {
        "exists": True,
        "column_count": len(col_defs),
        "column_definitions": col_defs,
        "primary_key_columns": pk_cols,
        "indexes": idx_defs,
        "row_count": row_count,
        "null_hash_count": null_hash_count,
        "primary_key_set": pk_set,
        "ordered_tuples": ordered_tuples,
        "deterministic_digest": digest,
    }


def compare_legacy_audits(pre_audit: Dict[str, Any], post_audit: Dict[str, Any]) -> None:
    """
    Asserts that two legacy cancer_content audits are completely identical.
    Raises AssertionError with clear description on any discrepancy.
    """
    assert pre_audit["exists"] == post_audit["exists"], "Legacy table existence mismatch!"
    if not pre_audit["exists"]:
        return

    assert pre_audit["column_count"] == post_audit["column_count"] == 22, (
        f"Legacy column count mismatch! Pre: {pre_audit['column_count']}, Post: {post_audit['column_count']}"
    )
    assert pre_audit["column_definitions"] == post_audit["column_definitions"], (
        "Legacy column definitions were modified!"
    )
    assert pre_audit["primary_key_columns"] == post_audit["primary_key_columns"], (
        "Legacy primary key definition was modified!"
    )
    assert pre_audit["indexes"] == post_audit["indexes"], (
        f"Legacy index definitions were modified! Pre: {pre_audit['indexes']} vs Post: {post_audit['indexes']}"
    )
    assert pre_audit["row_count"] == post_audit["row_count"], (
        f"Legacy row count changed from {pre_audit['row_count']} to {post_audit['row_count']}!"
    )
    assert pre_audit["null_hash_count"] == post_audit["null_hash_count"], (
        f"Legacy null hash count changed from {pre_audit['null_hash_count']} to {post_audit['null_hash_count']}!"
    )
    assert pre_audit["primary_key_set"] == post_audit["primary_key_set"], (
        "Legacy primary key set was altered!"
    )
    assert pre_audit["deterministic_digest"] == post_audit["deterministic_digest"], (
        f"Legacy data digest mismatch! Pre: {pre_audit['deterministic_digest']} vs Post: {post_audit['deterministic_digest']}"
    )

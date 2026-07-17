"""One-shot migration: re-encrypt any legacy-format config rows to the
current Fernet ``{"__enc__": true, "__data__": ...}`` shape.

Background: ``utils.encryption.decrypt_config`` still accepts three legacy
formats (plain dict, base64-encoded JSON string, raw JSON string) alongside
the current encrypted-dict format, so that old rows written before Fernet
encryption was introduced keep working. That's a permanent soft spot: those
rows sit in the database with secrets in plaintext (or trivially-reversible
base64) rather than encrypted. This script finds and re-encrypts them.

Rows with no sensitive fields (no ``client_secret``/``key_file_base64``/
``key_file_content``) are left untouched even if stored in a legacy shape —
``encrypt_config`` has nothing to protect there, so there's no security gap
to close and no point rewriting the row.

Tables touched: ``cloud_config.config`` and ``auth_providers.config``.

Usage:
    # Report what would change, write nothing (default):
    uv run python -m scripts.migrate_config_encryption

    # Actually apply the re-encryption:
    uv run python -m scripts.migrate_config_encryption --commit

Safety:
    - Dry-run by default; --commit is required to write anything.
    - Take a database backup before running with --commit — this rewrites
      the config column for every non-canonical row in a single transaction
      (rolled back automatically if any row fails to decrypt or re-encrypt).
    - Requires ENCRYPTION_KEY to be set to the value already used for
      existing rows encrypt_config produced (i.e. the current running
      config), not a rotated key — this migrates *format*, not *key*.
    - Idempotent: rows already in canonical {"__enc__": true, ...} shape
      with no legacy fields left over are left untouched, so re-running is
      safe.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.encryption import decrypt_config, encrypt_config

logger = logging.getLogger("migrate_config_encryption")

TABLES = ("cloud_config", "auth_providers")


def _is_canonical(raw: object) -> bool:
    """True if *raw* is already in the current encrypted-dict shape."""
    return isinstance(raw, dict) and raw.get("__enc__") is True


def migrate_table(conn: psycopg.Connection, table: str, commit: bool) -> tuple[int, int]:
    """Re-encrypt legacy-format config rows in *table*. Returns (total, changed)."""
    with conn.cursor(row_factory=dict_row) as cur:  # type: ignore[arg-type]
        cur.execute(f"SELECT id, config FROM {table} WHERE config IS NOT NULL")  # noqa: S608 — table from fixed TABLES tuple
        rows = cur.fetchall()

    changed = 0
    for row in rows:
        raw = row["config"]
        if _is_canonical(raw):
            continue

        try:
            plain = decrypt_config(raw)
        except Exception:
            logger.exception("Failed to decrypt %s.config for id=%s; skipping", table, row["id"])
            continue

        if not plain:
            logger.warning(
                "%s.config for id=%s decrypted to empty dict; skipping to avoid data loss",
                table,
                row["id"],
            )
            continue

        re_encrypted = encrypt_config(plain)
        if not (isinstance(re_encrypted, dict) and re_encrypted.get("__enc__") is True):
            # No sensitive fields present — encrypt_config returned the dict
            # unchanged. Nothing to protect, so leave the row as a plain
            # dict rather than performing a no-op rewrite.
            logger.info(
                "%s row id=%s: legacy dict shape but no sensitive fields; leaving as plain dict",
                table,
                row["id"],
            )
            continue

        changed += 1
        logger.info(
            "%s row id=%s: legacy format -> re-encrypted (%d field(s))",
            table,
            row["id"],
            len(re_encrypted.get("__fields__", [])),
        )

        if commit:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {table} SET config = %s WHERE id = %s",  # noqa: S608 — table from fixed TABLES tuple
                    (Jsonb(re_encrypted), row["id"]),
                )

    return len(rows), changed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually write changes. Without this flag, only reports what would change.",
    )
    args = parser.parse_args()

    dsn = os.environ.get("PG_DSN")
    if not dsn:
        raise SystemExit("PG_DSN environment variable is required")
    if not os.environ.get("ENCRYPTION_KEY"):
        raise SystemExit("ENCRYPTION_KEY environment variable is required")

    if not args.commit:
        logger.info("DRY RUN — no changes will be written. Pass --commit to apply.")

    with psycopg.connect(dsn) as conn:
        total_rows = 0
        total_changed = 0
        try:
            for table in TABLES:
                rows, changed = migrate_table(conn, table, args.commit)
                total_rows += rows
                total_changed += changed
                logger.info("%s: %d row(s) scanned, %d need re-encryption", table, rows, changed)

            if args.commit:
                conn.commit()
                logger.info("Committed: %d/%d row(s) re-encrypted", total_changed, total_rows)
            else:
                conn.rollback()
                logger.info(
                    "Dry run complete: %d/%d row(s) would be re-encrypted. Re-run with --commit to apply.",
                    total_changed,
                    total_rows,
                )
        except Exception:
            conn.rollback()
            logger.exception("Migration failed; rolled back all changes")
            raise


if __name__ == "__main__":
    main()

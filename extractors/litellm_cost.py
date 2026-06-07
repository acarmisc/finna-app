"""LiteLLM cost extractor for FinOps multi-cloud monitoring.

Pulls per-request LLM spend from a LiteLLM proxy via `GET /spend/logs`,
normalizes each transaction into a NormalizedCostRecord, and batch-inserts
into PostgreSQL. One LiteLLM request -> one record.

Configuration via environment variables:
  LITELLM_BASE_URL       LiteLLM proxy base URL (e.g. http://litellm:4000)
  LITELLM_MASTER_KEY     Master key (or key with `get_spend_routes` perm)
  LITELLM_TIMEOUT        HTTP timeout in seconds (default 30)
  LITELLM_PAGE_SIZE      Max rows per /spend/logs page (default 1000)
  LITELLM_TASK_TAG_PREFIX  Optional prefix that marks a tag as the task name
                           (e.g. "task:"). First matching tag wins. Defaults
                           to using the first request_tag as project_id.
  PG_DSN                 PostgreSQL connection string
  DATE_FROM              Start date (YYYY-MM-DD), defaults to 30 days ago
  DATE_TO                End date (YYYY-MM-DD), defaults to today
  BATCH_SIZE             DB insert batch size (default 500)

Cost is always in USD (LiteLLM stores spend in USD only).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, cast

import httpx
import psycopg
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_chain,
    wait_fixed,
)

from models import NormalizedCostRecord, Provider, ServiceCategory

logger = logging.getLogger(__name__)

EXTRACTOR_NAME = "litellm_cost"
DEFAULT_TIMEOUT = 30
DEFAULT_PAGE_SIZE = 1000


# ---------------------------------------------------------------------------#
# LiteLLM HTTP client                                                        #
# ---------------------------------------------------------------------------#


@retry(
    stop=stop_after_attempt(3),
    wait=wait_chain(wait_fixed(1), wait_fixed(2), wait_fixed(4)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def _fetch_page(
    client: httpx.Client,
    base_url: str,
    start_date: str,
    end_date: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Fetch one page of /spend/logs."""
    url = f"{base_url.rstrip('/')}/spend/logs"
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "summarize": "false",
        "page": str(page),
        "page_size": str(page_size),
    }
    resp = client.get(url, params=params)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    if isinstance(data, list):
        return {"data": data, "total_pages": 1}
    return cast(dict[str, Any], data)


def fetch_spend_logs(
    base_url: str,
    master_key: str,
    start_date: str,
    end_date: str,
    page_size: int = DEFAULT_PAGE_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    """Pull all spend log rows in [start_date, end_date], paginated."""
    headers = {"Authorization": f"Bearer {master_key}"}
    rows: list[dict[str, Any]] = []

    with httpx.Client(timeout=timeout, headers=headers) as client:
        page = 1
        while True:
            payload = _fetch_page(client, base_url, start_date, end_date, page, page_size)
            page_rows = payload.get("data") or payload.get("logs") or []
            if not page_rows:
                break
            rows.extend(page_rows)
            total_pages = payload.get("total_pages") or payload.get("totalPages")
            if total_pages and page >= int(total_pages):
                break
            if len(page_rows) < page_size:
                break
            page += 1

    logger.info("Fetched %d spend log rows from LiteLLM", len(rows))
    return rows


# ---------------------------------------------------------------------------#
# Normalization                                                              #
# ---------------------------------------------------------------------------#


def _generate_record_id(request_id: str) -> str:
    raw = f"llm:{request_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _hash_api_key(api_key: str | None) -> str:
    if not api_key:
        return ""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        logger.warning("Unparseable timestamp %r", value)
        return None


def _parse_tags(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t) for t in raw if t]
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(t) for t in parsed if t]
        except json.JSONDecodeError:
            pass
        return [s]
    return []


def _pick_project_id(tags: list[str], prefix: str | None) -> str:
    if prefix:
        for t in tags:
            if t.startswith(prefix):
                return t[len(prefix):] or "default"
        return "default"
    return tags[0] if tags else "default"


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def normalize_litellm_records(
    rows: list[dict[str, Any]],
    task_tag_prefix: str | None = None,
) -> list[NormalizedCostRecord]:
    """Transform LiteLLM /spend/logs rows into NormalizedCostRecord instances."""
    records: list[NormalizedCostRecord] = []

    for row in rows:
        request_id = row.get("request_id") or row.get("id")
        if not request_id:
            logger.debug("Skipping row without request_id")
            continue

        spend = _to_decimal(row.get("spend"))
        if spend <= 0:
            continue

        usage_start = _parse_dt(row.get("startTime") or row.get("start_time"))
        usage_end = _parse_dt(row.get("endTime") or row.get("end_time")) or usage_start
        if not usage_start:
            continue
        if not usage_end:
            usage_end = usage_start

        model = row.get("model") or "unknown"
        model_group = row.get("model_group")
        provider_name = row.get("custom_llm_provider")
        user_id = row.get("user") or row.get("user_id") or "unknown"
        team_id = row.get("team_id")
        end_user = row.get("end_user")
        api_key = row.get("api_key")
        status = row.get("status")
        session_id = row.get("session_id")
        cache_hit = row.get("cache_hit")

        prompt_tokens = int(row.get("prompt_tokens") or 0)
        completion_tokens = int(row.get("completion_tokens") or 0)
        total_tokens = int(row.get("total_tokens") or (prompt_tokens + completion_tokens))

        tags_list = _parse_tags(row.get("request_tags"))
        project_id = _pick_project_id(tags_list, task_tag_prefix)

        tag_payload: dict[str, str] = {}
        if model_group:
            tag_payload["model_group"] = str(model_group)
        if provider_name:
            tag_payload["llm_provider"] = str(provider_name)
        if end_user:
            tag_payload["end_user"] = str(end_user)
        if api_key:
            tag_payload["api_key_hash"] = _hash_api_key(str(api_key))
        if status:
            tag_payload["status"] = str(status)
        if session_id:
            tag_payload["session_id"] = str(session_id)
        if cache_hit is not None:
            tag_payload["cache_hit"] = str(cache_hit)
        if tags_list:
            tag_payload["request_tags"] = ",".join(tags_list)
        tag_payload["prompt_tokens"] = str(prompt_tokens)
        tag_payload["completion_tokens"] = str(completion_tokens)

        record = NormalizedCostRecord(
            record_id=_generate_record_id(str(request_id)),
            provider=Provider.LLM,
            usage_start=usage_start,
            usage_end=usage_end,
            account_id=str(user_id),
            project_id=project_id,
            team=str(team_id) if team_id else None,
            service_category=ServiceCategory.LLM,
            service_name=str(model),
            resource_id=str(session_id) if session_id else None,
            cost_usd=spend,
            currency_original="USD",
            cost_original=spend,
            discount_usd=Decimal("0"),
            net_cost_usd=spend,
            usage_quantity=Decimal(total_tokens),
            usage_unit="tokens",
            model_name=str(model),
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=total_tokens,
            trace_id=str(request_id),
            tags=tag_payload,
        )
        records.append(record)

    return records


# ---------------------------------------------------------------------------#
# PostgreSQL helpers                                                         #
# ---------------------------------------------------------------------------#

_INSERT_SQL = """
INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, ingestion_ts,
    account_id, project_id, team, service_category, service_name,
    resource_id, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit,
    model_name, input_tokens, output_tokens, total_tokens, trace_id,
    tags
) VALUES (
    %(record_id)s, %(provider)s, %(usage_start)s, %(usage_end)s, %(ingestion_ts)s,
    %(account_id)s, %(project_id)s, %(team)s, %(service_category)s, %(service_name)s,
    %(resource_id)s, %(region)s, %(charge_type)s,
    %(cost_usd)s, %(currency_original)s, %(cost_original)s, %(discount_usd)s, %(net_cost_usd)s,
    %(usage_quantity)s, %(usage_unit)s,
    %(model_name)s, %(input_tokens)s, %(output_tokens)s, %(total_tokens)s, %(trace_id)s,
    %(tags)s
) ON CONFLICT (record_id) DO NOTHING
"""


def _insert_batch(conn: psycopg.Connection, records: list[NormalizedCostRecord]) -> int:
    if not records:
        return 0
    total = 0
    for rec in records:
        row = rec.model_dump()
        row["provider"] = rec.provider.value
        row["service_category"] = rec.service_category.value
        row["tags"] = json.dumps(row.get("tags", {}))
        with conn.cursor() as cur:
            cur.execute(_INSERT_SQL, row)
        total += 1
    conn.commit()
    return total


def insert_records(
    conn: psycopg.Connection,
    records: list[NormalizedCostRecord],
    batch_size: int = 500,
) -> int:
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        inserted = _insert_batch(conn, batch)
        total += inserted
        logger.info("Inserted batch %d-%d (%d records)", i, i + len(batch), inserted)
    return total


# ---------------------------------------------------------------------------#
# Health tracking                                                            #
# ---------------------------------------------------------------------------#


# Allowlist of timestamp column names that may be substituted into the
# extractor_health DML below. The values come from schema introspection, not
# user input, but we keep an explicit set so the SQL builder is statically
# auditable (see SECURITY_AUDIT.md §2.5).
_ALLOWED_HEALTH_TS_COLS = {"last_run_start", "last_run_end", "last_run_ts"}


def _safe_ts_col(name: str) -> str:
    if name not in _ALLOWED_HEALTH_TS_COLS:
        raise ValueError(f"Refusing to use unvetted ts column: {name!r}")
    return name


def _health_columns(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'extractor_health'
            """
        )
        return {row[0] for row in cur.fetchall()}


def _mark_health_start(conn: psycopg.Connection) -> None:
    try:
        cols = _health_columns(conn)
        if not cols:
            return
        ts_col = _safe_ts_col("last_run_start" if "last_run_start" in cols else "last_run_ts")
        sql = f"""
            INSERT INTO extractor_health
                (extractor_name, {ts_col}, status, records_extracted, updated_at)
            VALUES (%s, now(), 'running', 0, now())
            ON CONFLICT (extractor_name) DO UPDATE
                SET {ts_col} = now(),
                    status = 'running',
                    records_extracted = 0,
                    error_message = NULL,
                    updated_at = now()
        """
        with conn.cursor() as cur:
            cur.execute(sql, (EXTRACTOR_NAME,))
        conn.commit()
    except Exception:
        logger.warning("extractor_health start update skipped", exc_info=True)
        conn.rollback()


def _mark_health_success(conn: psycopg.Connection, record_count: int) -> None:
    try:
        cols = _health_columns(conn)
        if not cols:
            return
        ts_col = _safe_ts_col("last_run_end" if "last_run_end" in cols else "last_run_ts")
        sql = f"""
            UPDATE extractor_health
            SET {ts_col} = now(),
                status = 'success',
                records_extracted = %s,
                updated_at = now()
            WHERE extractor_name = %s
        """
        with conn.cursor() as cur:
            cur.execute(sql, (record_count, EXTRACTOR_NAME))
        conn.commit()
    except Exception:
        logger.warning("extractor_health success update skipped", exc_info=True)
        conn.rollback()


def _mark_health_failure(conn: psycopg.Connection, error_message: str) -> None:
    try:
        conn.rollback()
        cols = _health_columns(conn)
        if not cols:
            return
        ts_col = _safe_ts_col("last_run_end" if "last_run_end" in cols else "last_run_ts")
        sql = f"""
            UPDATE extractor_health
            SET {ts_col} = now(),
                status = 'failed',
                error_message = %s,
                updated_at = now()
            WHERE extractor_name = %s
        """
        with conn.cursor() as cur:
            cur.execute(sql, (error_message[:2000], EXTRACTOR_NAME))
        conn.commit()
    except Exception:
        logger.exception("Failed to mark extractor health as failed")


# ---------------------------------------------------------------------------#
# Main flow                                                                  #
# ---------------------------------------------------------------------------#


def extract_costs(
    date_from: datetime,
    date_to: datetime,
    batch_size: int = 500,
) -> int:
    base_url = os.getenv("LITELLM_BASE_URL")
    master_key = os.getenv("LITELLM_MASTER_KEY")
    pg_dsn = os.getenv("PG_DSN")
    page_size = int(os.getenv("LITELLM_PAGE_SIZE", str(DEFAULT_PAGE_SIZE)))
    timeout = float(os.getenv("LITELLM_TIMEOUT", str(DEFAULT_TIMEOUT)))
    task_tag_prefix = os.getenv("LITELLM_TASK_TAG_PREFIX") or None

    if not base_url or not master_key:
        logger.error("LITELLM_BASE_URL and LITELLM_MASTER_KEY are required")
        return 0
    if not pg_dsn:
        raise ValueError("PG_DSN is not configured")

    start_str = date_from.strftime("%Y-%m-%d")
    end_str = date_to.strftime("%Y-%m-%d")

    rows = fetch_spend_logs(
        base_url=base_url,
        master_key=master_key,
        start_date=start_str,
        end_date=end_str,
        page_size=page_size,
        timeout=timeout,
    )
    records = normalize_litellm_records(rows, task_tag_prefix=task_tag_prefix)

    if not records:
        logger.info("No LLM cost records for %s – %s", start_str, end_str)
        return 0

    pg_conn = psycopg.connect(pg_dsn)
    _mark_health_start(pg_conn)
    try:
        total = insert_records(pg_conn, records, batch_size)
        logger.info("LiteLLM extraction complete: %d records inserted", total)
        _mark_health_success(pg_conn, total)
        return total
    except Exception as exc:
        logger.exception("LiteLLM extraction failed: %s", exc)
        _mark_health_failure(pg_conn, str(exc))
        raise
    finally:
        pg_conn.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        stream=sys.stdout,
    )
    logger.info("Starting LiteLLM cost extractor")

    date_from_raw = os.getenv("DATE_FROM")
    date_to_raw = os.getenv("DATE_TO")

    if date_from_raw and date_to_raw:
        date_from = datetime.strptime(date_from_raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        date_to = datetime.strptime(date_to_raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        to_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        from_dt = to_dt - timedelta(days=30)
        date_to = to_dt
        date_from = from_dt

    batch_size = int(os.getenv("BATCH_SIZE", "500"))

    try:
        total = extract_costs(date_from=date_from, date_to=date_to, batch_size=batch_size)
        logger.info("LiteLLM cost extractor finished: %d records", total)
    except Exception:
        logger.exception("LiteLLM cost extractor failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

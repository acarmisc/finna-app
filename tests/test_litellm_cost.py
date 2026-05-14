"""Unit tests for extractors.litellm_cost."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx
import pytest

from extractors.litellm_cost import (
    _generate_record_id,
    _hash_api_key,
    _insert_batch,
    _parse_dt,
    _parse_tags,
    _pick_project_id,
    _to_decimal,
    extract_costs,
    fetch_spend_logs,
    normalize_litellm_records,
)
from models import Provider, ServiceCategory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _row(**overrides):
    base = {
        "request_id": "req-1",
        "api_key": "sk-abc",
        "spend": "0.0123",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
        "startTime": "2026-05-01T12:00:00Z",
        "endTime": "2026-05-01T12:00:02Z",
        "model": "gpt-4o-mini",
        "model_group": "openai-mini",
        "custom_llm_provider": "openai",
        "user": "alice",
        "team_id": "team-eng",
        "end_user": "customer-7",
        "request_tags": ["task:summarize", "env:prod"],
        "status": "success",
        "session_id": "sess-9",
        "cache_hit": "false",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_generate_record_id_deterministic():
    assert _generate_record_id("req-1") == _generate_record_id("req-1")
    assert _generate_record_id("req-1") != _generate_record_id("req-2")


def test_hash_api_key_empty():
    assert _hash_api_key(None) == ""
    assert _hash_api_key("") == ""
    assert len(_hash_api_key("sk-abc")) == 16


def test_parse_dt_iso_z():
    dt = _parse_dt("2026-05-01T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo is timezone.utc


def test_parse_dt_garbage():
    assert _parse_dt("not-a-date") is None
    assert _parse_dt(None) is None


def test_parse_tags_list_and_json_and_str():
    assert _parse_tags(["a", "b"]) == ["a", "b"]
    assert _parse_tags('["x","y"]') == ["x", "y"]
    assert _parse_tags("plain") == ["plain"]
    assert _parse_tags(None) == []
    assert _parse_tags("") == []


def test_pick_project_id_prefix_match():
    tags = ["env:prod", "task:summarize"]
    assert _pick_project_id(tags, "task:") == "summarize"


def test_pick_project_id_prefix_set_no_match_returns_default():
    tags = ["User-Agent: claude-cli", "env:prod"]
    assert _pick_project_id(tags, "task:") == "default"


def test_pick_project_id_no_prefix_uses_first():
    tags = ["alpha", "beta"]
    assert _pick_project_id(tags, None) == "alpha"
    assert _pick_project_id([], None) == "default"


def test_to_decimal_handles_garbage():
    assert _to_decimal("1.23") == Decimal("1.23")
    assert _to_decimal(None) == Decimal("0")
    assert _to_decimal("nope") == Decimal("0")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_normalize_full_row():
    records = normalize_litellm_records([_row()], task_tag_prefix="task:")
    assert len(records) == 1
    r = records[0]
    assert r.provider == Provider.LLM
    assert r.service_category == ServiceCategory.LLM
    assert r.service_name == "gpt-4o-mini"
    assert r.model_name == "gpt-4o-mini"
    assert r.account_id == "alice"
    assert r.project_id == "summarize"
    assert r.team == "team-eng"
    assert r.input_tokens == 100
    assert r.output_tokens == 50
    assert r.total_tokens == 150
    assert r.usage_quantity == Decimal(150)
    assert r.usage_unit == "tokens"
    assert r.cost_usd == Decimal("0.0123")
    assert r.currency_original == "USD"
    assert r.cost_original == r.cost_usd
    assert r.trace_id == "req-1"
    assert r.tags["end_user"] == "customer-7"
    assert r.tags["llm_provider"] == "openai"
    assert r.tags["model_group"] == "openai-mini"
    assert r.tags["request_tags"] == "task:summarize,env:prod"
    assert "api_key_hash" in r.tags


def test_normalize_skips_zero_spend():
    records = normalize_litellm_records([_row(spend="0")])
    assert records == []


def test_normalize_skips_missing_request_id():
    records = normalize_litellm_records([_row(request_id=None)])
    assert records == []


def test_normalize_defaults_missing_user_and_tags():
    rows = [_row(user=None, team_id=None, request_tags=[])]
    records = normalize_litellm_records(rows)
    r = records[0]
    assert r.account_id == "unknown"
    assert r.team is None
    assert r.project_id == "default"


def test_normalize_total_tokens_falls_back_to_sum():
    rows = [_row(total_tokens=None, prompt_tokens=10, completion_tokens=20)]
    r = normalize_litellm_records(rows)[0]
    assert r.total_tokens == 30
    assert r.usage_quantity == Decimal(30)


# ---------------------------------------------------------------------------
# HTTP fetch (httpx MockTransport)
# ---------------------------------------------------------------------------


def test_fetch_spend_logs_paginates(monkeypatch):
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        calls.append(params)
        page = int(params["page"])
        if page == 1:
            return httpx.Response(200, json={"data": [_row(request_id=f"r{page}")], "total_pages": 2})
        if page == 2:
            return httpx.Response(200, json={"data": [_row(request_id=f"r{page}")], "total_pages": 2})
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        return real_client(transport=transport, headers=kwargs.get("headers"))

    monkeypatch.setattr("extractors.litellm_cost.httpx.Client", fake_client)

    rows = fetch_spend_logs(
        base_url="http://litellm",
        master_key="sk-master",
        start_date="2026-05-01",
        end_date="2026-05-02",
        page_size=1,
    )
    assert len(rows) == 2
    assert calls[0]["page"] == "1"
    assert calls[1]["page"] == "2"
    assert calls[0]["start_date"] == "2026-05-01"
    assert calls[0]["summarize"] == "false"


def test_fetch_spend_logs_stops_on_empty(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        "extractors.litellm_cost.httpx.Client",
        lambda *a, **kw: real_client(transport=transport, headers=kw.get("headers")),
    )

    rows = fetch_spend_logs(
        base_url="http://litellm",
        master_key="sk",
        start_date="2026-05-01",
        end_date="2026-05-02",
    )
    assert rows == []


# ---------------------------------------------------------------------------
# Insert path
# ---------------------------------------------------------------------------


def test_insert_batch_invokes_cursor():
    records = normalize_litellm_records([_row()])
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor

    inserted = _insert_batch(conn, records)
    assert inserted == 1
    assert cursor.execute.called
    conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def test_extract_costs_missing_env(monkeypatch):
    monkeypatch.delenv("LITELLM_BASE_URL", raising=False)
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)
    monkeypatch.setenv("PG_DSN", "postgres://x")
    out = extract_costs(
        date_from=datetime(2026, 5, 1, tzinfo=timezone.utc),
        date_to=datetime(2026, 5, 2, tzinfo=timezone.utc),
    )
    assert out == 0


def test_extract_costs_missing_pg_dsn(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://x")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk")
    monkeypatch.delenv("PG_DSN", raising=False)
    with pytest.raises(ValueError):
        extract_costs(
            date_from=datetime(2026, 5, 1, tzinfo=timezone.utc),
            date_to=datetime(2026, 5, 2, tzinfo=timezone.utc),
        )


@patch("extractors.litellm_cost.psycopg.connect")
@patch("extractors.litellm_cost.fetch_spend_logs")
def test_extract_costs_happy_path(mock_fetch, mock_connect, monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk")
    monkeypatch.setenv("PG_DSN", "postgres://x")

    mock_fetch.return_value = [_row(), _row(request_id="req-2")]

    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value = conn

    total = extract_costs(
        date_from=datetime(2026, 5, 1, tzinfo=timezone.utc),
        date_to=datetime(2026, 5, 2, tzinfo=timezone.utc),
    )
    assert total == 2
    mock_fetch.assert_called_once()

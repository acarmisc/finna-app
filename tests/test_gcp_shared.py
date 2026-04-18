"""Unit tests for extractors.gcp_shared — shared normalization logic."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from extractors.gcp_shared import (
    extract_project_label,
    generate_record_id,
    labels_to_tags,
    normalize_csv_row,
    parse_datetime,
    resolve_service_category,
)
from models import Provider, ServiceCategory

# ---------------------------------------------------------------------------
# resolve_service_category
# ---------------------------------------------------------------------------

class TestResolveServiceCategory:
    def test_exact_match(self):
        assert resolve_service_category("Compute Engine") == ServiceCategory.COMPUTE

    def test_exact_match_storage(self):
        assert resolve_service_category("Cloud Storage") == ServiceCategory.STORAGE

    def test_substring_match(self):
        assert resolve_service_category("Compute Engine API") == ServiceCategory.COMPUTE

    def test_substring_match_case_insensitive(self):
        assert resolve_service_category("compute engine api") == ServiceCategory.COMPUTE

    def test_unknown_service_returns_other(self):
        assert resolve_service_category("Unknown Service XYZ") == ServiceCategory.OTHER

    def test_custom_mapping(self):
        custom = {"MyService": ServiceCategory.DATABASE}
        assert resolve_service_category("MyService", custom) == ServiceCategory.DATABASE

    def test_empty_string_returns_other(self):
        assert resolve_service_category("") == ServiceCategory.OTHER


# ---------------------------------------------------------------------------
# generate_record_id
# ---------------------------------------------------------------------------

class TestGenerateRecordId:
    def test_deterministic(self):
        id1 = generate_record_id("gcp", "proj1", "2025-01-01T00:00:00Z", "sku1")
        id2 = generate_record_id("gcp", "proj1", "2025-01-01T00:00:00Z", "sku1")
        assert id1 == id2

    def test_different_inputs_different_ids(self):
        id1 = generate_record_id("gcp", "proj1", "2025-01-01T00:00:00Z", "sku1")
        id2 = generate_record_id("gcp", "proj1", "2025-01-01T00:00:00Z", "sku2")
        assert id1 != id2

    def test_is_sha256_hex(self):
        rid = generate_record_id("gcp", "proj1", "2025-01-01T00:00:00Z", "sku1")
        assert len(rid) == 64
        assert all(c in "0123456789abcdef" for c in rid)


# ---------------------------------------------------------------------------
# parse_datetime
# ---------------------------------------------------------------------------

class TestParseDatetime:
    def test_iso_string(self):
        result = parse_datetime("2025-03-01T00:00:00Z")
        assert result.year == 2025
        assert result.month == 3

    def test_iso_string_no_tz(self):
        result = parse_datetime("2025-03-01T00:00:00")
        assert result.tzinfo is not None  # should get UTC attached

    def test_datetime_object_naive(self):
        dt = datetime(2025, 3, 1, 0, 0, 0)
        result = parse_datetime(dt)
        assert result.tzinfo is not None

    def test_datetime_object_aware(self):
        dt = datetime(2025, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = parse_datetime(dt)
        assert result == dt

    def test_none_returns_now(self):
        result = parse_datetime(None)
        assert result.tzinfo is not None


# ---------------------------------------------------------------------------
# extract_project_label
# ---------------------------------------------------------------------------

class TestExtractProjectLabel:
    def test_list_of_dicts(self):
        row = {"labels": [{"key": "project", "value": "my-project"}, {"key": "env", "value": "prod"}]}
        assert extract_project_label(row) == "my-project"

    def test_csv_string_format(self):
        row = {"labels": "project:my-project;env:prod"}
        assert extract_project_label(row) == "my-project"

    def test_no_project_label(self):
        row = {"labels": [{"key": "env", "value": "prod"}]}
        assert extract_project_label(row) == ""

    def test_empty_labels(self):
        row = {"labels": []}
        assert extract_project_label(row) == ""

    def test_no_labels_key(self):
        row = {}
        assert extract_project_label(row) == ""


# ---------------------------------------------------------------------------
# labels_to_tags
# ---------------------------------------------------------------------------

class TestLabelsToTags:
    def test_list_of_dicts(self):
        row = {"labels": [{"key": "env", "value": "prod"}, {"key": "team", "value": "backend"}]}
        result = labels_to_tags(row)
        assert result == {"env": "prod", "team": "backend"}

    def test_csv_string_format(self):
        row = {"labels": "env:prod;team:backend"}
        result = labels_to_tags(row)
        assert result == {"env": "prod", "team": "backend"}

    def test_dict_format(self):
        row = {"labels": {"env": "prod", "team": "backend"}}
        result = labels_to_tags(row)
        assert result == {"env": "prod", "team": "backend"}

    def test_empty_labels(self):
        row = {"labels": []}
        assert labels_to_tags(row) == {}

    def test_none_labels(self):
        row = {"labels": None}
        assert labels_to_tags(row) == {}

    def test_missing_labels_key(self):
        row = {}
        assert labels_to_tags(row) == {}


# ---------------------------------------------------------------------------
# normalize_csv_row
# ---------------------------------------------------------------------------

def _make_csv_row(**overrides) -> dict[str, str]:
    """Build a realistic GCP CSV billing row dict."""
    row = {
        "billing_account_id": "01D4EE-079462-DFD6EC",
        "project.id": "my-gcp-project",
        "project.name": "My GCP Project",
        "service.description": "Compute Engine",
        "sku.description": "N1 Predefined Instance Core",
        "usage_start_time": "2025-03-01T00:00:00Z",
        "usage_end_time": "2025-03-01T01:00:00Z",
        "cost": "12.50",
        "currency": "USD",
        "usage.amount": "7.0",
        "usage.unit": "hours",
        "labels": "project:my-label-project;environment:prod",
    }
    row.update(overrides)
    return row


class TestNormalizeCsvRow:
    def test_basic_row(self):
        row = _make_csv_row()
        record = normalize_csv_row(row)
        assert record.provider == Provider.GCP
        assert record.account_id == "01D4EE-079462-DFD6EC"
        assert record.project_id == "my-label-project"
        assert record.service_category == ServiceCategory.COMPUTE
        assert record.service_name == "N1 Predefined Instance Core"
        assert record.cost_usd == Decimal("12.50")
        assert record.currency_original == "USD"
        assert record.usage_quantity == Decimal("7.0")
        assert record.usage_unit == "hours"
        assert record.tags == {"project": "my-label-project", "environment": "prod"}

    def test_underscore_column_names(self):
        """CSV headers may use underscores instead of dots."""
        row = _make_csv_row(labels="environment:prod")
        del row["project.id"]
        del row["project.name"]
        del row["service.description"]
        del row["sku.description"]
        row["project_id"] = "my-gcp-project"
        row["project_name"] = "My GCP Project"
        row["service_description"] = "Compute Engine"
        row["sku_description"] = "N1 Predefined Instance Core"

        record = normalize_csv_row(row)
        assert record.project_id == "my-gcp-project"
        assert record.service_category == ServiceCategory.COMPUTE

    def test_missing_optional_fields(self):
        row = _make_csv_row(cost="", usage_amount="")
        record = normalize_csv_row(row)
        assert record.cost_usd == Decimal("0")

    def test_unknown_service(self):
        row = _make_csv_row(**{"service.description": "Future Service XYZ"})
        record = normalize_csv_row(row)
        assert record.service_category == ServiceCategory.OTHER

    def test_deterministic_record_id(self):
        row = _make_csv_row()
        id1 = normalize_csv_row(row).record_id
        id2 = normalize_csv_row(row).record_id
        assert id1 == id2

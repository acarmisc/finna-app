"""Unit tests for the Azure Cost Management extractor."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from models import NormalizedCostRecord, Provider, ServiceCategory

# Import the module under test
from extractors.azure_cost import (
    DEFAULT_METER_CATEGORY_MAP,
    AZURE_QUERY_COLUMNS,
    convert_to_usd,
    fetch_cost_rows,
    generate_record_id,
    map_service_category,
    mark_extractor_healthy,
    transform_row,
    _parse_tags,
    _azure_date_to_datetime,
)


# ---------------------------------------------------------------------------
# Fixtures — realistic Azure cost rows
# ---------------------------------------------------------------------------

def _make_azure_row(
    usage_date: int = 20240315,
    subscription_id: str = "sub-001",
    resource_group: str = "rg-prod-app",
    meter_category: str = "Virtual Machines",
    meter_sub_category: str = "D2s v3",
    product: str = "D2s v3/Windows",
    cost: float = 42.50,
    currency: str = "USD",
    tags: dict | None = None,
) -> dict:
    """Build a realistic Azure cost row dict."""
    return {
        "UsageDate": usage_date,
        "SubscriptionId": subscription_id,
        "ResourceGroup": resource_group,
        "MeterCategory": meter_category,
        "MeterSubCategory": meter_sub_category,
        "Product": product,
        "CostInBillingCurrency": cost,
        "Currency": currency,
        "Tags": tags or {"project": "finops-monitor", "environment": "prod"},
    }


# ---------------------------------------------------------------------------
# Test: generate_record_id
# ---------------------------------------------------------------------------

class TestGenerateRecordId:
    def test_deterministic(self):
        """Same inputs always produce the same record_id."""
        id1 = generate_record_id("sub-001", "20240315", "Virtual Machines", "D2s v3", "D2s v3/Windows")
        id2 = generate_record_id("sub-001", "20240315", "Virtual Machines", "D2s v3", "D2s v3/Windows")
        assert id1 == id2

    def test_different_inputs_produce_different_ids(self):
        id1 = generate_record_id("sub-001", "20240315", "Virtual Machines", "D2s v3", "D2s v3/Windows")
        id2 = generate_record_id("sub-002", "20240315", "Virtual Machines", "D2s v3", "D2s v3/Windows")
        assert id1 != id2

    def test_length(self):
        rid = generate_record_id("sub-001", "20240315", "VM", "D2s", "Prod")
        assert len(rid) == 32


# ---------------------------------------------------------------------------
# Test: map_service_category
# ---------------------------------------------------------------------------

class TestMapServiceCategory:
    def test_known_compute(self):
        assert map_service_category("Virtual Machines") == ServiceCategory.COMPUTE

    def test_known_storage(self):
        assert map_service_category("Storage") == ServiceCategory.STORAGE

    def test_known_network(self):
        assert map_service_category("Virtual Network") == ServiceCategory.NETWORK

    def test_known_database(self):
        assert map_service_category("SQL Database") == ServiceCategory.DATABASE

    def test_known_ml(self):
        assert map_service_category("Machine Learning") == ServiceCategory.ML

    def test_known_llm(self):
        assert map_service_category("Azure OpenAI") == ServiceCategory.LLM

    def test_unknown_falls_back_to_other(self):
        assert map_service_category("SomeNewService") == ServiceCategory.OTHER

    def test_custom_mapping_overrides_default(self):
        custom = {"CustomThing": ServiceCategory.COMPUTE}
        assert map_service_category("CustomThing", custom) == ServiceCategory.COMPUTE

    def test_custom_mapping_does_not_use_default(self):
        """When a custom map is provided, the default map is NOT consulted."""
        custom = {"CustomThing": ServiceCategory.COMPUTE}
        # Virtual Machines is in the default map but NOT in custom map
        assert map_service_category("Virtual Machines", custom) == ServiceCategory.OTHER

    def test_default_map_has_expected_entries(self):
        assert "Virtual Machines" in DEFAULT_METER_CATEGORY_MAP
        assert "Storage" in DEFAULT_METER_CATEGORY_MAP
        assert "SQL Database" in DEFAULT_METER_CATEGORY_MAP
        assert "Azure OpenAI" in DEFAULT_METER_CATEGORY_MAP


# ---------------------------------------------------------------------------
# Test: currency conversion
# ---------------------------------------------------------------------------

class TestConvertToUsd:
    def test_usd_passthrough(self):
        assert convert_to_usd(Decimal("100.00"), "USD", {"USD": Decimal("1")}) == Decimal("100.00")

    def test_eur_conversion(self):
        rates = {"USD": Decimal("1"), "EUR": Decimal("1.08")}
        result = convert_to_usd(Decimal("100.00"), "EUR", rates)
        assert result == Decimal("108.000000")

    def test_gbp_conversion(self):
        rates = {"USD": Decimal("1"), "GBP": Decimal("1.27")}
        result = convert_to_usd(Decimal("50.00"), "GBP", rates)
        assert result == Decimal("63.500000")

    def test_missing_currency_treats_as_usd(self):
        """If no rate found, treat as USD=1 and log a warning."""
        rates = {"USD": Decimal("1")}
        result = convert_to_usd(Decimal("100.00"), "JPY", rates)
        assert result == Decimal("100.00")

    def test_zero_cost(self):
        rates = {"USD": Decimal("1"), "EUR": Decimal("1.08")}
        assert convert_to_usd(Decimal("0"), "EUR", rates) == Decimal("0.000000")


# ---------------------------------------------------------------------------
# Test: _azure_date_to_datetime
# ---------------------------------------------------------------------------

class TestAzureDateToDatetime:
    def test_integer_format(self):
        dt = _azure_date_to_datetime(20240315)
        assert dt == datetime(2024, 3, 15, tzinfo=timezone.utc)

    def test_iso_string(self):
        dt = _azure_date_to_datetime("2024-03-15T00:00:00")
        assert dt == datetime(2024, 3, 15, tzinfo=timezone.utc)

    def test_date_string(self):
        dt = _azure_date_to_datetime("2024-03-15")
        assert dt == datetime(2024, 3, 15, tzinfo=timezone.utc)

    def test_compact_string(self):
        dt = _azure_date_to_datetime("20240315")
        assert dt == datetime(2024, 3, 15, tzinfo=timezone.utc)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _azure_date_to_datetime("not-a-date")

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            _azure_date_to_datetime(3.14)


# ---------------------------------------------------------------------------
# Test: _parse_tags
# ---------------------------------------------------------------------------

class TestParseTags:
    def test_dict_input(self):
        result = _parse_tags({"project": "finops", "env": "prod"})
        assert result == {"project": "finops", "env": "prod"}

    def test_json_string(self):
        result = _parse_tags('{"project": "finops", "env": "prod"}')
        assert result == {"project": "finops", "env": "prod"}

    def test_none_returns_empty(self):
        assert _parse_tags(None) == {}

    def test_invalid_json_string_returns_empty(self):
        assert _parse_tags("not-json") == {}

    def test_non_dict_json_returns_empty(self):
        assert _parse_tags('"just a string"') == {}

    def test_numeric_values_cast_to_str(self):
        result = _parse_tags({"count": 42})
        assert result == {"count": "42"}


# ---------------------------------------------------------------------------
# Test: transform_row (field mapping)
# ---------------------------------------------------------------------------

class TestTransformRow:
    def setup_method(self):
        self.rates = {"USD": Decimal("1"), "EUR": Decimal("1.08"), "GBP": Decimal("1.27")}

    def test_basic_field_mapping(self):
        row = _make_azure_row()
        rec = transform_row(row, self.rates)
        assert isinstance(rec, NormalizedCostRecord)
        assert rec.provider == Provider.AZURE
        assert rec.account_id == "sub-001"
        assert rec.service_category == ServiceCategory.COMPUTE
        assert rec.cost_usd == Decimal("42.50")
        assert rec.currency_original == "USD"
        assert rec.cost_original == Decimal("42.50")
        assert rec.project_id == "finops-monitor"
        assert rec.service_name == "D2s v3"
        assert rec.resource_id == "rg-prod-app"
        assert rec.tags == {"project": "finops-monitor", "environment": "prod"}

    def test_subscription_id_mapping(self):
        row = _make_azure_row(subscription_id="sub-abc-999")
        rec = transform_row(row, self.rates)
        assert rec.account_id == "sub-abc-999"

    def test_meter_category_to_service_category(self):
        row = _make_azure_row(meter_category="Storage")
        rec = transform_row(row, self.rates)
        assert rec.service_category == ServiceCategory.STORAGE

    def test_meter_category_unknown_to_other(self):
        row = _make_azure_row(meter_category="UnknownService")
        rec = transform_row(row, self.rates)
        assert rec.service_category == ServiceCategory.OTHER

    def test_tag_project_to_project_id(self):
        row = _make_azure_row(tags={"project": "my-proj"})
        rec = transform_row(row, self.rates)
        assert rec.project_id == "my-proj"

    def test_tag_Project_capitalized(self):
        """Azure tags may use 'Project' (capitalized)."""
        row = _make_azure_row(tags={"Project": "capital-proj"})
        rec = transform_row(row, self.rates)
        assert rec.project_id == "capital-proj"

    def test_no_project_tag_falls_back_to_resource_group(self):
        row = _make_azure_row(tags={"env": "prod"})
        rec = transform_row(row, self.rates)
        assert rec.project_id == "rg-prod-app"

    def test_no_project_tag_no_resource_group_falls_back_to_sub(self):
        row = _make_azure_row(tags={"env": "prod"}, resource_group="")
        rec = transform_row(row, self.rates)
        assert rec.project_id == "sub-001"

    def test_meter_sub_category_maps_to_service_name(self):
        row = _make_azure_row(meter_sub_category="DS2 v2")
        rec = transform_row(row, self.rates)
        assert rec.service_name == "DS2 v2"

    def test_resource_group_maps_to_resource_id(self):
        row = _make_azure_row(resource_group="rg-data-pipeline")
        rec = transform_row(row, self.rates)
        assert rec.resource_id == "rg-data-pipeline"

    def test_empty_resource_group_gives_none(self):
        row = _make_azure_row(resource_group="")
        rec = transform_row(row, self.rates)
        assert rec.resource_id is None

    def test_product_stored_in_service_name_when_subcat_empty(self):
        """When MeterSubCategory is empty, service_name falls back to MeterCategory."""
        row = _make_azure_row(meter_sub_category="", meter_category="Storage")
        rec = transform_row(row, self.rates)
        assert rec.service_name == "Storage"

    def test_usage_date_to_usage_start_end(self):
        row = _make_azure_row(usage_date=20240315)
        rec = transform_row(row, self.rates)
        assert rec.usage_start == datetime(2024, 3, 15, tzinfo=timezone.utc)
        assert rec.usage_end == datetime(2024, 3, 16, tzinfo=timezone.utc)

    def test_deterministic_record_id(self):
        row = _make_azure_row()
        rec1 = transform_row(row, self.rates)
        rec2 = transform_row(row, self.rates)
        assert rec1.record_id == rec2.record_id

    def test_different_rows_produce_different_record_ids(self):
        row1 = _make_azure_row(subscription_id="sub-A")
        row2 = _make_azure_row(subscription_id="sub-B")
        rec1 = transform_row(row1, self.rates)
        rec2 = transform_row(row2, self.rates)
        assert rec1.record_id != rec2.record_id

    def test_currency_conversion_eur(self):
        row = _make_azure_row(cost=100.00, currency="EUR")
        rec = transform_row(row, self.rates)
        assert rec.cost_original == Decimal("100")
        assert rec.cost_usd == Decimal("108.000000")
        assert rec.currency_original == "EUR"

    def test_currency_conversion_gbp(self):
        row = _make_azure_row(cost=50.00, currency="GBP")
        rec = transform_row(row, self.rates)
        assert rec.cost_usd == Decimal("63.500000")

    def test_missing_rate_treats_as_usd(self):
        row = _make_azure_row(cost=100.00, currency="CAD")
        rec = transform_row(row, self.rates)
        assert rec.cost_usd == Decimal("100")

    def test_custom_meter_category_map(self):
        custom_map = {"SuperCompute": ServiceCategory.COMPUTE}
        row = _make_azure_row(meter_category="SuperCompute")
        rec = transform_row(row, self.rates, meter_category_map=custom_map)
        assert rec.service_category == ServiceCategory.COMPUTE

    def test_empty_tags(self):
        row = _make_azure_row(tags=None)
        # _make_azure_row defaults tags=None to a dict, let's override
        row["Tags"] = None
        rec = transform_row(row, self.rates)
        assert rec.tags == {}

    def test_json_string_tags(self):
        row = _make_azure_row()
        row["Tags"] = json.dumps({"project": "json-proj", "team": "platform"})
        rec = transform_row(row, self.rates)
        assert rec.project_id == "json-proj"
        assert rec.tags["team"] == "platform"


# ---------------------------------------------------------------------------
# Test: pagination handling
# ---------------------------------------------------------------------------

class TestFetchCostRows:
    def _mock_column(self, name: str) -> MagicMock:
        col = MagicMock()
        col.name = name
        return col

    def _mock_result(self, rows, columns, next_link=None, skip_token=None):
        result = MagicMock()
        result.columns = [self._mock_column(c) for c in columns]
        result.rows = rows
        result.next_link = next_link
        result.skip_token = skip_token
        # Ensure properties is None by default
        del result.properties
        return result

    def test_single_page(self):
        mock_client = MagicMock()
        columns = ["UsageDate", "SubscriptionId", "ResourceGroup", "MeterCategory",
                    "MeterSubCategory", "Product", "CostInBillingCurrency", "Currency", "Tags"]
        rows = [
            [20240315, "sub-001", "rg-1", "Virtual Machines", "D2s v3", "D2s v3/Win", 10.0, "USD", {}],
        ]
        mock_client.query.usage_by_scope.return_value = self._mock_result(rows, columns)

        result = fetch_cost_rows(
            mock_client, "/subscriptions/sub-001",
            datetime(2024, 3, 1, tzinfo=timezone.utc),
            datetime(2024, 3, 31, tzinfo=timezone.utc),
        )
        assert len(result) == 1
        assert result[0]["SubscriptionId"] == "sub-001"
        mock_client.query.usage_by_scope.assert_called_once()

    def test_pagination_with_next_link(self):
        mock_client = MagicMock()
        columns = ["UsageDate", "SubscriptionId", "ResourceGroup", "MeterCategory",
                    "MeterSubCategory", "Product", "CostInBillingCurrency", "Currency", "Tags"]
        page1_rows = [
            [20240315, "sub-001", "rg-1", "VM", "D2s", "D2s/Win", 10.0, "USD", {}],
        ]
        page2_rows = [
            [20240316, "sub-001", "rg-2", "Storage", "Blob", "Blob/Hot", 5.0, "USD", {}],
        ]

        page1 = self._mock_result(page1_rows, columns, next_link="token-page2")
        page2 = self._mock_result(page2_rows, columns, next_link=None)

        mock_client.query.usage_by_scope.side_effect = [page1, page2]

        result = fetch_cost_rows(
            mock_client, "/subscriptions/sub-001",
            datetime(2024, 3, 1, tzinfo=timezone.utc),
            datetime(2024, 3, 31, tzinfo=timezone.utc),
        )

        assert len(result) == 2
        assert result[0]["UsageDate"] == 20240315
        assert result[1]["UsageDate"] == 20240316
        assert mock_client.query.usage_by_scope.call_count == 2

    def test_pagination_with_skip_token(self):
        mock_client = MagicMock()
        columns = ["UsageDate", "SubscriptionId", "ResourceGroup", "MeterCategory",
                    "MeterSubCategory", "Product", "CostInBillingCurrency", "Currency", "Tags"]
        page1_rows = [[20240315, "sub-001", "rg-1", "VM", "D2s", "D2s/Win", 10.0, "USD", {}]]
        page2_rows = [[20240316, "sub-001", "rg-2", "Storage", "Blob", "Blob/Hot", 5.0, "USD", {}]]

        page1 = self._mock_result(page1_rows, columns, skip_token="skip-abc")
        page2 = self._mock_result(page2_rows, columns)

        mock_client.query.usage_by_scope.side_effect = [page1, page2]

        result = fetch_cost_rows(
            mock_client, "/subscriptions/sub-001",
            datetime(2024, 3, 1, tzinfo=timezone.utc),
            datetime(2024, 3, 31, tzinfo=timezone.utc),
        )
        assert len(result) == 2

    def test_empty_result_set(self):
        mock_client = MagicMock()
        columns = ["UsageDate", "SubscriptionId", "ResourceGroup", "MeterCategory",
                    "MeterSubCategory", "Product", "CostInBillingCurrency", "Currency", "Tags"]
        mock_client.query.usage_by_scope.return_value = self._mock_result([], columns)

        result = fetch_cost_rows(
            mock_client, "/subscriptions/sub-001",
            datetime(2024, 3, 1, tzinfo=timezone.utc),
            datetime(2024, 3, 31, tzinfo=timezone.utc),
        )
        assert result == []

    def test_three_pages(self):
        mock_client = MagicMock()
        columns = ["UsageDate", "SubscriptionId", "ResourceGroup", "MeterCategory",
                    "MeterSubCategory", "Product", "CostInBillingCurrency", "Currency", "Tags"]
        p1 = [[20240310, "sub-001", "rg-1", "VM", "D2s", "D2s/Win", 10.0, "USD", {}]]
        p2 = [[20240311, "sub-001", "rg-1", "VM", "D2s", "D2s/Win", 10.0, "USD", {}]]
        p3 = [[20240312, "sub-001", "rg-1", "VM", "D2s", "D2s/Win", 10.0, "USD", {}]]

        r1 = self._mock_result(p1, columns, next_link="tok2")
        r2 = self._mock_result(p2, columns, next_link="tok3")
        r3 = self._mock_result(p3, columns)

        mock_client.query.usage_by_scope.side_effect = [r1, r2, r3]

        result = fetch_cost_rows(
            mock_client, "/subscriptions/sub-001",
            datetime(2024, 3, 1, tzinfo=timezone.utc),
            datetime(2024, 3, 31, tzinfo=timezone.utc),
        )
        assert len(result) == 3
        assert mock_client.query.usage_by_scope.call_count == 3


# ---------------------------------------------------------------------------
# Test: extractor health marking
# ---------------------------------------------------------------------------

class TestExtractorHealth:
    def test_mark_healthy(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mark_extractor_healthy(
            mock_conn, "azure",
            datetime(2024, 3, 1, tzinfo=timezone.utc),
            datetime(2024, 3, 31, tzinfo=timezone.utc),
            100,
        )

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "ok" in str(call_args)
        mock_conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Test: run_extractor integration (mocked)
# ---------------------------------------------------------------------------

class TestRunExtractor:
    @patch("extractors.azure_cost.psycopg.connect")
    @patch("extractors.azure_cost.fetch_cost_rows")
    @patch("extractors.azure_cost._create_azure_client")
    def test_empty_result_set_graceful(self, mock_client_fn, mock_fetch, mock_pg_connect):
        """When Azure returns 0 rows, extractor exits gracefully and marks healthy."""
        mock_fetch.return_value = []

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pg_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pg_connect.return_value.__exit__ = MagicMock(return_value=False)

        from extractors.azure_cost import run_extractor
        total = run_extractor(
            pg_dsn="postgresql://test:test@localhost/test",
            date_from=datetime(2024, 3, 1, tzinfo=timezone.utc),
            date_to=datetime(2024, 3, 31, tzinfo=timezone.utc),
            subscription_id="sub-001",
        )
        assert total == 0

    @patch("extractors.azure_cost._load_exchange_rates")
    @patch("extractors.azure_cost.insert_records")
    @patch("extractors.azure_cost.psycopg.connect")
    @patch("extractors.azure_cost.fetch_cost_rows")
    @patch("extractors.azure_cost._create_azure_client")
    def test_records_inserted(self, mock_client_fn, mock_fetch, mock_pg_connect, mock_insert, mock_rates):
        """Verify the full pipeline transforms and inserts records."""
        mock_fetch.return_value = [_make_azure_row(), _make_azure_row(subscription_id="sub-002")]
        mock_rates.return_value = {"USD": Decimal("1")}
        mock_insert.return_value = 2

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pg_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pg_connect.return_value.__exit__ = MagicMock(return_value=False)

        from extractors.azure_cost import run_extractor
        total = run_extractor(
            pg_dsn="postgresql://test:test@localhost/test",
            date_from=datetime(2024, 3, 1, tzinfo=timezone.utc),
            date_to=datetime(2024, 3, 31, tzinfo=timezone.utc),
            subscription_id="sub-001",
        )
        assert total == 2
        mock_insert.assert_called_once()
        inserted_records = mock_insert.call_args[0][1]
        assert len(inserted_records) == 2
        assert all(isinstance(r, NormalizedCostRecord) for r in inserted_records)
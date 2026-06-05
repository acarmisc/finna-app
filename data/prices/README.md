# Price Catalog

Minimal SKU price maps used by the wastage rule engine to estimate monthly savings.

> **These are public list prices.** They do not reflect EA/CSP discounts, reserved instances,
> or committed-use discounts. Always verify estimates in the provider's Cost Analysis tool.

## Files

| File | Provider | Currency | Primary region |
|------|----------|----------|----------------|
| `azure_list_prices.json` | Azure | EUR | westeurope |
| `aws_list_prices.json` | AWS | USD | eu-west-1 |
| `gcp_list_prices.json` | GCP | USD | europe-west1 |

## Structure

Each file has a `_meta` block (currency, source, refresh date) followed by
resource-category objects keyed by region then SKU name.

The `pricing.lookup(provider, sku, region)` function expects the SKU in
`"<category>/<sku_name>"` format, e.g. `"managed_disk/Premium_LRS"`.

## Refreshing prices

### Azure

```bash
# Azure Retail Prices REST API — no auth required
curl -s "https://prices.azure.com/api/retail/prices?\$filter=serviceName eq 'Virtual Machines' and armRegionName eq 'westeurope' and priceType eq 'Consumption'" \
  | jq '[.Items[] | {sku: .skuName, price: .retailPrice}]'
```

Update `azure_list_prices.json` manually or use the script below and bump `_meta.refreshed`.

### AWS

```bash
# AWS Pricing API (public, no credentials needed for list prices)
curl -s "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/eu-west-1/index.json" \
  | jq '.products | to_entries[] | select(.value.productFamily == "Storage") | .value.attributes | {sku: .volumeApiName, price: .pricePerUnit}'
```

### GCP

```bash
# GCP Cloud Billing Catalog (requires API key or gcloud auth)
gcloud billing catalogs list --billing-account=BILLING_ACCOUNT_ID \
  --filter="sku.description:Persistent Disk" \
  --format=json
```

## Refresh cadence

Prices change infrequently. A quarterly refresh is sufficient for estimation purposes.
Check provider pricing pages for major changes (new SKUs, region expansions, price reductions).

After refreshing, update `_meta.refreshed` in each file and commit with message:
`chore(prices): refresh list prices <YYYY-MM-DD>`.

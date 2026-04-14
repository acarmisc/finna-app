# FinOps Tagging Strategy

This document defines the required labels and tags for each cloud provider, naming conventions, and how tags map to the `NormalizedCostRecord` model used across the FinOps pipeline.

---

## GCP Labels

GCP labels are key-value pairs attached to resources. They flow through the BigQuery billing export as a repeated struct (`key`, `value`).

### Required Labels

| Label Key      | Description                          | Example           |
|----------------|--------------------------------------|-------------------|
| `project`      | Logical project identifier           | `ml-platform`     |
| `environment`  | Deployment environment               | `prod`            |
| `team`         | Owning team                          | `platform`         |
| `cost-center`  | Billing cost center                  | `eng-001`          |

### GCP Label Example YAML

```yaml
labels:
  project: ml-platform
  environment: prod
  team: platform
  cost-center: eng-001
```

## Azure Tags

Azure tags are key-value pairs on resources. They appear in the Cost Management API output as a JSON object.

### Required Tags

| Tag Key       | Description                          | Example           |
|---------------|--------------------------------------|-------------------|
| `Project`     | Logical project identifier           | `ml-platform`      |
| `Environment` | Deployment environment               | `prod`             |
| `Team`        | Owning team                          | `platform`          |
| `CostCenter`  | Billing cost center                  | `eng-001`           |

### Azure Tag Example YAML

```yaml
tags:
  Project: ml-platform
  Environment: prod
  Team: platform
  CostCenter: eng-001
```

---

## Naming Conventions

These rules apply to both GCP labels and Azure tags:

- **Lowercase only** for values (GCP label keys are always lowercase; Azure tag keys are PascalCase by convention above).
- **Hyphens** as the only separator. No underscores, no spaces, no dots.
- **No spaces** in keys or values.
- **Alphanumeric** characters plus hyphens only.
- Maximum key length: 63 characters (GCP limit; Azure limit is 512 but keep consistent).

### Valid Examples

```
project: ml-platform
environment: prod
team: data-engineering
cost-center: eng-001
```

### Invalid Examples

```
project: ML Platform     # spaces and uppercase
environment: production  # prefer short form: prod/staging/dev
team: data_engineering   # underscores not allowed
cost-center: eng.001     # dots not allowed
```

---

## Tag-to-NormalizedCostRecord Mapping

The `NormalizedCostRecord` Pydantic model (in `models/__init__.py`) has dedicated fields that are populated from cloud labels/tags. Tags that do not map to a dedicated field are preserved in the `tags` JSONB column.

| NormalizedCostRecord Field | GCP Label Source              | Azure Tag Source         | Fallback                     |
|----------------------------|-------------------------------|--------------------------|------------------------------|
| `project_id`               | `labels.project`              | `Tags.Project`          | Resource group (Azure)       |
| `project_name`             | `labels.project-name`         | `Tags.ProjectName`       | Derived from `project_id`    |
| `environment`              | `labels.environment`          | `Tags.Environment`       | `None`                       |
| `team`                     | `labels.team`                 | `Tags.Team`              | `None`                       |
| `tags` (JSONB)             | All labels as `{key: value}`  | All tags as `{key: value}` | `{}`                         |

### Extraction Details

**GCP**: The `gcp_billing` extractor reads the `labels` repeated struct from BigQuery. The `project` label is extracted first and used as `project_id`. All remaining labels are stored in the `tags` JSONB field.

**Azure**: The `azure_cost` extractor reads the `Tags` column from the Cost Management API. The `Project` tag (case-insensitive lookup) is used as `project_id`. All tags are stored in the `tags` JSONB field.

**LLM (OTel Collector)**: LLM telemetry ingested via OTel Collector maps `service.name` to `project_id`, with `model_name`, `trace_id`, and `latency_ms` stored in dedicated columns. OTel resource attributes are stored in `tags`.

---

## Enforcement

- **GCP**: Use Organization Policy constraints (`constraints/requiredlabels`) to enforce required labels at the org or folder level.
- **Azure**: Use Azure Policy definitions with `modify` effect to automatically inject missing tags and deny deployments that lack required tags.
- **CI Check**: Consider adding a pre-deploy lint step that validates labels/tags against the required set before infrastructure changes are applied.
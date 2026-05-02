# FinOps Tagging Strategy

## Required Labels

### GCP

| Key | Description | Example |
|-----|-------------|---------|
| `project` | Logical project | `ml-platform` |
| `environment` | Deployment environment | `prod` |
| `team` | Owning team | `platform` |
| `cost-center` | Billing cost center | `eng-001` |

### Azure

| Key | Description | Example |
|-----|-------------|---------|
| `Project` | Logical project | `ml-platform` |
| `Environment` | Deployment environment | `prod` |
| `Team` | Owning team | `platform` |
| `CostCenter` | Billing cost center | `eng-001` |

## Naming Conventions

- **Lowercase only** for values
- **Hyphens** as separator (no underscores, spaces, or dots)
- **Alphanumeric + hyphens** only
- Max length: 63 characters

### Valid
```yaml
project: ml-platform
environment: prod
team: data-engineering
cost-center: eng-001
```

### Invalid
```yaml
project: ML Platform      # spaces, uppercase
environment: production  # use: prod
team: data_engineering   # underscores
cost-center: eng.001     # dots
```

## Mapping to NormalizedCostRecord

| NormalizedCostRecord Field | GCP Source | Azure Source | Fallback |
|---------------------------|------------|--------------|----------|
| `project_id` | `labels.project` | `Tags.Project` | Resource group |
| `project_name` | `labels.project-name` | `Tags.ProjectName` | Derived |
| `environment` | `labels.environment` | `Tags.Environment` | None |
| `team` | `labels.team` | `Tags.Team` | None |
| `tags` (JSONB) | All labels | All tags | `{}` |

## Enforcement

- **GCP**: Use Organization Policy `constraints/requiredlabels`
- **Azure**: Use Azure Policy with `modify` effect
- **CI**: Add pre-deploy lint to validate required tags

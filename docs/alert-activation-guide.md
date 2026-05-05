# FinOps Alert Activation Guide

This guide covers how to activate and customize the prepared alert rules for a
new client deployment.  All rules ship in a **disabled** state so nothing fires
until you explicitly enable it.

---

## 1. Activating Alerts for a New Client

1. **Configure notification channels** — In Superset, navigate to
   **Alerts & Reports > Alerts** and set up notification integrations:
   - **Email**: Configure the SMTP settings in `superset/superset_config.py`
     (add `SMTP_*` variables) or via environment variables.
   - **Slack**: Add a Slack webhook URL when creating the alert.
   - **Webhook**: Supply a custom endpoint URL when creating the alert.

   Restart the Superset container to pick up config changes:
   ```bash
   docker compose restart superset
   ```

2. **Enable alerts** — In the Superset UI:
   - Navigate to **Alerts & Reports**.
   - Select the alert you want to activate.
   - Click the toggle to **enable** it.
   - Set the evaluation schedule (cron expression or interval).

   Or via the REST API:
   ```bash
   curl -X PUT \
     -H "Authorization: Bearer <ACCESS_TOKEN>" \
     -H "Content-Type: application/json" \
     -H "X-CSRFToken: <CSRF_TOKEN>" \
     -d '{"active": true}' \
     "http://localhost:8088/api/v1/alert/<ALERT_ID>"
   ```

3. **Verify** — Check the **Last run** column on the Alerts page.  A recent
   timestamp and "success" status means the alert evaluated without error.

---

## 2. Setting Budget Thresholds

Two mechanisms control budget thresholds:

### Uniform budget (simplest)

Edit the SQL inline query inside the Superset alert definition.  The budget
threshold lives in the `params` CTE:

```sql
WITH params AS (
    SELECT 25000.00 AS budget_override_usd  -- new value
), ...
```

In the Superset UI: edit the alert, update the SQL, and save.

### Per-project budget (recommended for production)

1. Create the `project_budgets` table (DDL is in `sql/alert_queries.sql` at the
   bottom, currently commented out).  Run it against the database:

   ```sql
   CREATE TABLE IF NOT EXISTS project_budgets (
       project_id     TEXT PRIMARY KEY,
       monthly_budget NUMERIC(18,2) NOT NULL
   );

   INSERT INTO project_budgets (project_id, monthly_budget) VALUES
       ('finops-prod',    15000.00),
       ('ml-platform',    20000.00),
       ('analytics-prod', 12000.00);
   ```

2. When `project_budgets` rows exist for a project, the query uses those
   values automatically.  Projects without a row fall back to
   `budget_override_usd`.

---

## 3. Configuring Notification Channels

Superset alerts deliver notifications via **email**, **Slack**, or a **webhook
endpoint**.  Configure each channel when creating or editing an alert:

| Channel | Configuration                                                                 |
|---------|-------------------------------------------------------------------------------|
| Email   | Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` in               |
|         | `superset/superset_config.py` or environment variables.                      |
|         | Specify the recipient address in the alert definition.                       |
| Slack   | Provide a Slack incoming webhook URL in the alert's notification settings.   |
| Webhook | Supply a custom endpoint URL in the alert's notification settings.           |

To assign a channel, edit the alert and fill in the **Recipients** field
(email) or the **Slack channel / Webhook URL** field.

### SMTP configuration example

Add to `superset/superset_config.py` or set as environment variables:

```python
SMTP_HOST = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "superset@example.com"
SMTP_PASSWORD = "REPLACE_ME_SMTP_PASSWORD"
SMTP_MAIL_FROM = "superset@example.com"
```

---

## 4. Testing Alerts

### Test a single alert manually

1. Open **Alerts & Reports**, find the alert, and click **Run** (play icon).
2. Superset evaluates the SQL trigger immediately.  If the query returns any
   rows (i.e. the condition is met), the alert fires and sends the
   notification.

### Trigger a real alert end-to-end

1. Temporarily lower a threshold so the current data triggers it.
   For example, set `spike_pct` to `1` in the cost_spike query.
2. Enable the alert.
3. Click **Run** or wait for the next scheduled evaluation.
4. Confirm the notification arrives at the configured channel.
5. Restore the original threshold and disable the alert.

### Test notification channels independently

Send a test email by running a Python snippet inside the Superset container:

```bash
docker compose exec superset python -c "
from superset.utils.email import send_email_smtp
send_email_smtp(
    'alerts@example.com',
    'FinOps Alert Test',
    'This is a test notification from Superset.',
)
"
```

---

## 5. Customizing Spike Detection Sensitivity

The cost spike alert has three tunable parameters, all located in the `params`
CTE at the top of the SQL trigger query:

| Parameter            | Default | Effect                                      |
|----------------------|---------|---------------------------------------------|
| `spike_pct`          | 30      | % above baseline that triggers the alert.   |
|                      |         | Lower = more sensitive (more false alarms). |
|                      |         | Higher = less sensitive (may miss spikes).  |
| `lookback_days`      | 7       | Days in the rolling baseline window.        |
|                      |         | Longer = smoother baseline, fewer blips.    |
| `min_baseline_cost`  | 10.00   | Minimum average daily cost (USD) to check.  |
|                      |         | Filters out low-spend noise.                |

To adjust, edit the alert's SQL trigger query in the Superset UI:

```sql
-- In the cost_spike alert's SQL trigger:
WITH params AS (
    SELECT
        20   AS spike_pct,         -- was 30, now more sensitive
        14   AS lookback_days,     -- was 7, now a 2-week baseline
        25.0 AS min_baseline_cost  -- was 10, now filters more noise
), ...
```

After changing values, save the alert for the changes to take effect at the
next scheduled evaluation.
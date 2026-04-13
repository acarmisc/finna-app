# FinOps Alert Activation Guide

This guide covers how to activate and customize the prepared alert rules for a
new client deployment.  All rules ship in **paused** state so nothing fires
until you explicitly enable it.

---

## 1. Activating Alerts for a New Client

1. **Configure contact points** — Edit
   `grafana/provisioning/alerting/contact-points.yml` and replace the
   placeholder values (see section 3 below).  Restart Grafana or reload
   provisioning:
   ```bash
   docker compose restart grafana
   ```

2. **Unpause rules** — In the Grafana UI:
   - Navigate to **Alerting > Alert rules**.
   - Select the **FinOps** folder, group **finops-cost-alerts**.
   - For each rule you want active, click the pause toggle to **unpause** it.

   Or via the HTTP API:
   ```bash
   curl -X POST \
     -H "Authorization: Bearer <API_KEY>" \
     -H "Content-Type: application/json" \
     -d '{"isPaused": false}' \
     "http://localhost:3000/api/v1/provisioning/alert-rules/<UID>/pause"
   ```

3. **Verify** — Check the **State history** column on the Alert rules page.  A
   green checkmark means the rule evaluated without error.

---

## 2. Setting Budget Thresholds

Two mechanisms control budget thresholds:

### Uniform budget (simplest)

Edit the `params` CTE inside the budget_threshold rule in
`grafana/provisioning/alerting/rules.yml`:

```yaml
annotations:
  budget_override_usd: "10000"   # <-- change this
```

And update the matching SQL inline query's `params` CTE:

```sql
WITH params AS (
    SELECT 25000.00 AS budget_override_usd  -- new value
), ...
```

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

## 3. Configuring Contact Points

Edit `grafana/provisioning/alerting/contact-points.yml` and replace each
placeholder:

| Contact Point | Placeholder                  | Replace With                        |
|---------------|------------------------------|-------------------------------------|
| finops-slack  | `REPLACE_ME_SLACK_WEBHOOK`   | Slack incoming webhook URL          |
| finops-email  | `alerts@example.com`         | Real alert recipient email address  |
| finops-webhook| `https:// REPLACE_ME_WEBHOOK_URL` | Your incident management endpoint |

After editing, restart or reload Grafana provisioning.  To assign a contact
point to a notification policy, go to **Alerting > Notification policies** and
map the desired label (e.g. `alert_type=cost_spike`) to the contact point.

---

## 4. Testing Alerts

### Test a single rule manually

1. Open **Alerting > Alert rules**, find the rule, and click **Test rule**.
2. Grafana evaluates the query immediately and shows whether the condition is
   met.  If the result set is non-empty and crosses the threshold, the rule
   would fire.

### Trigger a real alert end-to-end

1. Temporarily lower a threshold so the current data triggers it.
   For example, set `spike_pct` to `1` in the cost_spike query.
2. Unpause the rule.
3. Wait for the next evaluation cycle (or click **Test rule**).
4. Confirm the notification arrives at the contact point.
5. Restore the original threshold and re-pause the rule.

### Test contact points independently

In the Grafana UI: **Alerting > Contact points**, click **Test** on a contact
point to send a synthetic notification without needing a real alert.

---

## 5. Customizing Spike Detection Sensitivity

The cost spike rule has three tunable parameters, all located in the `params`
CTE at the top of the query:

| Parameter            | Default | Effect                                      |
|----------------------|---------|---------------------------------------------|
| `spike_pct`          | 30      | % above baseline that triggers the alert.   |
|                      |         | Lower = more sensitive (more false alarms). |
|                      |         | Higher = less sensitive (may miss spikes).  |
| `lookback_days`      | 7       | Days in the rolling baseline window.        |
|                      |         | Longer = smoother baseline, fewer blips.    |
| `min_baseline_cost`  | 10.00   | Minimum average daily cost (USD) to check.  |
|                      |         | Filters out low-spend noise.                 |

To adjust, edit both the annotation in `rules.yml` (for documentation) and the
`params` CTE in the inline SQL (for actual behavior):

```sql
-- In the cost_spike rule's inline SQL:
WITH params AS (
    SELECT
        20   AS spike_pct,         -- was 30, now more sensitive
        14   AS lookback_days,     -- was 7, now a 2-week baseline
        25.0 AS min_baseline_cost  -- was 10, now filters more noise
), ...
```

And update the annotations to match:

```yaml
annotations:
  spike_pct: "20"
  lookback_days: "14"
  min_baseline_cost_usd: "25"
```

After changing values, restart Grafana or reload provisioning for the changes
to take effect.
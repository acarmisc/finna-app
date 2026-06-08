# LiteLLM extractor deployment

> Local-only. Directory is gitignored — do not commit.

## Files
- `litellm-extractor-cronjob.yaml` — CronJob for `finops-extractor-litellm` in `finna-app-staging`
- `sync-litellm-secret.sh` — copy master-key from `litellm/litellm-secrets` to `finna-app-staging/litellm-master-key`

## First-time install

1. Cut a release tag that includes `extractors/litellm_cost.py` + `httpx` dep — CI pushes
   `ghcr.io/acarmisc/finna-app/finops-extractor:<version>`. Bump the `image:` tag in the
   CronJob manifest to match.

2. Sync the master-key secret:
   ```sh
   ./sync-litellm-secret.sh
   ```

3. Apply the CronJob:
   ```sh
   kubectl apply -f litellm-extractor-cronjob.yaml
   ```

4. Trigger an ad-hoc run to validate:
   ```sh
   kubectl -n finna-app-staging create job --from=cronjob/finops-extractor-litellm \
     litellm-manual-$(date +%s)
   ```

## Rotation

If LiteLLM master-key rotates: rerun `./sync-litellm-secret.sh` — next scheduled run picks
up the new value automatically (env from secretKeyRef is re-read per pod start).

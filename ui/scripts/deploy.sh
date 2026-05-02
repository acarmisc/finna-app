#!/bin/bash
set -e
cd /root/projects/finna-app-ui
npm run build
docker build -t finna-frontend:latest .
docker tag finna-frontend:latest europe-west1-docker.pkg.dev/<gcp-project-id>/finna-app-staging/frontend:latest
docker push europe-west1-docker.pkg.dev/<gcp-project-id>/finna-app-staging/frontend:latest
kubectl rollout restart deployment/finna-console -n finna-app-staging
kubectl rollout status deployment/finna-console -n finna-app-staging --timeout=120s
echo "Done! Frontend: https://<your-domain>"

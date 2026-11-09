# 04 — CI/CD Pipelines (GitHub Actions & GitLab CI) with Zero-Downtime Rollback

Pair with [`vendor/OWASP_CI_CD_Security_Cheat_Sheet.md`](vendor/OWASP_CI_CD_Security_Cheat_Sheet.md) and [`vendor/OWASP_Secrets_Management_Cheat_Sheet.md`](vendor/OWASP_Secrets_Management_Cheat_Sheet.md).

---

## 1. Mandatory CI/CD Security & Reliability Gates

1. **Least-Privilege `permissions` Block**: Always set `permissions: contents: read` at the top of GitHub Actions workflows.
2. **Pin Third-Party Actions & Lockfiles**: Always use `npm ci` / `pip install --require-hashes` / `composer install --no-dev --prefer-dist` and cache dependencies cleanly.
3. **Gate Order**: `Install -> Lint & Typecheck -> Unit & Integration Tests -> Security Audit -> Build Artifact/Image -> Deploy -> Post-Deploy Smoke Check -> Auto-Rollback on Failure`.
4. **Backward-Compatible DB Migrations**: Run expand-only migrations before switching application traffic so rolling back the container never breaks against the database schema.

---

## 2. Production GitHub Actions Template (`.github/workflows/ci-cd.yml`)

```yaml
name: Production CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  packages: write

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}

jobs:
  verify:
    name: Lint, Typecheck, Test & Security Audit
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm

      - name: Install clean dependencies
        run: npm ci

      - name: Strict Typecheck & Lint
        run: |
          npm run typecheck --if-present
          npm run lint --if-present

      - name: Run Automated Tests
        run: npm test --if-present

      - name: Dependency Security Audit
        run: npm audit --omit=dev --audit-level=high

  deploy:
    name: Build & Zero-Downtime Deploy
    needs: verify
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4

      - name: Deploy & Verify Healthcheck via SSH
        env:
          SSH_PRIVATE_KEY: ${{ secrets.PROD_SSH_KEY }}
          SSH_HOST: ${{ secrets.PROD_SSH_HOST }}
          SSH_USER: ${{ secrets.PROD_SSH_USER }}
        run: |
          mkdir -p ~/.ssh
          echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan -H "$SSH_HOST" >> ~/.ssh/known_hosts

          ssh "$SSH_USER@$SSH_HOST" << 'EOF'
            set -euo pipefail
            cd /srv/app
            PREV_COMMIT=$(git rev-parse HEAD)
            git fetch origin main
            git reset --hard origin/main

            docker compose -f docker-compose.prod.yml build --pull api
            docker compose -f docker-compose.prod.yml up -d --no-deps api

            echo "Waiting for readiness healthcheck..."
            for i in $(seq 1 15); do
              if curl -fsS http://127.0.0.1:3000/healthz > /dev/null; then
                echo "Deployment healthy!"
                exit 0
              fi
              sleep 2
            done

            echo "ERROR: Smoke check failed! Rolling back to $PREV_COMMIT..."
            git reset --hard "$PREV_COMMIT"
            docker compose -f docker-compose.prod.yml up -d --build --no-deps api
            exit 1
          EOF
```

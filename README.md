# workflows

Reusable GitHub Actions workflows.

## Reusable CI — `.github/workflows/ci.yml`

A single, language-aware CI pipeline for **Node.js**, **Python** and **Go** projects.

```
Plan ─┬─ Validate ─────────────── formatting · linting · type checking
      ├─ Test ─────────────────── unit · integration · coverage
      ├─ Security / Dependencies ─ dependency review · npm/pip-audit/govulncheck
      ├─ Security / Secrets ────── TruffleHog
      └─ Security / Code ───────── CodeQL
                 │
                 └─ Container (optional) ─ build · Trivy scan · SBOM · push to GHCR · provenance
                              │
                              └─ CI result ─ summary table + single required status check
```

| Component | Implementation |
|---|---|
| Checkout | `actions/checkout` with `persist-credentials: false` |
| Runtime setup | `setup-node` / `setup-python` / `setup-go` (+ pnpm / corepack for yarn) |
| Dependency caching | Built-in cache of the setup actions, keyed on the lockfile; buildx GHA cache for images |
| Formatting | Prettier · `ruff format --check` · `gofmt -l` |
| Linting | ESLint · `ruff check` · golangci-lint |
| Type checking | `tsc --noEmit` · mypy · `go vet` |
| Unit tests | `<pm> test` · pytest · `go test -race` |
| Integration tests | Optional, with an optional docker compose file for service dependencies |
| Coverage | Reads lcov, Cobertura XML, Istanbul json-summary or Go coverprofile; enforces `coverage-threshold` |
| Security scanning | Dependency review (PRs), language audit, TruffleHog secrets, CodeQL `security-extended` |
| Docker build | `docker/build-push-action` (multi-platform via QEMU) |
| Image scanning | Trivy (SARIF to code scanning + severity gate) |
| SBOM | Syft SPDX artifact + BuildKit SBOM attestation in the image |
| Image publishing | GHCR, only on non-`pull_request` events and only when every gate passed |
| Provenance | BuildKit provenance (`mode=max`) + `actions/attest-build-provenance` |
| Status reporting | Per-job step summaries, annotations, SARIF, and a final `CI result` job |

All third-party actions are pinned to full commit SHAs.

### Usage

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]
    tags: ["v*"]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  ci:
    uses: pslabs2/workflows/.github/workflows/ci.yml@main # pin to a tag or SHA in production
    permissions:
      contents: read
      actions: read
      security-events: write # CodeQL + Trivy SARIF
      packages: write        # push to GHCR
      id-token: write        # provenance signing
      attestations: write    # provenance storage
    with:
      language: node
      coverage-threshold: 80
      enable-docker: true
```

> The caller must grant **all** of the permissions above, even when `enable-docker` is
> `false`: GitHub validates the permissions of every job in a reusable workflow up front.

Mark the **`CI result`** check as required in branch protection — it fails if any stage failed.

### Inputs

| Input | Default | Description |
|---|---|---|
| `language` | — (required) | `node`, `python` or `go` |
| `language-version` | from `.nvmrc`/`.node-version`, `.python-version`, `go.mod`; else `lts/*` / `3.x` | Runtime version |
| `working-directory` | `.` | Project directory (monorepos) |
| `package-manager` | detected from lockfile | `npm`, `pnpm` or `yarn` |
| `runs-on` | `ubuntu-latest` | Runner label |
| `timeout-minutes` | `30` | Per-job timeout |
| `install-command`, `format-command`, `lint-command`, `typecheck-command`, `unit-test-command`, `integration-test-command`, `audit-command` | language default | Override a step. Use `skip` to disable it |
| `compose-file` | — | Compose file (relative to `working-directory`) started with `--wait` before integration tests |
| `coverage-file` | `coverage/lcov.info` · `coverage.xml` · `coverage.out` | Coverage report, relative to `working-directory` |
| `coverage-threshold` | `0` (report only) | Minimum line coverage % |
| `enable-dependency-review` | `true` | Run dependency review on PRs |
| `dependency-review-fail-on-severity` | `high` | |
| `enable-secret-scan` | `true` | TruffleHog (verified + unknown results) |
| `enable-codeql` | `true` | CodeQL (private repos need GitHub Code Security) |
| `enable-docker` | `false` | Build/scan/publish an image |
| `dockerfile` / `docker-context` | `Dockerfile` / `.` | Relative to the repository root |
| `image-name` | `ghcr.io/<owner>/<repo>` | |
| `platforms` | `linux/amd64` | e.g. `linux/amd64,linux/arm64` |
| `build-args` | — | Newline-separated |
| `push-image` | `true` | Push on non-PR events |
| `image-scan-severity` | `CRITICAL,HIGH` | |
| `fail-on-image-vulnerabilities` | `true` | Fail when Trivy finds fixable vulns at that severity |

Outputs: `image-name`, `image-digest`, `image-tags`, `coverage`.

### Language defaults

| Step | Node (npm shown) | Python | Go |
|---|---|---|---|
| Install | `npm ci` | `pip install -r requirements-dev.txt` / `requirements.txt`, `pip install -e ".[dev]"`, plus ruff/mypy/pytest/pytest-cov/pip-audit | `go mod download` |
| Format | `npm run format:check` if defined, else `prettier --check .` | `ruff format --check .` | `gofmt -l .` must be empty |
| Lint | `npm run lint` if defined, else `eslint .` | `ruff check .` | golangci-lint (action) |
| Type check | `npm run typecheck`, else `tsc --noEmit` if `tsconfig.json`, else skipped | `mypy .` | `go vet ./...` |
| Unit tests | `npm run test:unit` if defined, else `npm test` | `pytest --cov` (excluding `tests/integration`) | `go test -race -coverprofile=coverage.out ./...` |
| Integration | `npm run test:integration` if defined | `pytest tests/integration` if present | `go test -tags=integration ./...` if any `//go:build integration` test |
| Audit | `npm audit --audit-level=high` | `pip-audit` | `govulncheck ./...` |

Node projects must commit a lockfile. For Node coverage, make your test script write
`coverage/lcov.info` (or set `coverage-file`).

### Verifying published images

```sh
gh attestation verify oci://ghcr.io/<owner>/<repo>@<digest> -R <owner>/<repo>
```

### Self-test

`.github/workflows/self-test.yml` runs actionlint and calls the workflow against the Go
(with Docker), Python (with a Redis integration test) and Node fixtures in `tests/fixtures/`.

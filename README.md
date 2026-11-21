# workflows
Reusable GitHub Actions CI/CD workflows.

| Workflow | Does |
| --- | --- |
| `ci-node.yaml` | npm/pnpm/yarn install, `lint`, `test`, `build` scripts (skipped if missing) |
| `ci-python.yaml` | pip install, ruff lint + format check, optional mypy, pytest |
| `ci-go.yaml` | `go mod tidy` check, gofmt, go vet, golangci-lint, `go test -race`, `go build` |
| `ci-helm.yaml` | `helm dependency build`, `helm lint`, `helm template`, kubeconform validation |
| `cd-node.yaml` | Build multi-arch Docker image and push to GHCR, passing `NODE_VERSION` build arg |
| `cd-python.yaml` | Build multi-arch Docker image and push to GHCR, passing `PYTHON_VERSION` build arg |
| `cd-go.yaml` | Build multi-arch Docker image and push to GHCR, passing `GO_VERSION` (from `go.mod`) build arg |

## Usage

```yaml
# .github/workflows/ci.yaml in your repo
name: CI
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  node:
    uses: pslabs2/workflows/.github/workflows/ci-node.yaml@main
    with:
      node-version: "22"
      package-manager: pnpm

  python:
    uses: pslabs2/workflows/.github/workflows/ci-python.yaml@main
    with:
      python-version: "3.13"
      run-typecheck: true

  go:
    uses: pslabs2/workflows/.github/workflows/ci-go.yaml@main

  helm:
    uses: pslabs2/workflows/.github/workflows/ci-helm.yaml@main
    with:
      chart-path: charts
```

### CD (Docker images to GHCR)

```yaml
# .github/workflows/cd.yaml in your repo
name: CD
on:
  push:
    branches: [main]
    tags: ["v*"]

jobs:
  image:
    uses: pslabs2/workflows/.github/workflows/cd-node.yaml@main  # or cd-python / cd-go
    permissions:
      contents: read
      packages: write
      id-token: write      # for provenance attestation
      attestations: write  # for provenance attestation
    with:
      node-version-file: .nvmrc
```

Images are published as `ghcr.io/<owner>/<repo>` (override with `image-name`) and tagged by branch, PR, semver, short SHA and `latest` on the default branch (override with `tags`). Images are built but never pushed on `pull_request` events. The language version is passed as a build arg, so declare it in your Dockerfile, e.g. `ARG NODE_VERSION=22` / `FROM node:${NODE_VERSION}-alpine`. Outputs: `image`, `digest`, `tags`.

See the `inputs` section of each workflow for all options (`working-directory`, `runs-on`, toggles for each step, etc.).

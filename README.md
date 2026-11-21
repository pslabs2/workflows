# workflows
Reusable GitHub Actions CI workflows.

| Workflow | Does |
| --- | --- |
| `ci-node.yaml` | npm/pnpm/yarn install, `lint`, `test`, `build` scripts (skipped if missing) |
| `ci-python.yaml` | pip install, ruff lint + format check, optional mypy, pytest |
| `ci-go.yaml` | `go mod tidy` check, gofmt, go vet, golangci-lint, `go test -race`, `go build` |
| `ci-helm.yaml` | `helm dependency build`, `helm lint`, `helm template`, kubeconform validation |

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

See the `inputs` section of each workflow for all options (`working-directory`, `runs-on`, toggles for each step, etc.).

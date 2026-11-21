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
| `onboard-app.yaml` | Onboard the app onto the GitOps repo [`pslabs2/infra`](https://github.com/pslabs2/infra) (Argo CD app of apps) |

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

### Onboarding to infra (Argo CD)

`onboard-app.yaml` commits two files straight to the infra repo's `main`:

- `apps/<app>/values.yaml`: values for the shared chart `charts/app` (a Deployment, Service and optional Ingress per component)
- `clusters/<cluster>/<app>.yaml`: an Argo CD Application (namespace `<app>`), which the root app syncs automatically

```yaml
# in .github/workflows/cd.yaml, after the image jobs
  onboard:
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
    needs: [backend, frontend]
    uses: pslabs2/workflows/.github/workflows/onboard-app.yaml@main
    permissions:
      contents: read
      packages: read  # to resolve image digests
    with:
      app-client-id: ${{ vars.INFRA_APP_CLIENT_ID }}
      # ingress-host: chat.example.com   # default <app>.localhost
    secrets:
      app-private-key: ${{ secrets.INFRA_APP_PRIVATE_KEY }}
      infra-token: ${{ secrets.INFRA_TOKEN }}  # used if no GitHub App is configured
```

- **Components** come from `deploy/values.yaml` in the app repo (see [template-chat](https://github.com/pslabs2/template-chat/blob/main/deploy/values.yaml)). Without that file, every `Dockerfile` in the repo root or a subdirectory becomes a component, with its `EXPOSE` port and an ingress for `frontend` (or the only component). The `values` input is deep-merged on top.
- **Images** default to `ghcr.io/<owner>/<repo>-<component>:sha-<short sha>`, matching the `cd-*` workflows with `image-name: <repo>-<component>`, and are pinned by digest. The job fails if an image doesn't exist yet.
- **Idempotent**: once onboarded, later runs only print a notice. Set `overwrite: true` to regenerate the files, which discards edits made in infra. The job refuses to reuse another Application's name or namespace.
- **Credentials**: `GITHUB_TOKEN` can't write to another repo. Use a GitHub App installed on the infra repo with **Contents: read and write** (`app-client-id` + the `app-private-key` secret), or a fine-grained PAT with the same permission (the `infra-token` secret). Organization-level variables and secrets let every repo created from the template use them. `dry-run: true` renders and validates without credentials or pushing.

After onboarding, the infra repo is the source of truth. To roll out a new image, change `image.tag` and `image.digest` in `apps/<app>/values.yaml`.

See the `inputs` section of each workflow for all options (`working-directory`, `runs-on`, toggles for each step, etc.).

# Branch protection & CI

## What blocks a bad change

| Layer | What it does |
|-------|----------------|
| **GitHub branch protection on `main`** | Force-push/delete disabled; PRs required for non-owner contributors |
| **Required status check `ci`** | PR cannot merge until `.github/workflows/ci.yml` passes (strict: branch must be up to date) |
| **Required PR review + CODEOWNERS** | At least one approving review from **@akshatnavlani** (code owner) for others' PRs |
| **Owner (`@akshatnavlani`)** | Can merge own PRs without waiting for another reviewer (`enforce_admins` off). Still keep CI green before merging. |
| **Conversation resolution** | Open review threads must be resolved |
| **CI guards** | pytest, ruff, no tracked `.env`/keys, no `pull_request_target`, no write workflow perms |

`.github/CODEOWNERS` owns all paths as `@akshatnavlani`, so teammate / Dependabot / agent PRs need your approval.

## Local checks (same as CI)

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest -q
```

## Agent / contributor workflow

1. `git fetch origin && git checkout main && git pull origin main`
2. `git checkout -b issue/D1-XX`
3. Implement, run local checks
4. Push branch and open PR → `main`
5. Wait for **ci** to go green + **@akshatnavlani** review (unless you are the owner merging your own PR)
6. Merge via GitHub UI (squash or merge)

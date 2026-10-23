# Branch protection & CI

## What blocks a bad change

| Layer | What it does |
|-------|----------------|
| **GitHub branch protection on `main`** | No direct pushes; changes only via PR; force-push/delete disabled; admins included |
| **Required status check `ci`** | PR cannot merge until `.github/workflows/ci.yml` passes |
| **Required PR review** | At least one approving review |
| **Conversation resolution** | Open review threads must be resolved |
| **CI guards** | pytest, ruff, no tracked `.env`/keys, no `pull_request_target`, no write workflow perms |

CI alone cannot stop `git push origin main`. Branch protection does that; CI is the test gate the protection rule requires.

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
5. Wait for **ci** to go green + get a review
6. Merge via GitHub UI (squash or merge — no direct push)

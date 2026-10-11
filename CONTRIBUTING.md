# Contributing to ZenCRM

## Running tests locally

Unit tests use the project virtual environment (`venv/`) and Node 24:

```bash
venv/bin/python -m unittest discover -s tests
node --test tests/*.cjs
```

Lint with the minimal rule set in `ruff.toml` (syntax errors and undefined names):

```bash
venv/bin/pip install -r requirements-dev.txt
venv/bin/ruff check .
```

On macOS two template-rendering tests fail because the sandbox's `RLIMIT_AS` limit
is too small for macOS processes; they pass on Linux and in CI.

### End-to-end tests (Playwright)

```bash
npm ci
npx playwright install chromium
npm test                 # whole suite
npm run test:ui          # interactive UI mode: watch, step through, pick selectors
npx playwright codegen http://127.0.0.1:5101   # record a new test against a running suite server
```

Without `BASE_URL`, Playwright starts the application twice from `venv` on throwaway
databases (port 5101 for the suite, 5102 for the first-run test) and stops it
afterwards. Your own database is not used. Flask's `instance/` directory is shared,
so tests must not upload files.

To test the Docker image exactly as CI does:

```bash
docker build -t zencrm:local .
.github/scripts/container-smoke.sh zencrm:local zencrm-e2e 8081
.github/scripts/container-smoke.sh zencrm:local zencrm-first-run 8082
BASE_URL=http://127.0.0.1:8081 FIRST_RUN_BASE_URL=http://127.0.0.1:8082 npx playwright test
docker rm -f zencrm-e2e zencrm-first-run && docker volume rm zencrm-e2e-data zencrm-first-run-data
```

Writing tests:

- Use `test` and `expect` from `e2e/fixtures.ts`. Its fixtures (`adminPage`,
  `employeePage`, `api`, `uniqueName`) give logged-in pages, an API client for test
  data, and unique record names so tests can run in parallel.
- The fixtures fail a test on an uncaught page error, an unexpected `console.error`,
  or an API response with status 500 or higher. Extend `ALLOWED_CONSOLE_ERRORS` only
  with a justified, specific pattern.
- Select elements by role and visible text. Prepare data through the API; exercise
  the behaviour under test through the UI.
- The public helpdesk accepts 5 submissions per hour per address: keep it to one
  submission per suite run.

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request and on pushes to `main`:

| Job | What it does |
|---|---|
| `lint` | `ruff check .` |
| `unit` | Python `unittest` and `node --test` suites |
| `image` | Builds the `amd64` image, starts it on a fresh volume (`container-smoke.sh`), runs the Playwright suite against it, then scans it with Trivy (fails on fixable CRITICAL or HIGH findings) |
| `image-arm64` | Builds and smoke-tests the `arm64` image when a PR changes `Dockerfile`, `requirements.txt` or `entrypoint.sh` |

`lint`, `unit` and `image` are required checks for merging into `main`. When `image`
fails, download the `e2e-report` artifact from the run: open
`playwright-report/index.html`, or a trace with `npx playwright show-trace <trace.zip>`.

Dependabot opens grouped weekly updates for Python, npm, GitHub Actions and the
Docker base image. Third-party actions are pinned to commit SHAs.

## Releasing

1. In a pull request, set `VERSION` to the new version (for example `0.9.0.6`) and merge it.
2. Tag the merged commit on `main` and push the tag:

   ```bash
   git fetch origin
   git tag v0.9.0.6 origin/main
   git push origin v0.9.0.6
   ```

3. `.github/workflows/release.yml` then:
   - checks the tag format, that the tag equals `VERSION`, and that the commit is on `main`;
   - runs the whole CI workflow on the tagged commit;
   - builds `amd64` and `arm64` images on native runners, smoke-tests each, and pushes them by digest;
   - publishes the multi-architecture image as `<version>` and, for stable releases,
     `latest` to `ghcr.io/<owner>/<repository>` (lowercased) and, when the `DOCKERHUB_IMAGE` variable is
     set, to Docker Hub; attests build provenance on GHCR;
   - creates the GitHub Release with generated notes, last, so the application's
     Settings → Updates never offers a version without an image.

A tag with a suffix (`v0.9.1.0-rc1`, with the same value in `VERSION`) publishes a
pre-release: the version tag only, never `latest`.

If a job fails, fix the cause and use "Re-run failed jobs"; no step publishes a partial result. The
per-architecture digests are kept for one day, so re-run `publish` alone within 24 hours,
or re-run the whole workflow after that.

### Rolling back `latest`

Version tags are immutable; fix a bad release with a new version. In an emergency,
point `latest` back to the previous version in each registry:

```bash
docker buildx imagetools create -t ghcr.io/zencrm/zencrm:latest ghcr.io/zencrm/zencrm:<previous-version>
docker buildx imagetools create -t <docker-hub-image>:latest <docker-hub-image>:<previous-version>
```

## One-time repository setup

| Owner | Step |
|---|---|
| Project Docker Hub account owner | Create a personal access token with *Read & Write* scope on the dedicated project account. Keep the account credentials in the team password manager with 2FA enabled. |
| Repository admin | Settings → Environments → `release`: secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`; deployments limited to tags `v*`. Repository variable `DOCKERHUB_IMAGE` (for example `zencrm/zencrm`). |
| Repository admin | Ruleset for `main`: require a pull request and the checks `lint`, `unit`, `image`; block force pushes. |
| Repository admin | Ruleset for tags `v*`: creation by maintainers only; block deletion and updates. |
| Organization admin | After the first release: Packages → `zencrm` → change visibility to Public and link it to the repository. |
| Repository admin | Settings → Code security: enable Dependabot alerts and code scanning. |

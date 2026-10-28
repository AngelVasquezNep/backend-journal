# Quickstart and validation guide

The application and deterministic story slices are implemented. Actual commands/results
and remaining reference-review/live-provider/human-study gates are in [validation.md](validation.md).
Skipped live/human checks are not passed acceptance gates. Preserve reviewer-owned checklist markers.

## Start the local application

Use Docker with Compose, uv, Python 3.14 for Identity and Python 3.12 for Knowledge/Chat.
Frontend development uses Node 22.12+ and the pnpm version pinned in package.json.
Run commands from this project directory; the enclosing Git repository root is two levels above it.

For an existing named-volume installation, choose a
[fresh start or data migration](../../infra/local-storage.md) before starting services.

```sh
python3 infra/init-env.py
docker compose build
mkdir -p data/postgres data/originals
docker compose run --rm --no-deps --user root --entrypoint chown knowledge 10001:10001 /data/originals
docker compose up -d
docker compose ps
```

The generator creates an ignored 0600 `.env` with independent random development secrets,
stub mode and blank provider key/model. It refuses to overwrite existing configuration.
Keep the existing local `.env` if already initialized. Compose synchronizes local database
passwords, runs migrations, and waits for API readiness before starting the web app.
The operator and migration containers normally exit with status 0. Migration and worker
services use the matching built application image, avoiding schema/image drift. When
updating code, repeat `docker compose build` and `docker compose up -d`, or combine them
with `docker compose up -d --build`. Runtime containers never receive migration credentials.
Production password rotation requires a separately coordinated operator procedure.

Open http://localhost:8080. It is a loopback development origin; production requires HTTPS,
secure cookies and encrypted service traffic. Nginx exposes only the static SPA and `/api/v1`,
stripping identity claims and blocking internal/health/metrics routes. The databases and
Knowledge originals persist in `data/postgres/` and `data/originals/` respectively.
Chat never mounts Knowledge files or a Docker socket.

## Provision and use accounts

The operator CLI prompts for a hidden confirmed initial password; never pass passwords in arguments:

```sh
docker compose run --rm identity taskify-admin create --company-name "Company A" --display-name "Admin A" --email admin-a@example.test
docker compose run --rm identity taskify-admin create --company-name "Company B" --display-name "Admin B" --email admin-b@example.test
```

For another admin in an existing company, replace --company-name with --company-id UUID.
Log in at `/login` and change the initial password. Admins create user-role accounts at
`/admin/users`, sharing initial credentials through their company's trusted channel.
New users also must change their initial password. There is no external signup or third role.
CLI outputs contain identifiers, never passwords; see [CLI contract](contracts/cli.md).

Admin knowledge controls at `/admin/knowledge` accept PDF, DOCX, strict UTF-8/BOM TXT,
PNG/JPEG and scanned PDFs, from 1 byte through 20 MiB. Processing becomes ready or a safe
explanatory failure. English/Spanish OCR runs locally. Users see ready originals at
`/knowledge` with authenticated downloads. Titles/versions and provenance remain server-owned.

Title/replacement/removal mutations require current ETags. A conflict requires reload;
a failed replacement preserves the old ready original. Removal requires explicit confirmation,
excludes subsequent reads/retrieval immediately and cancels pending publication. Old citations
never relink to replacement files. Cleanup removes only guarded unavailable/unreferenced data.

`/chat` restores one saved private conversation per account, including active accepted turns.
It has no new-chat/reset/share controls or model selector. Enter sends; Shift+Enter adds a line.
Only committed results appear: answer, refusal, insufficient information, clarification or failure.
A lost send response reuses its original UUID; deliberate retry after failure creates a new one.
History persists across logout/reload, and every factual source opens the exact currently
available original. Same-company admins cannot read another account's chat.

## Configuration and bounded processing

`.env.example` documents independent runtime/migration database passwords, SESSION_HMAC_KEY,
caller-scoped API/worker credentials, PUBLIC_ORIGIN and explicit AI settings. Every browser
mutation requires exact Origin and current CSRF; cookies are HttpOnly/SameSite and production
__Host/Secure. No credentials, transcript or document cache is persisted in browser storage.
Status polls and background checks do not refresh the 30-minute inactivity boundary.

Optional LangSmith tracing is disabled by default and restricted to Chat/Knowledge.
Follow the [tracing guide](../../infra/tracing.md) for configuration and verification.
Compose aligns modern/legacy tracing flags and hides inputs/outputs; startup rejects
enabled tracing without a LangSmith key or with unhidden payloads.

Knowledge processing requires Linux: a fresh secret-free child enforces 512-MiB address space,
90-second CPU/wall, 32-MiB file-backed output, 40-million decoded pixels and 256-MiB DOCX
expansion limits. Native macOS parser skips do not count as acceptance; use its Linux test
container. Files are immutable/hash-verified. The pipeline records NFC/newline offsets,
800/100 cl100k token splitting and text-embedding-3-small at dimensions=1536. Stub and OpenAI
vector spaces have different immutable version suffixes; never reinterpret old vectors.

Chat's finite LangGraph uses scope → retrieve → generate → verify, without tools/back edges,
checkpoints/stores/caches. Actor context is outside model-writable state. Each attempt has a
20-second shared deadline, 12-step limit and one transient provider retry. History is the newest
complete prior messages within 6000 tokens, separate from the current question; missing older
topics require clarification. History is never factual evidence. The application checks login
and one fresh atomic source snapshot under the SQL lease fence before saving an answer.
Changes after that snapshot permit the validated answer but affect future retrieval/source opens.

Ingestion uses 120-second leases/eight-second heartbeats and up to three transient retries after
the first attempt. Chat uses 30-second leases/four-second heartbeats and at most three claims.
Recovery restarts complete attempts with fresh evidence and the accepted exact answer settings.
Provider cost may repeat; terminal SQL constraints prevent duplicate saved assistant messages.

## Engineering checks

```sh
uv sync --project services/identity --python 3.14 --locked
uv sync --project services/knowledge --python 3.12 --locked
uv sync --project services/chat --python 3.12 --locked
(cd services/identity && TASKIFY_RUN_DB_TESTS=1 .venv/bin/pytest tests -q)
docker compose run --rm --build knowledge-test
(cd services/chat && TASKIFY_RUN_DB_TESTS=1 .venv/bin/pytest tests -q)
(cd services/identity && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy src && .venv/bin/lint-imports)
(cd services/knowledge && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy src && .venv/bin/lint-imports)
(cd services/chat && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy src && .venv/bin/lint-imports)
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend exec playwright install chromium
```

Owned fixtures reject production database names, exercise real RLS/nonowner roles, pool resets,
concurrency, format limits and source/lease fences. TypeScript/Vite/Vitest/Playwright share `@/`;
ESLint checks static/type/re-export/dynamic imports and inward boundaries. Core layers know no
React/Fetch/browser files or service frameworks. Ruff/TSDoc checks cover source documentation.

Prepare disposable host-owned public-flow acceptance fixtures in stub mode:

```sh
services/knowledge/.venv/bin/python tests/fixtures/build_corpus.py --output /tmp/taskify-corpus
services/knowledge/.venv/bin/python tests/fixtures/provision.py --output /tmp/taskify-fixtures.json --corpus /tmp/taskify-corpus --users-per-company 20 --measure-boundaries
TASKIFY_FIXTURES=/tmp/taskify-fixtures.json services/knowledge/.venv/bin/pytest tests/integration/test_contract_compatibility.py -q
TASKIFY_RUN_RESTORE=1 services/knowledge/.venv/bin/pytest tests/integration/test_restore_recovery.py -q
```

The host tool creates admins through CLI, then users/first-password changes/uploads through public
HTTP. It never truncates existing companies. Keep its credential-bearing output ignored/0600.
The restore exercise creates/drops only random isolated databases and checks matching original
bytes, forced RLS and pending-work recovery; see [backup/restore](../../infra/backup-restore.md).

For complete Chromium story checks, use a private 0600 browser-admin JSON file containing email
and replacement (the admin's changed password):

```sh
TASKIFY_E2E_CREDENTIALS=/private/browser-admin.json pnpm --dir frontend test:e2e chat.spec.ts maintenance.spec.ts users.spec.ts
TASKIFY_WEB_ONLY=1 pnpm --dir frontend test:e2e imports.spec.ts
```

Initial-login auth.spec.ts additionally needs a fresh CLI-provisioned admin via private
TASKIFY_E2E_ADMIN_EMAIL, TASKIFY_E2E_ADMIN_PASSWORD and TASKIFY_E2E_NEW_PASSWORD environment
settings. Keep test-results private/ignored: failed-test form snapshots can contain credentials
even with Playwright tracing/screenshots/video disabled. Global setup validates private files
but never runs Docker or adds a public seed/auth-bypass route.

The installed CI workflow at the enclosing repository's `.github/workflows/taskify.yml` runs
owned real-storage suites, strict Linux parsers, frontend checks, the complete composed public
contract suite and isolated restore exercise. The project copy is maintained for review.
Hosted CI has not been executed in this workspace.

## Live acceptance gates

Use a separate disposable OpenAI-mode run with a backend-only OPENAI_API_KEY and explicit
OPEN_AI_MODEL. There is no compiled model default or legacy alias. Exact model/graph/prompt/
profile settings are captured at acceptance; rollouts retain old handlers or drain queued work.
Unsupported native structured-output profiles fail explicitly, without tool/model fallback.
Ordinary readiness validates local configuration/owned schema/dependencies without paid calls.

Changing the chat model does not alter Knowledge embeddings. Changing embedding mode/model/
pipeline requires a new vector version and explicit reindexing. Recreate API/worker containers
with the new configuration, then provision fresh fixtures with --allow-paid-provider. Live
uploads/evaluation can incur substantial provider cost and require explicit opt-in.

Follow [quality evaluation](../../tests/evaluation/README.md) for independent reference review,
50 answerable, 20 unanswerable, 20 within/at/beyond-window multi-turn and 30 adversarial/mixed
cases. The harness verifies exact original identity and separately requires independent factual
support/completeness/conflict/refusal grades. Replay collected results to avoid repeating paid calls.

Follow [capacity and human onboarding](../../tests/load/README.md) for 20 simultaneous questioners,
95% completed within 15 seconds and representative 95% readiness within two minutes. Stub
benchmarks cannot substitute for actual provider latency. SC-003 needs at least ten first-time
eligible human admins and ten users, excluding implementers, with >=90% unaided first-attempt
success per role. Coaching, abandonment and incomplete flows fail and stay in actual denominators.
Automation cannot supply that human evidence.

Record mode/model/pipeline, corpus digest, commands, sample sizes, failures and reviewer/human
outcomes in [validation.md](validation.md). Do not claim merge/production acceptance while these
external evidence gates remain unmet. The full [HTTP](contracts/http.md), [internal](contracts/internal.md)
and [frontend](contracts/frontend.md) contracts remain the authority for all story scenarios,
field boundaries, failures and response-release consistency rules.

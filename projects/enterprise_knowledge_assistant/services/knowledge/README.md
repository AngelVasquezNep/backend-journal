# Taskify Knowledge

Knowledge owns company items, immutable original files, revisions, extraction blocks,
1536-dimensional chunks and its durable ingestion queue. No other service mounts its
private original directory or reads its database. Public reads resolve the current
Identity session online; admin mutations additionally require Origin and CSRF.

Upload/list/item/status/source, internal retrieval/source snapshots and admin maintenance
are implemented. Live provider quality/load and cross-cutting acceptance are recorded
separately; this is not full feature acceptance.

Run from the project root:

```sh
docker compose run --rm knowledge-migrate
docker compose up -d knowledge knowledge-worker
docker compose run --rm --build knowledge-test
```

The test service targets only `knowledge_test`, uses real PostgreSQL/pgvector and local
parsers/OCR, and substitutes explicitly tagged deterministic embeddings. It mounts
public corpus fixtures read-only, never another service's storage. Host unit checks:

```sh
uv sync --project services/knowledge --locked
cd services/knowledge
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run lint-imports
uv run pytest tests/unit
```

Processing requires Linux to enforce a 512-MiB address-space limit plus 90-second CPU
and wall limits in a fresh parser process, with 32-MiB bounded file-backed output. macOS host parser tests skip explicitly;
use the Linux test container for actual acceptance. The child inherits no application
secrets and fetches no remote files. PNG/JPEG and rendered PDF pages are limited to
40 million decoded pixels; DOCX uncompressed entries total at most 256 MiB. Limit,
protected, malformed, unsupported, empty and unreadable outcomes are explicit failures,
never silent truncation. English and Spanish Tesseract packs are installed in images.

Accepted originals contain 1–20,971,520 bytes with matching filename extension, media
type and inspected content: strict UTF-8/BOM TXT, DOCX paragraphs/tables, native/scanned
PDF, PNG or JPEG. Private random filenames are exclusive, read-only after acceptance,
and verified by size/SHA-256 before extraction/publication/source reading. Public
sources authorize the exact current ready revision and return original bytes with
no-store/nosniff. Foreign IDs are 404; stale own revisions are unavailable. Users see
only ready resources; admins also see candidate processing and safe failure outcomes.

A staged original precedes atomic item/revision/job acceptance (202). Claims use a
120-second lease, heartbeat every eight seconds, and increasing fencing versions.
Extraction/embedding run outside long database transactions. A fresh lease and locked
item/candidate/removal check protect the atomic ready-pointer switch. There are three
transient retries after the first attempt (four maximum claims), exponential backoff
and jitter; invalid files are not retried. Old ready content survives a failed candidate.
Complete unreferenced objects older than 24 hours are conservatively swept each minute,
under the same file guards used by acceptance and a fresh database reference check.
Database outages preserve files. Active writable staging is protected by shared file guards;
abandoned staging and obsolete lifecycle data are swept conservatively without restoring availability.

Pipeline metadata is immutable and includes NFC/newline normalization and source maps,
extractor versions, recursive cl100k_base splitting at 800 tokens with 100 overlap,
text-embedding-3-small and dimensions=1536. Blocks preserve page/section/line/OCR
provenance and never cross source block boundaries. Embedding batches contain at most
32 chunks / 25,600 tokens, with ordered finite nonzero vectors. Stub and OpenAI modes
have distinct pipeline version suffixes, preventing accidental mixing of their vector
spaces. Changing a model/backend/pipeline requires a new version and explicit reindex
migration; never reinterpret saved vectors or silently fall back to another model.
OpenAI mode requires a backend-only key; readiness never invokes the paid provider.
Deterministic fixture vectors provide no live quality evidence.

Runtime roles are nonowners with forced tenant RLS and reset transaction-local context.
Migration credentials are operator-only. Core imports only standard-library code and
owned ports. Logs exclude originals, queries, prompts, session/CSRF secrets and keys;
third-party tracing stays off. Configuration and contracts are documented under
`specs/001-company-knowledge-qa/`. There is no positive authentication cache; automatic
status polling and background work never refresh session inactivity.

Title edits, replacement and removal require a quoted current positive `If-Match` ETag.
Missing/malformed versions fail 422; stale edits fail 409 and require reload. Replacement
accepts one validated immutable candidate while retaining the old ready original until
publication. Failed candidates preserve ready content. Removal clears visibility pointers,
supersedes the old current revision and cancels candidate/jobs atomically. Item-before-job
lock ordering avoids publication/removal deadlocks. The admin UI explicitly confirms
removal and never silently retries a stale edit. Users have read/download only.

The worker conservatively cleans regular staging/orphans older than 24 hours under
nonblocking per-key guards shared by staging and acceptance, checking database references
afresh. Obsolete superseded/failed/cancelled originals and derived vectors are retired
only after another locked visibility/queue check. Immutable revision metadata remains,
with an owned retirement record preventing repeated sweeps. Cleanup cannot restore
availability or relink an old citation. Outages preserve private data for the next sweep.

Internal search is worker-only exact cosine over current same-company ready chunks,
limited to 20 candidates and the current immutable vector space. Both active pipeline
and retrieval versions are returned even for empty successful results. Source validation
checks up to 100 history or eight release triples in one SQL snapshot and constructs
exact original paths/locators; unknown/foreign/unavailable triples disclose no metadata.
Identity resolution uses Knowledge worker scope for accepted session references and
never refreshes inactivity. Chat API credentials may hydrate history; only worker
credentials may retrieve or request release validation. No positive identity/source cache
exists. Vector-space mismatches fail 503 instead of being searched across incompatible models.

Operational readiness and metrics are available only on the private service port:
`/health/live`, `/health/ready`, `/metrics`. Ingress returns 404 for these paths.
Counters contain only request/status-class/time and readiness totals; they are process
local and reset on restart. Workers emit fixed outcome/error-code/attempt/count fields,
never documents, queries, prompts, chat text, identities or secrets. Normal readiness
makes no paid provider call; Knowledge/Chat additionally check configured first-party
dependency readiness over bounded nonredirecting HTTP. Third-party tracing remains off.
See `infra/backup-restore.md` for consistent owned-database/private-original recovery.

Long upload/replacement staging is followed by another online session/role/CSRF check
before the acceptance transaction commits. Revocation/expiry rolls back domain changes
and leaves only private staged bytes for cleanup. Owned SQL transactions bound lock
waits to three seconds and individual statements to five seconds.

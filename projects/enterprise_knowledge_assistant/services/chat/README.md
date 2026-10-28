# Taskify Chat

Chat owns one saved private conversation per Identity account, ordered messages,
accepted turns, leases and citation references. Login sessions grant access; they are
not conversation identities. Same-company accounts cannot read each other's history.
There are no new-chat/reset/share controls, agent tools, graph checkpoint tables,
foreign database connections or mounts of Knowledge originals.

Run from the project root after owned migrations:

```sh
docker compose run --rm chat-migrate
docker compose up -d chat chat-worker web
```

Local owned checks (PostgreSQL must be running for integration):

```sh
cd services/chat
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run lint-imports
TASKIFY_RUN_DB_TESTS=1 uv run pytest tests -q
```

Tests reject URLs outside `chat_test`, use distinct runtime/migration roles and actual
forced company+account RLS. Provider/Identity/Knowledge doubles are injected only by
tests, never exposed as public seed/auth-bypass routes. Fixture models give no live
OpenAI quality evidence. Normal runtime APIs/workers have no migration credentials.

All public operations require an online Identity resolution and a changed initial
password. Mutations additionally require exact Origin and current CSRF. A single
account lock protects lazy conversation creation, replay checks, expected sequence and
one active turn. Identical client UUID/content replay is resolved before obsolete
sequence/active checks; changed content with that ID is a conflict. Acceptance commits
one user question plus a queued turn before 202. Reload discovers the active turn and
polls its nonrefreshing endpoint every second. History remains saved across sessions.
Browser state and source object URLs are transient and cleared on account changes.

A turn snapshots AI mode, exact model, graph, prompt and model-profile versions.
`AI_MODE=stub` is local development/test only. `AI_MODE=openai` requires a backend-only
`OPENAI_API_KEY` and explicit `OPEN_AI_MODEL`, with no alias or fallback. Each scope,
generation and verification role uses the accepted model, native Responses structured
output, `store=false`, no tools and zero SDK retries. Optional temperature/reasoning/
token-limit parameters are omitted instead of inferred from a model name. Incompatible
profiles/models fail explicitly. Readiness validates configuration/owned schema without
a paid provider probe; operators must retain old handlers or drain accepted versions.

The [LangGraph graph](https://docs.langchain.com/oss/python/langgraph/graph-api) has
explicit scope → retrieve → generate → verify branches and no back edges. It compiles
without checkpoints, stores or result caches. Immutable actor context is separate from
model-writable state. Each whole attempt is bounded to 12 graph steps and a shared
60-second deadline; all roles share one transient provider retry. Prior history is only
for topic resolution, never facts. The newest complete prior messages fit within 6000
cl100k tokens; older messages stay saved but missing/ambiguous referents require a
clarification. The current question is separate and limited to 4000 code points.

Knowledge searches fresh same-company/current-ready evidence on every attempt. At most
20 candidates are decoded, deduplicated to eight chunks, then checked for relevant
supported claims. Empty evidence differs from an outage. Mixed requests can answer
only the company part and explicitly decline the rest. Document/history instructions
cannot authorize tools, ownership changes or factual release. Unsupported claims,
unknown IDs, model URLs, HTML and failed grounding become safe failures. There are
five saved outcomes: answer, refusal, insufficient_information, clarification, failure.
No unverified tokens or partial drafts stream to the browser.

After the graph, application code revalidates the accepting login, checks supplied
citation membership and calls Knowledge for one fresh atomic exact-source snapshot
while holding the current SQL turn fence. Only then can it atomically append one
assistant result, citations and the terminal attempt's retrieval version. Pending turns
have a null retrieval version; a successful empty search still records its version at
completion. Final source validation is the release consistency checkpoint: removal or
replacement before it blocks factual release; a change afterward permits the validated
answer but immediately affects future retrieval, hydrated links and original opens.
Saved old labels/locators are never relinked to replacement files.

Workers use 30-second leases and four-second heartbeats, up to 20 concurrent attempts.
An abandoned lease restarts the first graph node with fresh own history/evidence,
accepted answer settings and then-active Knowledge retrieval configuration. At most
three claims are allowed; exhausted abandoned turns receive one safe terminal failure.
Unique message/turn constraints and increasing lease versions prevent duplicate saves.
An expired/reclaimed worker cannot reuse a previous source receipt. Whole-turn recovery
may repeat provider cost; there is no durable node-level resume guarantee.

Logs/metrics exclude chat text, evidence, prompts, passwords, API keys, cookies and CSRF
secrets. LangSmith tracing is off by default; opt-in graph/model traces hide inputs and
outputs as described in the [tracing guide](../../infra/tracing.md).
API source hydration uses Chat API scope; retrieval
and release use worker scope. Internal URLs are nonpublic and require encrypted traffic
in production. Contracts live under `specs/001-company-knowledge-qa/contracts/`.

Operational readiness and metrics are available only on the private service port:
`/health/live`, `/health/ready`, `/metrics`. Ingress returns 404 for these paths.
Counters contain only request/status-class/time and readiness totals; they are process
local and reset on restart. Workers emit fixed outcome/error-code/attempt/count fields,
never documents, queries, prompts, chat text, identities or secrets. Normal readiness
makes no paid provider call; Knowledge/Chat additionally check configured first-party
dependency readiness over bounded nonredirecting HTTP. Optional LangSmith exports are
outside readiness checks and do not require a paid provider probe.
See `infra/backup-restore.md` for consistent owned-database/private-original recovery.

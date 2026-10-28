# Research: Taskify Company Knowledge Q&A

**Date**: 2026-10-20
**Inputs**: [Specification](spec.md), constitution v1.0.0, and the requested stack.

The requested “langchaing” is interpreted as LangChain. Decisions below are project choices;
linked primary documentation establishes capabilities, not a guarantee that Taskify meets its
quality or latency targets. Phase 0 research used separate retrieval and architecture research
agents plus direct review of official OpenAI documentation. All design questions are resolved.
No application or paid provider calls were made during planning.

## R-01: Application boundaries and hexagonal architecture

**Decision**: Three independently deployable Python services: Identity, Knowledge, and Chat.
The initial design selected Python 3.12 for all three. The user updated Identity to Python 3.14
on 2026-10-21; Knowledge and Chat retain Python 3.12. Frontend dependency management uses pnpm
per the user's instruction on the same date.
Each has its own PostgreSQL database, database credentials, migrations, package, and dependency
lock. Knowledge and Chat each have a separately runnable durable worker within their own service
boundary. Use FastAPI and Pydantic v2 for transport adapters, SQLAlchemy 2 and Alembic for storage
adapters. React 19 with strict TypeScript and Vite provides the frontend.

Domain entities and application use cases depend on ports, never on FastAPI, SQLAlchemy,
LangChain, LangGraph, OpenAI, React, or browser globals. React views and HTTP clients are frontend adapters.
Explicit composition roots connect adapters to ports. Pin compatible patched dependency versions
and container digests during implementation, rather than pretending a planning document is a lock.

**Rationale**: These boundaries satisfy independent deployment and the user's architecture choices.
**Alternatives considered**: A monolith violates the constitution; separate embedding, OCR, and
retrieval services add distributed coordination before there is a separate business owner.

**Sources**: [Original hexagonal architecture](https://alistair.cockburn.us/hexagonal-architecture),
[FastAPI](https://fastapi.tiangolo.com/),
[Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/),
[React application setup](https://react.dev/learn/build-a-react-app-from-scratch),
[TypeScript strict mode](https://www.typescriptlang.org/tsconfig/strict),
[Vite prerequisites](https://vite.dev/guide/).

## R-02: First-party login and identity propagation

**Decision**: Email/password authentication owned by Identity, Argon2id through `pwdlib`, and
cryptographically random opaque login tokens in HttpOnly cookies. Store only token digests.
Use the specified 30-minute inactivity timeout. Require a changed password on first login and
increment the account credential version, revoke all previous sessions, and issue a new login token atomically after successful password change. A concurrent login cannot mint a session from an obsolete password/version. No OAuth, external identity provider,
or browser-stored bearer token. Login uses exact same-origin and JSON-content checks;
authenticated mutations also require a session-bound synchronizer CSRF token.

Every protected service request validates the login with Identity through an authenticated
internal interface; do not positively cache validation. Background turn processing revalidates
the accepting login session without extending its inactivity. Service authentication uses
separate scoped bearer credentials over TLS, independent of the user's login. No service trusts
browser-supplied company, account, or role headers. Identity outage fails closed.

**Rationale**: Immediate logout, simple credential ownership, and separate persistent chats.
**Alternatives considered**: Browser JWTs complicate revocation; shared account tables violate
service ownership; adding an external provider contradicts the request.

**Sources**: [FastAPI password hashing](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[OWASP sessions](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[OWASP CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html),
[OWASP microservices](https://cheatsheetseries.owasp.org/cheatsheets/Microservices_Security_Cheat_Sheet.html).

## R-03: LangGraph workflow with LangChain integrations

**Decision**: Use LangGraph `StateGraph` for the bounded company-Q&A workflow, LangChain model,
prompt and structured-output components for LLM steps, and the existing LangChain splitter and
embedding integrations for Knowledge. The Chat application invokes a framework-free `TurnWorkflow`
port implemented by a LangGraph adapter. LangGraph and LangChain types stay outside domain and
application code. Do not use Deep Agents, `create_agent`, `create_deep_agent`, or `ToolNode`.

The acyclic workflow classifies scope/resolves follow-ups, routes pure refusals or clarification,
retrieves current company evidence for allowed questions, routes insufficient evidence, generates
a structured candidate, and verifies grounding/citation membership. A mixed request retains only
the allowed informational question plus an explicit refused-part explanation. Retrieval is an
application-controlled port call, never a model-chosen tool. The model has no browsing, filesystem,
shell, delegation, administrative, or write capabilities. Source text/history remain untrusted.
The graph returns an uncommitted candidate, not permission to release it. Final login/source
validation and the lease-fenced database commit belong to the application after graph completion.

Compile without a checkpointer, memory store or graph result cache. Each turn attempt gets fresh
private state from Chat-owned history and the accepted turn. A crash restarts the whole workflow
with fresh retrieval under the existing SQL queue lease; no node-level continuation is claimed.
Repeated provider calls can incur additional cost after a crash, while unique constraints/fencing
still prevent duplicate saved assistant messages. A 12-step graph limit, no back edges, and the
existing shared 20-second attempt deadline bound execution. Automatic graph/SDK retry policies do
not multiply the application's single transient-provider retry allowance.

**Rationale**: Taskify has several required conditional exits, private conversational context and
mandatory verification gates. An explicit graph makes their order and test coverage visible while
preserving application ownership of authorization and durability. It does not itself guarantee
that answers are factual; the original grounding and real-provider evaluation gates still apply.

**Alternatives considered**:

| Option | Assessment for this feature |
|---|---|
| LangChain components alone | Viable, simpler dependency set; application code would manually maintain the refusal/clarification/evidence/verification branches. Explicit graph routing is chosen for these acceptance-critical paths. |
| LangGraph plus LangChain | Selected: graph control flow plus existing model, embedding and structured-output integrations, without an autonomous tool loop. |
| LangGraph plus native provider SDK only | Feasible, but would replace the already selected LangChain integrations without a feature benefit. |
| Deep Agents | Its filesystem/context harness, subagent delegation and optional planning features provide no required capability for this bounded company-information chatbot. |
| LangGraph persistent checkpoints | Step-level recovery is useful for long-running/human-approval workflows; here it would add a second execution store, retention and replay coordination alongside short SQL-owned turns. Revisit only if those needs arise. |

Use the Responses API and `store=false`. Resolve the model from `OPEN_AI_MODEL` as specified in
R-10. The documented `gpt-5.4-mini-2026-03-17` snapshot remains an example deployment value rather
than a code default; its profile uses `reasoning.effort=none`. Do not force unsupported parameters
onto other configured models or silently switch models on a failure.

**Sources**: [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview),
[LangGraph workflows](https://docs.langchain.com/oss/python/langgraph/workflows-agents),
[LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview),
[Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview),
[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence),
[ChatOpenAI integration](https://docs.langchain.com/oss/python/integrations/chat/openai),
[Official OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
[Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## R-04: Embedding and retrieval process

**Decision**: Extract text with stable source locators; normalize Unicode to NFC and line endings,
retaining an offset-to-source map. Split within pages/sections using LangChain's token-aware
`RecursiveCharacterTextSplitter`, starting with 800 tokens and 100-token overlap. Embed non-empty
chunks with `OpenAIEmbeddings`, `text-embedding-3-small`, 1,536 dimensions, `cl100k_base` token
counting, batches of at most 32 chunks and 25,600 aggregate tokens. The same embedding model,
dimensions, normalization, and pipeline version apply to document and query embeddings.

Store `vector(1536)` in Knowledge's PostgreSQL database with pgvector. Start with exact cosine
search over company-filtered current-ready revisions; B-tree indexes narrow company/item/revision
candidates. Return at most 20 candidates, deduplicate overlapping evidence, and supply up to eight
chunks to generation. Eight chunks and the splitter parameters are tunable project defaults.
An evaluation-calibrated relevance configuration and explicit evidence sufficiency gate determine
whether to answer; a universal cosine cutoff is not assumed. Record the deployed configuration.

**Rationale**: This provides a simple versioned pipeline with usable source provenance and avoids
an additional vector-store service. OpenAI documents the model's 1,536 dimensions and token limits.
**Alternatives considered**: `text-embedding-3-large` requires evaluation to justify added cost;
HNSW requires tenant-filtered recall/load evidence before introduction. A global ANN top-k followed
by application filtering is prohibited because it can both undermine isolation and lose recall.

**Sources**: [Official OpenAI embeddings](https://developers.openai.com/api/docs/guides/embeddings),
[Embedding request limits](https://developers.openai.com/api/reference/resources/embeddings/methods/create),
[LangChain embeddings](https://docs.langchain.com/oss/python/integrations/embeddings/openai),
[Splitter reference](https://reference.langchain.com/python/langchain-text-splitters/character/RecursiveCharacterTextSplitter),
[pgvector filtering](https://github.com/pgvector/pgvector#filtering).

## R-05: Document and image extraction

**Decision**: TXT is UTF-8 text with optional BOM; DOCX extraction uses `python-docx`, including
paragraphs and tables in document order; PDF extraction uses `pypdf`. Render PDF pages without
usable text using `pypdfium2`, then apply Tesseract OCR. Use Pillow plus Tesseract for PNG/JPEG.
Native-text PDF pages avoid OCR. Initial OCR language packs are English and Spanish; language
packs are deployment configuration and accuracy is evaluated on the agreed corpus. Preserve PDF
page numbers, DOCX heading/block/table positions, TXT line ranges, and image bounding boxes.
Originals remain immutable. OCR is text extraction, not arbitrary visual reasoning.

Parsers run in isolated worker subprocesses with bounded CPU, memory, decoded pixel count,
archive expansion, and deadlines. Defaults: 512 MiB per extraction process, 40 million decoded
pixels per raster page, 256 MiB uncompressed DOCX content, and a 90-second extraction deadline.
An exceeded limit gives an actionable failed-processing outcome, never silent truncation or ready
status. The upload limit remains 20 MiB; representative corpus performance must meet SC-006.

**Rationale**: Local extraction avoids sending originals to another processing provider.
**Alternatives considered**: `pypdf` alone cannot OCR. Tesseract alone does not ingest PDF files.
Managed OCR adds another provider. OCRmyPDF is viable but introduces a broader PDF rewrite toolchain
when Taskify only needs page text and locators.

**Sources**: [pypdf extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html),
[python-docx document interface](https://python-docx.readthedocs.io/en/latest/api/document.html),
[pypdfium2 rendering](https://pypdfium2.readthedocs.io/en/stable/python_api.html),
[Tesseract input formats](https://tesseract-ocr.github.io/tessdoc/InputFormats.html),
[Pillow decompression limits](https://pillow.readthedocs.io/en/stable/reference/Image.html).

## R-06: Durable work and atomic knowledge publication

**Decision**: Knowledge owns ingestion jobs and Chat owns answer turns in their respective
PostgreSQL databases. Workers claim short leased jobs with `FOR UPDATE SKIP LOCKED`; commit
claims before network/CPU work, heartbeat leases, and recover abandoned jobs. Ingestion retries
transient failures at most three times with jitter/backoff; invalid files fail without retries.
Chat uses a 20-second per-attempt deadline and at most one bounded retry on a transient provider
failure, within that deadline. Duplicate HTTP submissions are idempotent by client message UUID.

Build all chunks and embeddings in a staging revision. Atomically publish its ready pointer only
when processing succeeds and the item remains eligible. Failed replacements retain previous ready
content. Deletion immediately removes source/read eligibility; physical cleanup is separate.
Final response validation checks all cited revisions in one authoritative Knowledge snapshot. That result is single-use within the fenced terminal commit; reclaimed workers must revalidate.
Any changed/missing revision blocks release; return a retryable changed-information failure rather
than reuse an obsolete draft. This final validation is the response-release consistency checkpoint;
changes after release do not rewrite historical chat, and every later source open checks again.
The checkpoint is the final validation snapshot: a source change afterward may precede terminal
commit or browser display without invalidating that answer, while later retrieval/source opens
must reflect it. Recovery always obtains a new validation snapshot. Each attempt also uses
Knowledge's active retrieval configuration; only answer-model/graph/prompt settings are pinned
at acceptance. The terminal attempt's successful-search retrieval version is nullable audit
metadata saved with its result, keeping recovery current without an acceptance-time Knowledge call.

**Rationale**: Durable processing survives restarts without an initial message broker. Atomic
publication prevents partial content and mixed revisions. Final validation is required in addition
to retrieval-time filtering; the UI buffers factual output until the final outcome is available.
**Alternatives considered**: FastAPI in-memory background jobs lose work on process failure.
Celery plus a durable broker/outbox is suitable later but unnecessary for the initial scale.

**Sources**: [PostgreSQL locking/claims](https://www.postgresql.org/docs/current/sql-select.html),
[FastAPI background-task limits](https://fastapi.tiangolo.com/tutorial/background-tasks/).

## R-07: Ownership and storage

**Decision**: PostgreSQL 16 is the initial deployment baseline, with the compatible pgvector
extension enabled only for Knowledge. Three databases may share a local engine but never tables,
credentials, or cross-service queries. Tenant-bearing tables use application predicates plus
forced row-level security; application roles are neither owners nor `BYPASSRLS`. Chat also applies
account ownership. Tenant context is transaction-local, including pooled connections and workers.

Private immutable files live in a Knowledge-only mounted volume behind an `ObjectStorage` port.
Downloads always pass through Knowledge authorization; no public filesystem path or permanent
presigned download is exposed. Local deployment is single-host. A future S3 adapter supports
multi-host file storage without changing use cases, after its own deployment plan.

**Rationale**: Minimal local infrastructure and a replaceable storage boundary.
**Alternatives considered**: Shared cross-service repositories violate the constitution; adding
MinIO or a managed object-store account is unnecessary for a first local deployment.

**Source**: [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).

## R-08: Private persistent conversation and frontend state

**Decision**: Chat owns a unique `(company_id, account_id)` conversation, ordered messages,
idempotent turns, and citation provenance. Save accepted user messages before queueing work and
save complete terminal results before exposing them. One turn at a time per conversation avoids
ambiguous follow-up ordering. Store full history, paginate it, and use at most 6,000 tokens of
recent account-owned messages for reference resolution. If a reference lies outside usable
context, ask for clarification; history never supplies factual company evidence.

The React UI shows sending/processing/terminal outcomes and polls an accepted turn until done.
It does not stream unverified factual tokens. Keep credentials and raw company content out of
browser persistent storage; re-fetch authorized state after reload/login. Clear in-memory state
when accounts change. History remains server-side through logout. Retry after an operational
failure is an explicit new turn; retrying a lost HTTP response uses the original message UUID.

**Rationale**: Matches the accepted single-conversation clarification with deterministic failure
handling and no need for provider-hosted conversation state or a second graph memory store.
**Alternatives considered**: In-memory chat loses history; multiple chat threads exceed scope;
provider-hosted threads do not replace Taskify's ownership checks. LangGraph checkpointers are
not used as another conversation store: SQL history is supplied explicitly to each graph invocation.

## R-09: Provider data boundary and operational validation

**Decision**: OpenAI receives the minimum question/context and evidence needed for generation,
and normalized chunk text for embeddings. Only backend adapters hold API keys. Use `store=false`
and no hosted provider file stores, tools, background responses, or conversations. This avoids
opting into stored response state but is not a claim of Zero Data Retention; provider abuse
monitoring and account-specific controls still apply. Keep private text, passwords, cookies,
API keys, and session/CSRF tokens out of logs and optional tracing. Third-party tracing is
off by default; optional LangSmith graph/model/embedding tracing requires hidden inputs
and outputs. See the [tracing guide](../../infra/tracing.md) for configuration and limits.

Use pytest, HTTPX, real PostgreSQL/pgvector integration fixtures, frontend Vitest/Testing Library,
and Playwright acceptance scenarios. CI uses deterministic provider doubles. A separately enabled
real-OpenAI evaluation validates retrieval/answer/refusal quality and latency against the frozen
corpus; no pass is claimed until that evaluation runs. Emit request IDs, redacted operational
metrics, queue age, ingestion status, final outcomes, and provider error/latency/token counts.

**Rationale**: Reproducible development and explicit proof of the spec's behavioral requirements.
**Alternatives considered**: Live-provider-only CI is flaky and costly; provider mocks alone cannot
prove answer quality or latency. Automatic prompt tracing would copy private content elsewhere.

**Sources**: [Official OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data),
[Structured-output failure handling](https://developers.openai.com/api/docs/guides/structured-outputs).

## R-10: Explicit environment-selected OpenAI chat model

**Decision**: `OPEN_AI_MODEL` is the canonical, application-owned chat-model environment variable.
The composition root reads it into validated settings and passes the value explicitly to
`ChatOpenAI(model=...)`. It is not a provider SDK auto-discovered variable. In `AI_MODE=openai`,
missing, blank, whitespace-containing, control-containing or over-200-character model IDs fail
local configuration validation before a Chat API/worker becomes ready. Stub mode does not need a
real model or API key. There is no hidden model default, legacy variable alias or provider switch.

The future `.env.example` contains `OPEN_AI_MODEL=gpt-5.4-mini-2026-03-17` as a replaceable example.
Compose must forward it into both `chat` and `chat-worker` at runtime. All chat LLM roles (scope/
follow-up resolution, generation and grounding verification) use the same accepted setting.
Neither frontend build settings nor public request bodies can select a model. Keep
`OPENAI_API_KEY` as the standard backend secret and `OPENAI_EMBEDDING_MODEL` plus
`EMBEDDING_DIMENSIONS` as independent embedding settings; changing the chat model does not re-embed.

On turn acceptance, persist the resolved model and graph/prompt/configuration versions. A worker
uses those immutable accepted values on recovery, even after a deployment changes the environment
for new turns. Workers must support queued versions during rollout or the queue must be drained;
unavailable model/graph configurations fail explicitly rather than silently adopting a new one.

Configured models must support the selected Responses/structured-output contract. Adapter parameter
profiles omit unsupported optional fields; the example model can use `reasoning.effort=none`.
Local settings checks do not make paid network calls or claim account access/model availability.
An unsupported/unavailable provider model produces a safe typed configuration/provider failure,
not a fallback answer. Explicit live-provider smoke/evaluation verifies compatibility, grounding,
refusals and latency before deploying a changed model.

**Rationale**: Operators can select the chat model without source edits while accepted/recovered
turns remain reproducible and embedding vectors remain in their original vector space.
**Alternatives considered**: A code-level pinned fallback hides missing configuration; one model
setting for both chat and embeddings mixes incompatible roles; per-request model overrides expose
unnecessary runtime/cost choices to users.

**Source**: [ChatOpenAI explicit model configuration](https://docs.langchain.com/oss/python/integrations/chat/openai).

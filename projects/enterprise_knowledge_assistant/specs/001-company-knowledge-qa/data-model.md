# Data Model: Taskify Company Knowledge Q&A

**Date**: 2026-10-20
**Related**: [Specification](spec.md), [plan](plan.md), [contracts](contracts/http.md).

## Ownership and common rules

Identity, Knowledge, and Chat own separate PostgreSQL databases, migration histories, and runtime
roles. References across service boundaries are UUID values validated through interfaces, never
cross-database foreign keys. Within each database use real foreign keys and composite company
constraints to prevent mismatched ownership. All identifiers are UUIDs; timestamps are UTC
`timestamptz`. Text lengths count Unicode code points, not bytes, unless explicitly stated.

Runtime roles are non-owner, non-superuser, without `BYPASSRLS`. Tenant-bearing tables have forced
RLS based on transaction-local trusted company context. Chat's tables also require account context.
Set and clear context on every transaction, including worker claims and pooled connections.
Unscoped worker claim functions have only narrowly granted access to job IDs/leases; subsequent
work is scoped to the stored job owner. Identity's global email lookup and session introspection
use narrow identity-owned repositories/functions, not general unscoped data access. Migration roles
are separate. Test role policies, not merely application WHERE clauses.

## Identity-owned entities

| Entity | Fields | Invariants |
|---|---|---|
| Company | `id`, `name`, `created_at` | Name trimmed, 1–100 characters; first admin and company commit in one transaction |
| Account | `id`, `company_id`, `email`, `normalized_email`, `display_name`, `role`, `password_hash`, `credential_version`, `must_change_password`, `created_at`, `password_changed_at` | Unique normalized email across companies; role exactly `admin` or `user`; company immutable in this scope; password never persisted as plaintext |
| LoginSession | `id`, `account_id`, `token_digest`, `credential_version`, `csrf_secret`, `created_at`, `last_activity_at`, `revoked_at` | Unique digest of a random 256-bit token; 30-minute idle expiry; account role/company resolved from Account; no access except auth/password/logout while initial password change is pending |
| LoginAttemptWindow | `email_key`, `window_started_at`, `failure_count`, `blocked_until` | HMAC of normalized email, including unknown emails; atomic failure accounting; five failures in 15 minutes impose a 15-minute pause; no account-existence disclosure |

`csrf_secret` is server-side random material used for a session-bound synchronizer token. It is
never logged; only its derived/issued CSRF token is returned to the session's browser. Login
passwords are hashed with Argon2id via pwdlib; minimum parameters meet current OWASP guidance and
are configurable/recorded. Verify a dummy hash for unknown emails. Password change locks the account, increments its credential version, revokes all existing account
sessions, and issues one fresh login token in the same transaction. Introspection rejects sessions
whose recorded credential version differs from the account. Login verifies the current credential
version again when inserting a session, so a concurrent old-password verification cannot create a
valid session after the change. Account creation defaults
`must_change_password=true`; only the CLI creates admins. CLI provisioning owns a single Identity
transaction, so invalid/duplicate input cannot orphan a new company.

### Login state transitions

- No session + valid credentials → restricted session when `must_change_password=true`, otherwise
  normal authenticated session.
- Restricted session + valid new password different from the initial password → one fresh normal
  session, incremented credential version, all previous account sessions revoked, and
  `must_change_password=false`.
- Any session + logout → that session revoked.
- A session issued under an older account credential version → invalid even before cleanup.
- `now - last_activity_at >= 30 minutes` → expired; introspection fails even if cleanup has not run.
- Explicit user activity may refresh a valid session. Turn polling, background processing and
  internal validation never refresh inactivity. Logout/expiry never deletes conversation history.

## Knowledge-owned entities

| Entity | Fields | Invariants |
|---|---|---|
| KnowledgeItem | `id`, `company_id`, `title`, `created_by`, `active_revision_id?`, `candidate_revision_id?`, `version`, `created_at`, `updated_at`, `removed_at?` | Title trimmed 1–200 characters; current pointer must reference this item's ready revision; removed items are never readable/searchable; version increments on mutations |
| KnowledgeRevision | `id`, `company_id`, `item_id`, `uploaded_by`, `original_filename`, `media_type`, `size_bytes`, `sha256`, `storage_key`, `state`, `pipeline_version`, `error_code?`, `created_at`, `ready_at?` | Immutable file identity; size 1–20,971,520 bytes; matching supported content/extension; unique private storage key; no more than one candidate processing revision/item |
| ExtractedBlock | `id`, `company_id`, `revision_id`, `ordinal`, `normalized_text`, `locator`, `source_offset_map`, `extractor_version` | Non-empty UTF-8 text; monotonic source ordering; page/section/line/OCR provenance retained; extraction output cannot change the original |
| KnowledgeChunk | `id`, `company_id`, `item_id`, `revision_id`, `block_id`, `ordinal`, `text`, `token_count`, `locator`, `text_sha256`, `pipeline_version`, `embedding_model`, `dimensions`, `embedding` | Non-empty text, at most 800 tokens; no page/section boundary crossing; 100-token overlap where possible; dimensions exactly 1536 for initial model; unique `(revision_id, pipeline_version, ordinal)` |
| IngestionJob | `id`, `company_id`, `revision_id`, `pipeline_version`, `state`, `attempt_count`, `run_after`, `lease_owner?`, `lease_until?`, `lease_version`, `heartbeat_at?`, `last_error_code?`, `created_at` | One logical job/revision/pipeline; worker claims outside long transactions; transient retry limit three; stale lease holders cannot publish |
| PipelineConfiguration | `version`, `normalization_version`, `extractor_versions`, `splitter_name`, `chunk_tokens`, `overlap_tokens`, `embedding_model`, `dimensions`, `tokenizer`, `created_at` | Immutable version; initial values NFC/newline normalization, recursive token splitter, 800/100, text-embedding-3-small, 1536, cl100k_base |

File locators use a discriminated shape:

- PDF: `{kind: "pdf", page: positive integer, text_start?, text_end?}`.
- DOCX: `{kind: "docx", heading_path: string[], block: nonnegative integer, table?, row?, cell?}`.
- TXT: `{kind: "text", line_start: positive integer, line_end: integer >= line_start}`.
- Image: `{kind: "image", page: 1, bbox?: [x, y, width, height]}` in normalized image coordinates.

Locators contain no filesystem paths or arbitrary URLs. Source offsets refer to the normalized
extracted block with a map back to original locations. Embeddings and query vectors must have
the same model/dimensions; reject configuration mismatches. Pipeline upgrades stage a new revision
or complete shadow index and switch only when fully ready; never mix vector spaces silently.

### Knowledge lifecycle and publication

Revision states: `processing` → `ready` or `failed`; an active ready revision becomes `superseded`
when a replacement publishes. A removed item's pending candidate becomes `cancelled`. A newly
accepted revision starts processing with a queued job. Job states are `queued`, `running`,
`succeeded`, `failed`, or `cancelled`; transient failures return to queued with bounded backoff.

Upload order: fully stream and validate a private staged file, then commit item/revision/job in
one Knowledge transaction. A crash before commit may leave an unreferenced file, which reconciliation
cleans; it cannot produce a queryable item. A committed job retries if storage is temporarily
unavailable. Never publish a revision unless its object is present and all validated chunks and
vectors have been committed.

Replacement uses `If-Match` against item version and allows only one processing candidate. It keeps
the active ready revision until completion. Publication locks the item, verifies the current
candidate and lease fencing token, confirms it is not removed, then switches the active pointer,
supersedes the prior revision, and advances version atomically. A title edit does not invalidate
candidate processing; a conflicting title mutation receives a version conflict.

Removal locks the item, advances version, marks `removed_at`, clears active/candidate pointers,
and cancels pending work. Search and original-file access immediately exclude the item. Cleanup
of files/vectors is asynchronous and cannot restore availability. Publication after removal fails.

Retrieval joins KnowledgeChunk to its same-company item and current ready revision inside the
query; RLS supplies an additional boundary. Start with exact cosine distance and B-tree company/
revision indexes. Global top-k followed by tenant filtering is forbidden. Retrieval results include
chunk ID, item/revision IDs, current title, source locator, similarity, and text only for current
ready content. Batch source validation uses one authoritative snapshot and reports only authorized
current citations. This snapshot is the final answer-release consistency checkpoint. Its validation result is
single-use within the current fenced terminal-commit attempt; a reclaimed or expired worker must
revalidate rather than reuse old availability decisions.
Changes after that snapshot may precede Chat's terminal commit or browser display without invalidating
the validated answer; they immediately affect subsequent retrieval and source opens.

## Chat-owned entities

| Entity | Fields | Invariants |
|---|---|---|
| Conversation | `id`, `company_id`, `account_id`, `last_sequence`, `created_at`, `updated_at` | Unique `(company_id, account_id)` and unique account ID; lazy atomic creation; persists across login sessions; account/company cannot change |
| ChatMessage | `id`, `company_id`, `account_id`, `conversation_id`, `turn_id`, `sequence`, `sender`, `content`, `outcome?`, `refusal_text?`, `created_at` | Unique `(conversation_id, sequence)`; sender `user` or `assistant`; accepted user text 1–4000 characters trimmed; assistant has exactly one terminal outcome |
| ChatTurn | `id`, `company_id`, `account_id`, `conversation_id`, `client_message_id`, `user_message_id`, `assistant_message_id?`, `accepted_login_session_id`, `state`, `attempt_count`, `lease_until?`, `lease_version`, `created_at`, `completed_at?`, `error_code?`, `ai_mode`, `model`, `graph_version`, `prompt_version`, `model_config_version`, `retrieval_config_version?` | Unique `(conversation_id, client_message_id)`; one queued/running turn per conversation; retry payload must match original content; one assistant terminal result/turn; accepted AI mode/model/graph/prompt/model-config versions are immutable; retrieval version is nullable terminal-attempt metadata, not an acceptance-time setting |
| Citation | `id`, `company_id`, `account_id`, `assistant_message_id`, `item_id`, `revision_id`, `chunk_id`, `locator`, `title_at_answer`, `validated_at` | Only retrieved/verified evidence IDs; belongs to the same conversation/company; no model-supplied URL; resolved through Knowledge at source open |

Conversation and message account context always comes from the authenticated identity or the
stored worker turn, never request JSON. Unique constraints resolve simultaneous first opens and
submissions across tabs. `expected_last_sequence` prevents a second tab from silently submitting
against a changed conversational context. A client retry with the same message UUID and identical
content returns its existing turn even when the expected sequence is now old; mismatched content
returns conflict.

### Graph execution state and configuration

LangGraph state is transient within one turn attempt. Do not create graph checkpoint, thread,
store, cache or additional conversation tables in this feature. The unique Conversation and its
ChatMessages remain the only conversation/history authority. LangGraph is an adapter implementation
of the application-owned TurnWorkflow port; its state/type definitions never become core entities.

A fresh attempt carries the current user message, at most 6,000 tokens of authorized own history,
scope decision, standalone query, retrieved evidence, candidate claims/citations, verification
outcome and the existing overall deadline. Actor/account/company/session IDs, lease fencing,
and accepted model/graph/prompt configuration are supplied through immutable trusted runtime
context, not model-editable state. Reject model updates to those values. Do not place API keys,
raw login/CSRF tokens or framework runtime objects into persisted turn metadata or graph state.

Read `OPEN_AI_MODEL` at the Chat composition root and snapshot its resolved value into ChatTurn.model
when accepting a new turn. Snapshot AI mode and graph/prompt/parameter-profile versions as well.
Missing/blank or malformed configuration fails readiness in OpenAI mode; there is no model default
in code. Stub mode records its deterministic fixture model/configuration. On deployment changes,
new turns use the new environment while an existing turn retains its accepted configuration.
Workers need compatible version handlers or a drained queue; they cannot switch models or modes
silently. Embedding pipeline/model metadata remains independent of this chat configuration.
`retrieval_config_version` is null on queued/running turns. Each attempt needing evidence retrieves
using Knowledge's active configuration, which may differ after recovery. Keep the returned version in ephemeral attempt
state; the fenced terminal transaction stores that attempt's successful-search version with its
assistant result, or null if no search succeeded. Recovery discards uncommitted retrieval metadata.
The terminal value is immutable with the terminal result. No acceptance-time Knowledge call or
retrieval-version selector is required. This separation preserves fixed answer-model settings while
using fresh current evidence and active retrieval settings on every attempt.

### Chat lifecycle and outcomes

`PUT /chat` returns or creates the unique conversation. New-message acceptance locks the
conversation, verifies ownership and expected sequence, inserts the user message and queued turn,
and advances the sequence in one transaction. A duplicate idempotency key is resolved before
checking sequence or active-turn state.

Turn transitions: `queued` → `running` → `completed` or `failed`. An abandoned running lease may
be reclaimed; fencing prevents the old worker writing a terminal response. Validate the accepting
login before supplying history to the provider. On every attempt, construct a new LangGraph state
and start at its first node; no intermediate checkpoint is resumed. Reload authorized own history,
re-retrieve evidence, and use the accepted model/mode/graph/prompt configuration. Provider calls
may repeat after a crash, but only one terminal assistant message can be committed. The graph
returns an uncommitted candidate; the application performs fresh final login/source validation
and the fenced terminal transaction outside the graph. Failed provider calls
can retry once inside the 20-second attempt deadline; exhausted/revoked/stale-source outcomes
are terminal failures with an assistant failure message. A manual user retry is a new turn;
replayed HTTP submission of the same UUID never invokes the provider again after completion.

Terminal assistant outcomes: `answer`, `refusal`, `insufficient_information`, `clarification`,
`failure`. Mixed requests use `answer` plus non-empty `refusal_text`; the answer portion has
citations. A pure refusal/clarification/failure has no fabricated citations. Conflicting sources
use an answer identifying the conflict with each supporting reference. Operational failures never
masquerade as insufficiency. Cited IDs must be retrieved and verified against the final source
snapshot; unsupported claims cause verification failure and a retryable operational message.

History is immutable after release; title changes and source availability are resolved using
Knowledge when histories are loaded. A removed/superseded source is rendered as unavailable, with
no link to a replacement at an old locator. Historical text remains visible only to its owner and
cannot act as evidence for a new factual answer. A knowledge/identity outage prevents new answer
release. If metadata hydration is unavailable, history may show saved citation labels as
unavailable rather than invent active links.

Full ordered history is persisted and cursor-paginated. Only at most 6,000 recent history tokens
are supplied for follow-up resolution. Distant/ambiguous references prompt clarification. No
per-user chat reset, deletion, sharing, or multiple-chat creation exists in this feature.
Build the context from the newest complete prior messages that fit within 6,000 tokens, preserving
order and excluding the current question from this budget. A topic only in omitted messages requires
clarification. Test within/exactly-at/beyond-limit histories without deleting persisted messages.

## Validation and consistency matrix

| Input/invariant | Rule | Enforcement |
|---|---|---|
| Company/display names | Trim; 1–100 code points; reject control characters | HTTP/CLI adapter + application value object |
| Email | Valid address syntax, at most 254 characters; case-insensitive uniqueness | Adapter + normalized unique index; reject duplicates generically |
| Password | 12–128 code points; no trimming/truncation; new password differs on first change | Identity adapter/use case + password adapter |
| Title | Trim; 1–200 code points; reject control characters | Knowledge adapter/value object |
| User message | Trim; 1–4000 code points | Chat adapter/value object; internal worker revalidation |
| Filename/file | 1–255 characters, no separators/control characters; 1–20,971,520 bytes inclusive; allowlisted MIME and matching extension/content | Stream counter, parser and signature/format checks |
| UUIDs/version/sequence | Valid UUID; positive item version; sequence integer >= 0 | All public/internal adapters; ownership lookup and CAS |
| Pagination | `limit` 1–100, default 50; opaque bounded cursor <= 512 characters, scoped to query/owner | Adapter + repository cursor decoder |
| Source evidence | Current same-company ready revision; cited chunk belongs to item/revision | Retrieval predicate + final validation + authorized source endpoint |
| Chat ownership | Exactly one conversation/account, never visible to another account | Unique constraints + application authorization + forced RLS |
| Jobs and retries | Lease/fencing and logical unique keys; transient-only bounded retries | Claim transaction + application state machine + terminal CAS |

No automatic content expiry or company/account deletion is introduced. Storage and backup retention
is an operational setting; introducing a product retention/deletion policy requires an explicit
spec change. Raw company documents and chat are not emitted to logs or third-party tracing.

# Internal Service and Worker Contracts

**Version**: 1.0.0 | **Format**: JSON over authenticated service-to-service HTTP.
All routes below are internal-only, excluded from ingress and the public OpenAPI. Identity and
Knowledge publish provider/consumer tests for these schemas. Additive optional fields are compatible;
breaking fields/semantics require `/internal/v2` and a consumer migration. No direct database or
filesystem access crosses service boundaries.

## Trust and errors

Use caller-specific bearer credentials over TLS, with separately granted scopes and rotation.
Loopback Compose may use its isolated nonpublic network; production must encrypt service traffic.
Credentials authenticate the service; user authority is resolved from Identity and cannot come
from `X-Company-ID`, `X-Role`, request JSON company IDs, or model output. Ingress strips such headers.
Never log internal request bodies containing login tokens, CSRF material, text, or evidence.

Each request carries `X-Request-ID: UUID`; generate one if absent at the public edge. Reject unknown
fields and malformed identifiers before execution. Errors use the public safe Error shape.
Invalid service credentials: 401; disallowed scope: 403; invalid user session: 401; invalid schema:
422; missing/unauthorized resource: indistinguishable 404; dependency unavailable: 503. Callers use
bounded timeouts, no positive session-validation cache, and fail closed. Internal requests cannot
refresh a login unless an authenticated public handler explicitly records real user activity.

## Identity: resolve a login

`POST /internal/v1/sessions/resolve`

Allowed callers: Knowledge and Chat API/worker credentials with `identity:resolve` scope.

Request:

| Field | Type/rule |
|---|---|
| `session_token` | Optional secret string, exactly the browser cookie token; mutually exclusive with login_session_id |
| `login_session_id` | Optional UUID; background/worker calls only; not a browser authentication alternative |
| `csrf_token` | Optional bounded string, required when require_csrf=true |
| `require_csrf` | Boolean set by the receiving handler's policy, never forwarded from browser JSON |
| `require_password_changed` | Boolean; true for all Knowledge/Chat operations |
| `activity` | `user_activity`, `poll`, or `background`; fixed by handler, not browser-controlled |

Exactly one session selector is required. Browser-facing service handlers forward the cookie token.
Workers use the accepted session ID recorded in their durable turn. Credentials used for workers
are constrained to `activity=background`; they cannot revive sessions, change passwords, or create
accounts. Identity resolves Account itself and evaluates revocation, credential-version match, idle timeout, password-change
state and, when requested, CSRF. An expired session is never extended by this operation.

200 response: `{login_session_id, account_id, company_id, role, must_change_password,
idle_expires_at, csrf_valid}`. IDs are UUIDs; role is admin/user; `csrf_valid` is true only after
validation, or null if no CSRF check was requested. Never return cookie token, password hash,
csrf_secret, or another account's details. Invalid CSRF returns 403 rather than a usable identity
for a mutating operation. Password-change-required access returns 403 for Knowledge/Chat.

Public handlers may refresh inactivity after successful explicit user activity. Polling and
background validation never do. Identity's own authentication handlers use the same application
policy without making HTTP calls to themselves.

## Knowledge: retrieve current evidence

`POST /internal/v1/retrieval/search`

Allowed caller: Chat answer worker with `knowledge:retrieve` scope. Request:
`{login_session_id: UUID, query: string[1..4000], request_id: UUID}`. Query is a bounded standalone
company-information question, resolved from the same chat's recent context. A long rewrite is
rejected rather than silently truncated. Company/account/role are not accepted as authority.

Knowledge resolves the session with Identity (`activity=background`), embeds the query using the
active pipeline configuration, and performs exact cosine search within the authenticated company
and current-ready revisions. No caching crosses company/model/pipeline boundaries. Default maximum
20 candidates is server-owned; the chat pipeline deduplicates to eight evidence chunks.

200 response: `{pipeline_version, retrieval_config_version, candidates: Evidence[]}`.
Both version values describe the active Knowledge configuration used for this search, including an
empty candidate result. They are nonempty version identifiers. The request has no version selector:
every recovered attempt reaching retrieval searches again using the then-active configuration and current sources.
Chat holds the returned retrieval version in ephemeral attempt state and writes it only with the
fenced terminal result; pending turns and terminal attempts with no successful search use null.
Evidence contains `{chunk_id, item_id, revision_id, title, text, locator, similarity}`. Each ID is a
UUID, text is nonempty and bounded by chunk limits, similarity is a finite number, and locator has
the public Locator shape. An empty array means no ready matching evidence, not an outage. Provider
embedding errors, model/dimension mismatch and database failures return 503 with safe error codes.

Knowledge revalidates forwarded query and session data before embedding. The model cannot call
this endpoint directly or choose a company filter. Query text cannot become SQL, an arbitrary
fetch URL, or instructions to the provider that override the pipeline policy.

## Knowledge: validate and resolve citations

`POST /internal/v1/sources/validate`

Allowed caller: Chat API/worker with `knowledge:validate_sources` scope.
Request: `{login_session_id: UUID, citations: [{item_id, revision_id, chunk_id}], purpose}`,
where purpose is `release` or `history`; max 100 unique triples, UUID fields, no unknown keys.
A release request has at most eight evidence chunks. The API may batch history hydration.

Knowledge validates the session without touching inactivity and checks all triples in one
transactional snapshot for the authenticated company, ready/current revision, item availability,
and chunk membership. It constructs locators and paths from owned records, not caller strings.

200 response: `{validated_at: ISO8601 UTC, all_current: boolean, sources: SourceStatus[]}`.
Each status contains `{item_id, revision_id, chunk_id, availability, label, locator?, resource_url?}`.
For current authorized content, availability is `current` and a server-built relative URL opens the
exact revision, e.g. `/api/v1/knowledge/{item}/source?revision_id={revision}#page=3` for a PDF page.
Other triples return `unavailable`, no private label, and null locator/URL. Do not distinguish
foreign-company, unknown, removed, superseded, or fabricated chunk IDs to the caller.

For `purpose=release`, all_current=false blocks the entire factual draft; the worker records a
retryable `information_changed` failure or `verification_failed` for fabricated evidence. The
atomic snapshot is the final response-release consistency checkpoint. The result is single-use
within a fenced terminal commit; a reclaimed worker or expired lease must validate again. Source changes after that
checkpoint, including before Chat's terminal commit or browser display, do not invalidate that
validated answer. They affect subsequent retrieval, hydrated links and source opens immediately.
A source request always verifies again.
Knowledge or Identity unavailability produces 503, not all_current=false; a failure is never
misreported as a genuine absence of company knowledge.

For `purpose=history`, Chat hydrates stored citations with current titles/availability. Old text
stays in the owning account's history; unavailable sources are marked and not relinked to new
revisions. Chat can retain its owner's historical label when hydration is unavailable, with no
active link. No endpoint exposes another account's conversation to Knowledge.

## Provider adapter contracts

These are application-owned Python protocols, not shared runtime models or public endpoints.

| Owner/port | Input/output | Failures and invariants |
|---|---|---|
| Knowledge `TextExtractor` | Validated immutable file reference → ordered extracted blocks with locators | Unsupported/corrupt/unreadable/resource-limit failures; no network fetches or file-path traversal |
| Knowledge `Chunker` | Extracted blocks + pipeline version → nonempty <=800-token chunks | Page/section boundaries and source-offset mapping preserved |
| Knowledge `Embedder` | Nonempty bounded texts + model/dimensions → finite vectors in input order | Timeout, provider unavailable, malformed vector/dimension; no partial publication |
| Knowledge `VectorSearch` | Trusted company context + query vector/config → current-ready evidence | Applies tenant/current revision before ranking; no global results returned for later filtering |
| Chat `TurnWorkflow` | Validated message, bounded authorized own history, immutable actor/configuration context → uncommitted candidate | LangGraph adapter; finite branches; no checkpoint/store/tool loop; cannot authorize release or write messages |
| Chat `Answerer` | Role-specific scope, generation or verification input plus allowed evidence → typed structured model result | LangChain/OpenAI adapter; model captured from OPEN_AI_MODEL; no tools/arbitrary URLs; failures explicit |
| Chat `KnowledgeGateway` | Login-session reference, bounded query or citation triples → typed evidence/status | HTTP adapter revalidates DTOs; dependency outage differs from empty evidence |
| Each `SessionValidator` | Current browser token or accepted internal session reference → trusted principal | Fail closed; no implicit company selection or silent expired-session refresh |

LangChain output schemas contain `intent` (company_information, unrelated, action_request, mixed,
ambiguous), a bounded standalone question or null, and any refused-part description. The answer
schema contains `outcome`, `claims[{text,evidence_ids}]`, optional company-scoped clarification,
optional refusal_text, and conflict flags. Reject schema violations, unknown evidence IDs, external
links and unsupported claims. The application renders citations and safe message text. Provider
safety refusals/incomplete structured responses are explicitly handled rather than parsed as facts.

## Graph and model-configuration contract

LangGraph StateGraph implements explicit routes from scope resolution to refusal, clarification,
or company retrieval; retrieval routes to insufficiency or generation/verification. Failed
grounding becomes a safe failure candidate. There are no back edges, autonomous regeneration,
ToolNode, create_agent or Deep Agents harness. Compile without a checkpointer, store or result
cache. Limit a graph attempt to 12 steps and the existing shared 20-second attempt deadline.
Scope classification and structured output do not confer authority: injected application ports
and policy code control retrieval, and immutable actor context cannot be changed by model output.

Validate the accepting login before graph invocation, and use newly loaded own history/evidence.
Every graph return is only a candidate. The application performs the final login and current-source
checks, constructs server-owned links, and commits under its SQL lease fence after the graph.
Recovered attempts restart from the first node with fresh evidence and cannot reuse an earlier
candidate, graph state, source-validation receipt, or another account's context. No graph node
writes ChatMessage/Citation records. Whole-turn recovery can repeat provider calls/cost, while
terminal persistence stays idempotent. No node-level durable-resume guarantee is made.

`OPEN_AI_MODEL` is an application-owned runtime setting, explicitly mapped to ChatOpenAI.model.
It is required in AI_MODE=openai; missing, blank, whitespace/control-containing or >200-character
values fail local configuration/readiness checks before new work is accepted. No legacy alias or
hard-coded model fallback is allowed. Compose forwards the setting to Chat API and Chat worker;
frontend and public request bodies cannot choose it. OPENAI_API_KEY remains backend-only.

Persist accepted AI mode, model, graph_version, prompt_version and model_config_version on the turn.
All LLM roles use that model/profile, including grounding verification. Retries/recovery use the
accepted snapshot, not a newly changed environment value. A rollout must retain handlers for queued
versions or drain old work. The profile must support the Responses/structured-output contract and
omit unsupported optional parameters; incompatible/unavailable configurations fail explicitly.
This snapshot does not pin Knowledge retrieval configuration. `retrieval_config_version` is nullable
terminal-attempt audit metadata as defined by the search response above; changing it on recovery does
not change the accepted AI mode/model/graph/prompt/model-profile settings.
Do not make a paid availability call during ordinary readiness checks. OPENAI_EMBEDDING_MODEL and
EMBEDDING_DIMENSIONS remain Knowledge-owned independent settings and are not derived from OPEN_AI_MODEL.

## Durable worker contracts

Workers read only their own service's queue through owned repositories. These are not broker events.
Every job record and recovered lease is validated before processing. A claim increments
`lease_version`; writes must match the latest lease version. Commit claims and heartbeat updates
in short transactions; never hold row locks across OCR or provider requests.

- Ingestion job identity: `{job_id, company_id, revision_id, pipeline_version}`. Lease 120 seconds,
  heartbeat at most every 10 seconds; recover expired work. A successful extraction/embedding commit
  is idempotent by `(revision_id,pipeline_version,chunk_ordinal)`. Retry transient failures at most
  three times with jitter/backoff. Permanent parser/format/validation failures become failed.
  Publication requires the current candidate, valid lease, and an item not removed.
- Chat turn identity: `{turn_id, company_id, account_id, conversation_id, accepted_login_session_id}`
  plus accepted `{ai_mode, model, graph_version, prompt_version, model_config_version}` from the
  Chat-owned record, never caller-selected model settings.
  Lease 30 seconds, heartbeat at most every 5 seconds, 20-second attempt deadline. Allow at most one
  transient provider retry within that shared deadline, with SDK automatic retries disabled to
  avoid multiplied attempts. LangGraph node retry policies must not add attempts outside this budget. Expired worker leases are recovered; one terminal assistant message
  per turn is enforced by a unique constraint and fencing. Bound recovery to three claims before
  a terminal retryable failure. Queue claim concurrency initially supports 20 simultaneous turns.

Raw tokens, passwords and provider API keys never appear in job payloads. Jobs carry IDs, not a
claimed role/company from browser JSON. No cross-service database worker polls another service's
queue. Chat cannot cause knowledge changes or identity administration.

## Operational endpoints and readiness

Each service exposes `/health/live` (process liveness) and `/health/ready` (required owned storage
and service configuration readiness) on its nonpublic service port. Worker readiness includes its
queue access; parser/OCR dependencies are checked at startup. An OpenAI connectivity probe is an
explicit operator check, not a billable call on every health request. Metrics are nonpublic and
redact content/credentials. Internal versioned contracts support independent consumer/provider
releases; schema compatibility and integration checks precede deployment.

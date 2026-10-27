# Public HTTP Contract

**Version**: 1.0.0 | **Base path**: `/api/v1`
**Machine-readable contract**: [openapi.json](openapi.json)
**Owner data rules**: [data-model.md](../data-model.md)

## Common rules

Same-origin HTTPS outside loopback. The ingress routes auth/users to Identity, knowledge to
Knowledge, and chat to Chat; it never publishes `/internal`. Public requests contain no trusted
company or account selector. Each service validates Identity and enforces its own ownership rules.
Exactly two application roles exist. Admin content/account management is outside the chatbot.

Production authentication uses the `__Host-taskify_session` HttpOnly/Secure/SameSite=Lax cookie,
Path=/, no Domain. Development uses `taskify_session` on loopback with Secure disabled. The
Identity service returns a session-bound `csrf_token`; clients keep it in memory and use
`X-CSRF-Token` for all authenticated mutations. Every browser mutation requires the exact configured
Origin, including login. Login requires JSON content type and rejects form or cross-origin login.
`GET /auth/session` recovers authenticated browser state and its CSRF token after reload.
Password change increments the account credential version, revokes all previous sessions, and
issues one fresh session atomically. Session creation checks that version at commit to reject
concurrent authentication using an obsolete password.

Authentication introspection on protected routes is online and fail-closed. A first-login session
requiring password change is restricted to auth/session, auth/password, and auth/logout. Browser
turn polling does not count as user activity; deliberate reads/submissions may refresh idle time.
All responses containing company/account/chat information use `Cache-Control: no-store`.

JSON mutations reject unknown fields. UUID, text, password, file and pagination limits match FR-016
and the data-model validation matrix. An empty JSON object is the only body accepted by `PUT /chat`.
No HTTP endpoint creates admins, changes company membership, or exposes someone else's chat.
Files have an inclusive size range of 1–20,971,520 bytes; a one-byte readable TXT is valid input,
subject to the other file rules. Zero-byte and 20,971,521-byte files fail size validation.

Errors use `{code, message, request_id, details}`. Details are field-level corrective data, never
secrets, parser stack traces, account ownership, private file paths, or provider payloads.

| Status | Codes and semantics |
|---|---|
| 400 | `invalid_request`: bad syntax/cursor/unknown fields |
| 401 | `authentication_required`: missing, expired or revoked login; `invalid_credentials` on login |
| 403 | `forbidden`, `csrf_failed`, `password_change_required`: own-role restriction; no cross-company details |
| 404 | `not_found`: unknown or unauthorized resource; identical shape for other-company objects/chats |
| 409 | `version_conflict`, `turn_in_progress`, `conversation_changed`, `idempotency_conflict`, `replacement_in_progress`, `account_unavailable` |
| 410 | `source_unavailable`: an authenticated same-company historical source was removed/superseded; no replacement silently substituted |
| 413 | `file_too_large` |
| 415 | `unsupported_file_type` |
| 422 | `validation_failed`: invalid fields, corrupt upload, unsupported text encoding or format mismatch |
| 429 | `login_temporarily_unavailable`; generic unknown/known email handling; `Retry-After` seconds |
| 503 | `dependency_unavailable`: authentication/storage unavailable before acceptance; never a fabricated answer |

Malformed requests have no domain changes. A processing failure after a durable upload/turn has
been accepted is represented in that resource's state rather than pretending acceptance failed.
HTTP error bodies use a documented safe message and correlation ID. No provider exception is
forwarded. Pagination defaults to 50 and allows 1–100 records; opaque cursors are owner-scoped and
at most 512 characters. Each response includes a next cursor or null.

## Endpoints

| Method and path | Service/role | Input | Success |
|---|---|---|---|
| POST `/auth/login` | Identity/public | `{email,password}`; Origin | 200 Session; sets rotated session cookie; 401 generic failure or 429 pause |
| GET `/auth/session` | Identity/own authenticated session | Cookie | 200 Session including first-password-change state and CSRF token |
| PUT `/auth/password` | Identity/own session including restricted login | `{current_password,new_password}`; CSRF | 200 fresh Session; all previous account sessions revoked; invalid/current-equal password rejected |
| POST `/auth/logout` | Identity/own session including restricted login | No body; CSRF | 204; revokes session and expires cookie; saved chat unchanged |
| POST `/users` | Identity/admin | `{display_name,email,initial_password}`; CSRF | 201 user-role Account in caller's company; duplicate email generic 409 |
| GET `/knowledge` | Knowledge/admin or user | `limit,cursor`; no company selector | 200 ItemPage; user sees ready items only, admin sees all nonremoved statuses |
| POST `/knowledge` | Knowledge/admin | Multipart `title,file`; CSRF | 202 processing KnowledgeItem with ETag and job already durable |
| GET `/knowledge/{item_id}` | Knowledge/admin or user | UUID | 200 KnowledgeItem and ETag; users only if ready |
| PATCH `/knowledge/{item_id}` | Knowledge/admin | `{title}`; `If-Match`; CSRF | 200 KnowledgeItem with new ETag |
| POST `/knowledge/{item_id}/revisions` | Knowledge/admin | Multipart `file`; `If-Match`; CSRF | 202 KnowledgeItem with active ready revision retained and candidate visible |
| GET `/knowledge/{item_id}/revisions/{revision_id}` | Knowledge/admin | UUIDs | 200 Revision processing/ready/failed/superseded/cancelled outcome; only within company |
| DELETE `/knowledge/{item_id}` | Knowledge/admin | `If-Match`; CSRF | 204; immediately excludes reads/retrieval and cancels pending candidate |
| GET `/knowledge/{item_id}/source` | Knowledge/admin or user | Required `revision_id`; optional `download=false` | 200 authorized current original bytes; 410 for unavailable own historical source |
| PUT `/chat` | Chat/own admin or user account | `{}`; CSRF | 200 existing or newly created unique Conversation |
| GET `/chat` | Chat/own account | No selector | 200 own Conversation; 404 before initial creation |
| GET `/chat/messages` | Chat/own account | `limit,cursor` | 200 ordered MessagePage; newest page by default, older page via cursor |
| POST `/chat/messages` | Chat/own account | `{client_message_id,content,expected_last_sequence}`; CSRF | 202 queued or running Turn; 200 already terminal identical replay |
| GET `/chat/turns/{turn_id}` | Chat/own account | UUID | 200 Turn with processing or terminal result; 404 for any other account's turn |

Item ETags are quoted positive decimal versions, e.g. `"3"`. Missing `If-Match` on a required
mutation is 422; a stale value is 409. Responses with an updated item include its new version/ETag.
DELETE confirmation occurs in the UI before submission. Two admins cannot silently overwrite each
other. A failed replacement leaves the ready revision available and exposes a safe failure reason.

Sources are streamed through Knowledge; no permanent public file URL or private storage key leaves
that service. Files with browser-active content are downloaded safely, using validated media types,
Content-Disposition and `X-Content-Type-Options: nosniff`. PDF/image preview is allowed; DOCX/TXT may
be downloaded when an inline viewer is unavailable. Locator labels still identify supporting
pages/sections/lines/images. Opening a source revalidates login, company, item and exact revision.

## Chat semantics

Initial `PUT /chat` is idempotent, including concurrent opens. There is no arbitrary chat-ID
parameter for history or sending and no list-other-chats capability. `expected_last_sequence` must
match the current conversation sequence for a new message. The client checks an existing
`client_message_id` before version validation; an identical network replay returns the same turn,
while a changed payload gives `idempotency_conflict`. A different message while a turn is queued or
running returns `turn_in_progress` without creating a message.

202 means the user message and turn were committed, not that an answer exists. Poll the returned
`poll_url` every second, without refreshing login idle time. A turn contains its accepted user
message and `assistant_message=null` until terminal. A terminal turn is completed or failed and
contains one saved assistant outcome. Network retry reuses the original UUID; deliberate retry
after a terminal failure sends a new UUID and message. Browser reload discovers the active turn
from the Conversation and resumes polling. Worker restarts cannot duplicate a terminal response.

| Assistant outcome | Display and citations |
|---|---|
| `answer` | Supported company answer with at least one authorized citation; `refusal_text` explains any declined mixed-request part |
| `refusal` | Brief company-information-only explanation; no unrelated answer/action and no invented citations |
| `insufficient_information` | Company-related question cannot be answered from ready company evidence; no fabricated facts |
| `clarification` | Ask for the missing/ambiguous company topic; no invented interpretation |
| `failure` | Safe retryable operational/authentication/source-change/verification failure; no partial factual answer |

Every factual claim must be supported by evidence. Generation returns supplied evidence identifiers;
Taskify verifies membership, current revision and factual grounding and constructs resource links.
Model-proposed URLs or arbitrary Markdown HTML never become trusted links. Citation DTOs include
`item_id`, `revision_id`, `chunk_id`, locator, current label, `availability`, and `resource_url`.
For historical removed/superseded resources, availability is unavailable and resource_url is null.
The saved answer text is not rewritten. Dependency failure during history hydration renders source
links unavailable until refreshed, without leaking another company's data.

A final login check and atomic batch source validation gate response release. Invalid/stale evidence
never appears as a streamed draft. Validation results are single-use in the current fenced commit;
recovered workers must revalidate. Final source validation is the consistency checkpoint; changes
afterward, including before terminal commit or browser display, do not invalidate the validated
answer but apply to future answers, hydrated links and source opens. If the accepting login expires during processing,
record an authentication-required terminal outcome; viewing it still requires a valid new login.

## Compatibility and examples

All public interfaces are `/api/v1`. Additive optional fields require consumer tolerance and
contract tests; required-field changes, removals, enum reinterpretation or permission changes
require a new major path or an explicit compatible migration with both consumers supported.
Generated TypeScript transport types remain outbound-adapter DTOs, never frontend domain types.

Example accepted message:

```json
{
  "client_message_id": "64a0ce52-5b6d-4c12-bc38-a5e5fa2a542c",
  "content": "What exceptions apply to that policy?",
  "expected_last_sequence": 2
}
```

Example safe refusal message content: “I can only answer questions using your company's information.
I cannot send messages or make changes.” Source references are empty. The same policy applies to
admins; they may use separate administrative screens to perform authorized management actions.

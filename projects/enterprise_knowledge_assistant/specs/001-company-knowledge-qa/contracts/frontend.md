# Frontend Interaction and Boundary Contract

**Stack**: React 19, TypeScript strict mode, Vite. Domain/application modules are framework-free.
**Transport source**: [openapi.json](openapi.json); adapter DTOs are decoded before mapping to
frontend domain types. Presentation labels do not expose embeddings, service names, prompts, or
provider internals unless an actual user action depends on that information.

## Application ports

| Port | Core operations |
|---|---|
| AuthPort | login(email,password), getSession(), changeInitialPassword(current,new), logout() |
| ChatPort | openOwnConversation(), loadOwnHistory(cursor,limit), send(content,clientId,expectedSequence), getOwnTurn(turnId) |
| KnowledgePort | list(cursor,limit), readItem(id), openSource(citation), upload(title,file), rename(id,title,version), replace(id,file,version), remove(id,version) |
| UsersPort | createUser(displayName,email,initialPassword) |
| Clock / IdGenerator | Deterministic time and UUIDs for polling/submission; browser adapters implement them |

Ports use domain IDs, results and typed errors, not Response, JSX, framework hooks or provider DTOs.
A binary attachment value is defined by an application-owned file abstraction; browser File is
wrapped by its adapter. React controls route lifecycle and calls use cases. Fetch, cookies, timers,
file APIs and routing implementations stay in adapters/composition. Imports are checked in CI.

## Source import convention

Use `@/` for all imports targeting `frontend/src`, including imports from frontend tests; for
example, `import type { ChatPort } from '@/application/ports/chat'`. The alias maps to that source
root consistently in TypeScript, Vite, Vitest, Playwright and ESLint. Static/type-only imports,
re-exports, literal dynamic imports and imported assets follow the same convention. Lint rejects
relative references into or within the source tree, including same-directory references. Bare
third-party package names and relative tooling/test-helper imports outside `src` remain valid.
Dependency rules apply to resolved targets: an alias never permits domain/application code to
import React, browser globals or transport/infrastructure adapters. See FR-023 and its acceptance
cases for valid resolution and rejected relative/boundary-violating examples.

## Routes and access

| Route | Actor and user-visible behavior |
|---|---|
| `/login` | Email/password form with validation and generic login/pause errors; no signup or external-login buttons |
| `/change-password` | Mandatory first-login password change before entering protected views |
| `/chat` | Own single saved conversation, message history, composer, linked sources and pending/terminal outcomes |
| `/knowledge` | Current company ready resources; view/download available to users and admins |
| `/admin/knowledge` | Admin upload/status/title edit/replace/remove; removal requires explicit confirmation |
| `/admin/users/new` | Admin creates a user-role account in the current company; no company/role override |

Protected navigation checks session and password-change state. The server remains authoritative
when requests are made outside the UI. Admin navigation does not reveal other users' chats.
There is no new-chat, chat-sharing, other-account history, chat reset, or chat deletion control.

## Chat interaction

On entry, initialize/reuse the one conversation through PUT /chat, load its latest message page,
and resume a saved active turn if present. Display chronological messages and an accessible
load-earlier control. A new account starts empty with an explanation of company-information scope.
Older pages are owner-scoped; no other account's data remains in caches after account change.
Saved history is distinct from the chatbot's at-most-6,000-token recent-context window. If a topic
only appears outside that window, show the clarification asking the user to restate it; older
messages remain readable and no reset or deletion is needed.

The composer accepts 1–4,000 characters after trimming and displays corrective validation. Generate
a client UUID for a deliberate send and preserve it while retrying a lost network response. Disable
new sends while the accepted turn is queued/running. Poll every second while the page is active;
network errors keep the pending turn identity for reconnection instead of inventing an answer.
After a version/conversation conflict, refresh history and ask the user to resend deliberately.

Render final outcomes distinctly:

- Answer: company-supported text with per-claim source links/labels and a separate refused-part
  explanation for mixed requests. Each link identifies the actual file and location.
- Refusal: brief explanation of company-information-only scope, without unrelated content/actions.
- Insufficient information: available company material cannot answer the company-related question.
- Clarification: ask which company topic the user means, retaining the ongoing conversation.
- Failure: safe explanation and explicit retry; a deliberate retry is a new turn/UUID.

Do not display draft factual tokens before verification. Render plain text or a restricted safe
Markdown subset; disable raw HTML and model-supplied external links. Build resource links only from
validated Citation DTOs, constrain them to the same-origin source route, and use current availability.
Unavailable historical citations show a clear label with no active link. A source-open 401 returns
to login; a 410 explains that the resource changed or was removed without substituting a new file.

Logout clears in-memory account/query/chat data and CSRF state, revokes the login cookie, and returns
to login. The server keeps conversation history. Session expiry pauses protected actions and asks
for login; after reauthentication restore the same account's conversation. An account switch must
never display the prior account's messages, even briefly.

## Admin and source workflows

Upload/replace show processing, ready, or failed outcomes with actionable file errors. A previous
ready revision remains usable while a replacement processes or fails. Editing uses the latest ETag;
conflicts require reload instead of silent overwrite. Removal first asks for confirmation and then
updates the list immediately after the server acknowledges. Failed/rejected changes do not optimistically
remove valid information. Users receive no editing controls; attempted unauthorized requests still fail.

User creation validates name/email/password, never offers an admin role selector, and shows a generic
duplicate-email error. An admin shares initial credentials through an existing trusted channel.
Do not retain the initial password after success or echo it in notification text.

## Accessibility and verification

All controls have labels, keyboard focus states and keyboard access. Announce processing/completion
and validation errors through suitable live regions; distinguish outcomes using text, not color
alone. Mobile layouts retain source links and the composer without horizontal page scrolling.

Component tests cover port success/errors and validation; browser tests cover login, initial password
change, persistence across reload/login, two-account cache isolation, refs/refusals, upload/status,
replacement failure, conflicts, and admin/user route restrictions. Unit tests run the same application
use cases using port doubles without a browser, React tree or network provider.

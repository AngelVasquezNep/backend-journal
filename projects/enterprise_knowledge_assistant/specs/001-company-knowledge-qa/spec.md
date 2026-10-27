# Feature Specification: Taskify Company Knowledge Q&A

**Feature Branch**: No feature branch created; branch creation hook is not configured.

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Develop Taskify, a Q&A platform where different owners/companies load information (documents, images, etc.) and users can query about it. Owners (company admins) can edit this info. Clients (By compnay) can read it. There are two roles (admin, users), Admins are created by CLI command and admins can create users. Login system is required."

## Clarifications

### Session 2026-10-20

- User clarification: Taskify is a chatbot with each account's own chat session and conversational context. It answers only from company knowledge, links the resources used, and refuses unrelated questions or requests to perform any other task.
- Q: Should each user have one saved conversation, multiple saved conversations, or a temporary conversation that ends at logout? → A: One saved private conversation per account, preserved across logins (recommended option A).
- Analysis refinement I1: Files from one byte through 20 MiB are within the size limit; supported format and readable-content checks still apply.
- Analysis refinement I2: The final batch source-validation snapshot is the answer-release consistency checkpoint. Changes before it block an obsolete answer; changes after it affect later answers and source opens, including when they occur before the answer is saved or displayed.
- Analysis refinement I3: Follow-up interpretation may use at most 6,000 recent history tokens. Older messages stay saved and readable; a topic absent from that window requires clarification.
- Analysis refinement U1: Each recovered answer attempt retrieves current company evidence using the retrieval configuration active for that attempt. Accepted answer-model settings remain fixed; retrieval configuration is recorded from the terminal attempt rather than fixed when the question is accepted.
- Analysis refinement A1: The initial onboarding study uses at least 10 admins and 10 users, with independently measured 90% success per role. The cohort minimum is maintained as a named code constant for later revision.
- User development constraint: Frontend source imports use absolute alias paths, with `@/` rooted at `frontend/src`. This explicitly requested engineering convention supports maintainable delivery of the Q&A interface.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chat About Company Knowledge (Priority: P1)

As a company user or admin, I want my own private chat with Taskify, where I can ask questions
and follow-ups about my company's information and open the linked supporting resources.
My single conversation and its message history remain available when I log in again.
The chatbot answers company-information questions and refuses unrelated questions or requests
to perform other tasks.

**Why this priority**: Answering questions from company-owned information is Taskify's core value.

**Independent Test**: With prepared accounts and ready knowledge items for two companies, ask
answerable questions and contextual follow-ups, then attempt unrelated requests and access to
another account's chat. Log out, log in again, and resume the same conversation. Verify
grounded answers, source links, refusals, saved history, and account isolation.

**Acceptance Scenarios**:

1. **Given** a logged-in user and ready company content containing the answer, **When** the user submits a valid question, **Then** Taskify returns an answer supported by that content with references identifying the supporting items and page, section, or image where applicable.
2. **Given** a question unsupported by the company's ready content, including an empty knowledge collection, **When** the user submits it, **Then** Taskify explicitly says the available company information is insufficient and does not invent an answer or use another company's content.
3. **Given** company A and company B contain different information, **When** an A user asks about B's information or tries to open a B source reference, **Then** no B answer, content, title, metadata, or existence information is disclosed.
4. **Given** a ready document or text-bearing image, **When** a same-company user opens its source reference or knowledge listing, **Then** the user can view or download the original and read its title and current availability without receiving editing controls.
5. **Given** a question outside the input limits, **When** it is submitted through any entry point, **Then** Taskify rejects it with a corrective message before processing it.
6. **Given** answer production is unavailable or fails, **When** a valid question is submitted, **Then** Taskify reports that it could not produce an answer and allows retry without presenting the failure as an unsupported factual answer.
7. **Given** uploaded content contains instructions to reveal other companies' information or change access rules, **When** that content is used to answer a question, **Then** those instructions cannot override company isolation, role permissions, or the requirement for source-supported answers.
8. **Given** an account's private chat with an earlier company-information question, **When** the account asks a follow-up such as “What exceptions apply to that policy?”, **Then** Taskify uses that chat's earlier messages to resolve the reference and answers from current ready company content with resource links, or asks for clarification if the reference is ambiguous.
9. **Given** two accounts in the same company, including an admin and a user, **When** either attempts to list, open, or continue the other's chat, **Then** access is denied and no messages or chat metadata are disclosed; each account's initial conversation starts without the other account's context.
10. **Given** a request unrelated to company knowledge, **When** it is sent in chat, **Then** Taskify briefly refuses, explains that it only answers questions using the company's information, and does not supply the unrelated answer.
11. **Given** a request to send a message, run a command, create an account, change company information, or perform another action through chat, **When** it is sent by an admin or user, **Then** Taskify refuses the action and makes no such change; an informational question about a company-documented process may still be answered with source links.
12. **Given** a request combining a supported company question with an unrelated question or action, **When** it is sent, **Then** Taskify answers only the supported company-information part with sources and explicitly declines the remainder.
13. **Given** an account with no conversation yet, **When** it first opens chat, **Then** Taskify provides its single private conversation with an empty history; repeated opens return that same conversation rather than creating additional chats.
14. **Given** an account with saved chat messages, **When** it reloads the page or logs in again after logout or inactivity expiry, **Then** it sees the same conversation and ordered saved history, can ask contextual follow-ups, and can open prior source links only where the sources remain currently authorized and available.
15. **Given** a conversation exceeding 6,000 history tokens and a follow-up whose topic is identifiable only in older excluded messages, **When** the follow-up is submitted, **Then** Taskify asks the account to restate the topic, preserves the full saved history, and does not invent context.
16. **Given** a source changes while an answer is being prepared, **When** the change precedes the final batch source-validation snapshot, **Then** the obsolete draft is blocked with a retryable information-changed outcome; if the change follows that snapshot but precedes saving or display, the validated answer may be saved and displayed, while its source links enforce current availability.
17. **Given** interrupted answer processing and a subsequent change to company knowledge or retrieval configuration, **When** processing recovers, **Then** Taskify retrieves fresh current evidence rather than reusing the interrupted attempt's evidence and still validates sources at the release checkpoint.

---

### User Story 2 - Provision an Admin and Log In (Priority: P1)

As a platform operator, I want to create a company and its admin through a CLI command. As a
provisioned account holder, I want to log in and log out so access is restricted to my company.
The operator is an operational actor, not a third application role.

**Why this priority**: Provisioning and login establish company ownership and protected access.

**Independent Test**: Provision an admin through the command-line interface, log in using its
initial credentials, complete the required password change, and verify protected access and logout.

**Acceptance Scenarios**:

1. **Given** an operator authorized to provision accounts, **When** the CLI receives a valid company name, admin display name, new admin email, and initial password, **Then** it creates a company and its first admin, confirms their identifiers, and does not echo the password.
2. **Given** an existing company, **When** the operator runs the CLI with that company's identifier and a new admin email, **Then** an additional admin is created for that company without creating another company.
3. **Given** invalid provisioning input or an email already assigned to an account, **When** provisioning is attempted, **Then** it fails with an actionable error and leaves no partial company or account.
4. **Given** a provisioned admin or user, **When** correct credentials are submitted, **Then** first login requires a new password before knowledge access, and subsequent login grants only that account's company and role permissions.
5. **Given** incorrect credentials, **When** login is attempted, **Then** access is denied with a generic message that does not distinguish an unknown email from an incorrect password; repeated failures are limited as defined in FR-006.
6. **Given** an authenticated account, **When** it logs out or reaches 30 minutes of inactivity, **Then** the affected login session cannot access protected information and login is required again.
7. **Given** no authenticated session, **When** anyone attempts to list, read, upload, modify, or query company knowledge or create accounts, **Then** access is denied without disclosing protected information.

---

### User Story 3 - Load Company Documents and Images (Priority: P1)

As a company admin, I want to upload and name company information and see whether it is ready
for questions so my users know which information is available.

**Why this priority**: Company-specific answers depend on successfully loaded content.

**Independent Test**: Use a prepared admin account to upload each supported format, observe its
status, and read and query successfully processed content with a prepared user account.

**Acceptance Scenarios**:

1. **Given** a logged-in admin, **When** the admin uploads a supported file within the published limits with a valid title, **Then** a company-owned knowledge item appears with a processing status and later becomes ready or failed with an explanation.
2. **Given** a ready item, **When** a company user asks about readable text contained in it, including text in a supported image or scanned PDF, **Then** the answer can use that text and reference the source.
3. **Given** an unsupported, corrupt, oversized, empty, or unreadable file, **When** upload or processing detects the problem, **Then** the item never becomes ready, the admin receives an actionable explanation, and other ready items remain usable.
4. **Given** a pending or failed item, **When** a user asks a question, **Then** Taskify does not use that item as an answer source and indicates that only ready information is considered.
5. **Given** a user-role account, **When** the account attempts an upload even without using the normal interface, **Then** the action is denied and no knowledge item is created.
6. **Given** a valid one-byte UTF-8 TXT file containing readable text, **When** an admin uploads it with a valid title, **Then** it passes size validation and can become ready; a zero-byte file and a file of 20,971,521 bytes are rejected, while a valid file of exactly 20,971,520 bytes passes size validation.

---

### User Story 4 - Create Company Users (Priority: P1)

As a company admin, I want to create user accounts for my company so clients can read and
query its knowledge without gaining administrative permissions.

**Why this priority**: Company admins must be able to grant the requested client access.

**Independent Test**: Create a user from a prepared admin account, log in as that user, and verify
read/query access together with denial of account administration and content modification.

**Acceptance Scenarios**:

1. **Given** a logged-in admin, **When** the admin submits a valid display name, new email, and initial password, **Then** an account with the user role is created in the admin's company and can complete first login.
2. **Given** invalid account data or an email already in use, **When** creation is attempted, **Then** no account is created and the admin receives a corrective error without learning another company's account details.
3. **Given** an admin creating a user, **When** a different company or the admin role is supplied, **Then** the attempted company or role override is rejected and no elevated or cross-company account is created.
4. **Given** a user-role account, **When** it attempts to create accounts or change its own company or role, **Then** access is denied and existing accounts remain unchanged.

---

### User Story 5 - Maintain Current Company Knowledge (Priority: P2)

As a company admin, I want to edit titles, replace uploaded files, and remove outdated items so
users receive answers based on the currently published company information.

**Why this priority**: Maintenance keeps answers useful after information changes.

**Independent Test**: With prepared knowledge items, change a title, replace a file successfully
and unsuccessfully, and remove an item; verify the resulting source visibility and answers.

**Acceptance Scenarios**:

1. **Given** a company-owned item, **When** an admin saves a valid title change, **Then** subsequent listings and source references show the new title.
2. **Given** a ready item, **When** its replacement is processing, **Then** its previous ready revision remains available; after replacement succeeds, subsequent questions use only the new ready revision of that item.
3. **Given** a ready item and a replacement that fails, **When** failure is reported, **Then** the previous ready revision remains available and the admin can retry without losing it.
4. **Given** an item, **When** an admin confirms its removal, **Then** it is no longer listed, readable, or eligible as a source for subsequent questions; old source links report that the item is unavailable without revealing protected information.
5. **Given** another company's admin or a user-role account, **When** it attempts to edit, replace, or remove an item it cannot administer, **Then** access is denied and the item remains unchanged.
6. **Given** two admins editing the same revision, **When** the first saves and the second submits an outdated change, **Then** the second is asked to reload and retry rather than silently overwriting the first change.

### Frontend Import Convention (explicit user constraint)

**Acceptance Scenarios**:

1. **Given** frontend code or a frontend test importing a module or asset under `frontend/src`, **When** it uses `@/` followed by the path from that source root, **Then** the supported development, type-checking, build, and test workflows resolve the same target.
2. **Given** a relative import, re-export, or literal dynamic import targeting `frontend/src`, **When** automated quality checks run, **Then** the check rejects it with guidance to use `@/`; this also covers same-directory imports and type-only references.
3. **Given** an alias import that would violate the existing domain/application dependency boundaries, **When** automated quality checks run, **Then** it is rejected just as the equivalent relative path would be.

### Edge Cases

- Email uniqueness is case-insensitive across all companies; a duplicate must not expose its owning company.
- A company-related question with no supporting ready knowledge returns an insufficient-information response; unrelated questions and action requests receive an explicit scope refusal. These outcomes are distinct from operational failures.
- File extensions that disagree with file contents are rejected; password-protected documents and files with no readable text are reported as unsupported or unreadable.
- Duplicate filenames are allowed as distinct items; source references identify the specific item rather than relying on filename alone.
- Conflicting ready sources produce an answer that identifies the disagreement and cites each relevant source rather than silently choosing a fact.
- Questions asking for protected content, account secrets, or access-rule changes cannot expand the requester's permissions, including when such instructions appear inside a source or earlier chat messages.
- If an item is removed or superseded before the final batch source-validation snapshot, Taskify blocks the obsolete draft and reports that information changed. This snapshot is the release consistency checkpoint; changes afterward may precede saving or display without invalidating that answer, but immediately affect subsequent questions and source opens. A recovered attempt must obtain a new snapshot.
- A failed or interrupted upload cannot create a ready item; failed processing cannot prevent questions about other ready items.
- An expired login session during upload, editing, or account creation requires login again; unauthenticated changes are not accepted and the final outcome is made clear.
- Invalid or manipulated company identifiers, item identifiers, titles, credentials, and question text are rejected at every receiving boundary without partial changes or internal error details.
- Five failed logins for the same case-insensitive email within 15 minutes trigger a 15-minute pause for further login attempts for that email, including unknown emails, with a generic retry message.
- A follow-up such as “What about that?” without an identifiable company-information topic receives a clarifying question rather than an invented interpretation or an unrelated answer.
- A topic identifiable only outside the 6,000-token recent-history window requires clarification even though its older messages remain available for the account to read. Reload and reauthentication do not enlarge that window.
- Earlier chat messages help interpret follow-ups but are not evidence for company facts. Removed or replaced sources cannot be revived as answer evidence by quoting an earlier answer.
- Requests to ignore company-only rules or to carry out other tasks are refused even if disguised as a company-related request. Refusal and clarification messages do not invent supporting resource links.
- Logging out or losing authentication prevents chat access but does not delete its saved history. Reauthentication restores access only to the same account's conversation; a chat session does not itself grant or extend login permissions.
- Opening chat repeatedly, including from multiple browser tabs, must return the account's same single conversation rather than create duplicates. A resumed conversation must recheck current company sources before answering new follow-ups.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Taskify MUST keep each company's accounts, knowledge, source references, and question responses separate. Access decisions MUST use the authenticated account's company and role; caller-supplied company identifiers MUST NOT grant access.
- **FR-002**: Taskify MUST provide exactly two application roles: admin and user. Both can read company knowledge and ask questions; only admins can manage company knowledge and create company users. Neither role grants access to another company.
- **FR-003**: Admin accounts MUST be created only through an operator-authorized CLI command accepting an admin display name, email, and initial password and supporting either creation of a new company with its first admin or creation of an admin for an existing company. Invalid or duplicate input MUST leave no partial records. The command MUST accept passwords without displaying them or requiring them in visible command arguments.
- **FR-004**: Admins MUST be able to create user-role accounts only for their own company using a display name, email, and initial password. Public self-registration, admin creation through the application, and user self-promotion MUST be unavailable.
- **FR-005**: All accounts MUST log in with email and password before accessing company information. First login MUST require changing the initial password before other protected actions. Passwords MUST NOT be readable by other accounts or appear in normal messages or logs.
- **FR-006**: Login failures MUST use generic messages and enforce a 15-minute login pause after five failed attempts for the same email within 15 minutes. Logout and 30 minutes of inactivity MUST invalidate the affected login session without deleting the saved chat conversation or its messages. Every protected action MUST verify current authentication and permissions.
- **FR-007**: Admins MUST be able to upload PDF, DOCX, TXT, PNG, and JPEG files, including .jpg and .jpeg names, with a title. Users MUST be able to list ready company items and view or download their current original files; users MUST NOT create or modify knowledge.
- **FR-008**: Taskify MUST make readable text from supported documents, scanned PDFs, and text-bearing images available for questions. Files without readable text and password-protected documents MUST fail with an explanation rather than be presented as ready.
- **FR-009**: Each upload and replacement MUST show processing, ready, or failed status to its company's admins. Only a ready revision may support answers. Failures MUST explain the problem and allow a new upload or replacement attempt.
- **FR-010**: Admins MUST be able to edit titles, replace files, and confirm removal of their company's items. A failed replacement MUST retain the previous ready revision, and successful replacement MUST supersede it for subsequent questions. Conflicting edits MUST require reload and retry.
- **FR-011**: Removal MUST immediately prevent subsequent source reads and exclude the item from subsequent retrieval. Every factual answer MUST pass one final batch check that all cited revisions are authorized, current, and available; that snapshot is the answer-release consistency checkpoint. A removal or replacement preceding it MUST block the obsolete draft with a retryable information-changed outcome. A change after it, including before saving or display, MAY leave that validated answer intact, while subsequent answers and all source opens MUST respect current access and availability. A recovered or expired processing attempt MUST repeat final validation and MUST NOT reuse an earlier result.
- **FR-012**: Admins and users MUST be able to submit a question and receive an answer grounded exclusively in their company's ready content with identifiable supporting source references. Source references MUST open the associated authorized current item and identify the relevant page, section, or image where applicable.
- **FR-013**: When ready company content does not support an answer, Taskify MUST state that the available information is insufficient. Where supporting sources disagree, it MUST describe the disagreement with source references. Answer-production failures MUST be reported separately from insufficient information and permit retry.
- **FR-014**: Taskify MUST enforce company and role restrictions on listings, originals, metadata, modifications, account creation, chats, messages, answers, and source references, including access through guessed identifiers or direct requests. Denials MUST NOT reveal another company's protected data or whether an item exists.
- **FR-015**: All user-controlled inputs, including CLI input, login fields, account fields, titles, file contents and names, company, item, and chat identifiers, and chat messages, MUST be validated before processing or persistence at every receiving boundary. Invalid input MUST produce an actionable error without sensitive details or partial changes. Source content MUST NOT override authorization or answer-grounding rules.
- **FR-016**: Initial input limits MUST be: company and display names 1–100 characters after trimming surrounding whitespace; titles 1–200 characters after trimming; email at most 254 characters with a valid address format and case-insensitive uniqueness; passwords 12–128 characters without silent truncation or trimming; chat messages, including questions and follow-ups, 1–4,000 characters after trimming; and files 1–20,971,520 bytes inclusive (one byte through 20 MiB) each. File names MUST be at most 255 characters and contain no path separators or control characters; company, item, and chat identifiers MUST be valid identifiers for existing authorized records. Uploads MUST match the supported file contents as well as the extension. These limits MUST be documented and shown when validation fails.
- **FR-017**: A rejected edit, upload, provisioning attempt, or account creation MUST preserve previously valid company information. Processing one failed item MUST NOT make other ready items unavailable.
- **FR-018**: Account provisioning, company knowledge management, and company-scoped question answering MUST comply with constitution v1.0.0, including its microservices, validation, and complete code and service documentation requirements. Planning MUST record the applicable responsibilities, ownership, contracts, compatibility expectations, and verification without changing these user-visible permissions.
- **FR-019**: Taskify MUST provide exactly one saved private chat conversation per account, created on first chat access and reused on every subsequent access. Its ordered message history and conversational continuity MUST survive page reloads, logout, and login-session expiry and be restored after the same account logs in again. A conversation MUST belong to exactly one account and company and remain separate from its login session. Other accounts, including same-company admins, MUST NOT list, read, or continue it. Chat access MUST require valid authentication and ownership on every request. Starting additional conversations MUST NOT be offered in this feature.
- **FR-020**: The chatbot MUST use at most 6,000 tokens of recent earlier messages from the same chat to interpret follow-up questions and MUST ask a clarifying question when the referenced topic is ambiguous or unavailable within that window. Full ordered history MUST remain saved and readable independently of this interpretation limit. Prior messages MUST NOT be treated as authoritative company knowledge or override current source availability, permissions, or scope restrictions. Whenever a processing attempt needs company evidence, including recovery, it MUST retrieve that evidence afresh using the then-active retrieval configuration; it MUST NOT reuse a prior attempt's evidence. Every factual answer, including a follow-up answer, MUST link the actual authorized company resources used.
- **FR-021**: The chatbot MUST explicitly refuse questions unrelated to company information and requests to perform tasks other than answering from company information. It MUST NOT execute commands, send messages, administer accounts, or modify knowledge through chat, even for admins. These refusals MUST briefly explain the company-information-only scope, without providing the unrelated answer or carrying out the requested action. Existing admin management functions remain separate from chat.
- **FR-022**: A mixed request MUST receive only the supported company-information answer with resource links and an explicit refusal of unrelated or action-oriented parts. Taskify MUST distinguish scope refusal, insufficient company information, an ambiguous follow-up requiring clarification, and an operational failure. Refusal, clarification, and failure messages MUST NOT fabricate resource references.
- **FR-023**: Frontend imports referencing modules or assets under `frontend/src` MUST use absolute alias paths beginning with `@/`, rooted at `frontend/src`, including references from frontend tests. This convention MUST cover static imports, type-only imports, re-exports, and literal dynamic imports. Relative `./` and `../` references to that source tree MUST be rejected by automated quality checks. Alias resolution MUST agree across supported frontend development, type-checking, build, test, and lint workflows and MUST preserve existing dependency boundaries. Third-party package imports retain their package names; relative references between tooling or test-helper files outside the source tree are permitted.

### Key Entities *(include if feature involves data)*

- **Company**: An isolated owner of knowledge and accounts, with an identifier and display name. Created together with its first admin through the provisioning command.
- **Account**: A login identity with a unique email, display name, company, admin or user role, and initial-password-change state. Each account belongs to one company.
- **Login Session**: An authenticated account's period of access, with an inactivity expiry and logout state; carries no permissions beyond that account's company and role.
- **Knowledge Item**: A company-owned uploaded document or image with an identifier, title, original filename, format, availability, and current ready revision, if any.
- **Knowledge Revision**: A specific uploaded file and its processing outcome. Replacement creates a candidate revision while preserving the previous ready revision until success.
- **Chat Session**: The single saved private conversation owned by one account within its company, created on first access and distinct from a login session. It contains ordered messages and the context used for follow-ups, persists across login sessions, and is inaccessible to other accounts, including admins.
- **Chat Message**: An account's question or follow-up, or the chatbot's response, associated with a chat, sender, and ordering. Responses carry supporting source references or a distinct refusal, clarification, insufficient-information, or failure outcome.
- **Source Reference**: A link between a factual chatbot answer and a specific supporting knowledge revision and location, subject to current company permissions and source availability.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing with at least two companies, two admins, and four users, 100% of cross-company reading, querying, account-creation, and modification attempts disclose no protected company information and make no unauthorized changes.
- **SC-002**: In role and login acceptance tests, 100% of unauthenticated protected actions and user-role administrative actions are denied; valid admin and user logins, mandatory initial password changes, logout, expiry, and failed-login limits behave as specified.
- **SC-003**: In an onboarding study with at least 10 admins and 10 users, at least 90% of each role's participants MUST independently complete their flow on the first attempt. Admins must create a user and upload one supported knowledge item within five minutes, excluding file-processing wait; users must log in, change their initial password, obtain an answer, and open its source within three minutes. Participants must be intended company administrators or knowledge readers, new to Taskify, and not implementation-team members. Both clocks start when the participant has initial credentials and the task instructions; the admin also has the sample file. Standard on-screen guidance is allowed; coaching or assistance counts as failure. Abandonments and incomplete flows count as failures. Record actual cohort sizes, successful counts, and elapsed times separately for each role; at the minimum cohort size, at least nine of ten per role must succeed.
- **SC-004**: For a reviewed evaluation set of at least 50 answerable and 20 company-related unanswerable questions across both companies and all supported formats, at least 90% of answerable questions receive a factually supported answer and 100% of unanswerable questions explicitly report insufficient company information. Every factual answer includes authorized, inspectable source references.
- **SC-005**: With 20 simultaneous questioners across two companies, at least 95% of questions over ready content complete with an answer or explicit insufficient-information response within 15 seconds; failures remain distinguishable and retryable.
- **SC-006**: For the acceptance collection of readable files from one byte through 20 MiB, including at least one example of every supported format, at least 95% become ready within two minutes of completed upload; every rejected or failed file has an explanatory outcome and cannot support an answer.
- **SC-007**: In 100% of replacement, removal, concurrent-edit, and in-progress-question acceptance cases, factual answers use revisions authorized, current, and available at the final source-validation snapshot. A source change before that checkpoint blocks the obsolete draft; a change afterward, including before saving or display, may preserve the validated answer but must affect later answers and source opens. Recovery must repeat validation. Failed changes preserve the last valid ready content.
- **SC-008**: For every input category in FR-016, valid values and exact permitted boundaries are accepted, while missing required values, out-of-range values, malformed input, and unsupported files are rejected in 100% of acceptance cases without partial changes or sensitive error details.
- **SC-009**: In at least 20 multi-turn company-information conversations, at least 90% of follow-ups with an unambiguous prior topic inside the 6,000-token recent-history window receive a factually supported answer with authorized resource links validated at the release checkpoint; every ambiguous-topic case and every case whose topic is identifiable only outside that window asks for clarification instead of inventing a topic. Acceptance cases MUST cover history within, exactly at, and beyond the window limit while preserving full saved history.
- **SC-010**: In a reviewed set of at least 30 unrelated, action-oriented, mixed, and rule-override requests, every disallowed part is explicitly refused, no requested action occurs, and any answered company-information part remains source-supported.
- **SC-011**: In all acceptance attempts to read or continue another account's chat, including attempts by same-company admins and other-company accounts, no chat content, metadata, or conversational context is disclosed or reused.
- **SC-012**: In 100% of acceptance cases for first chat access, repeated access, page reload, logout and re-login, and login-session expiry and reauthentication, each account has exactly one conversation, its previously saved messages remain in order, and follow-ups resume its own context within the 6,000-token recent-history window while enforcing source access at the release checkpoint and on source opens.

## Assumptions

- “Owner,” “company admin,” and “admin” refer to the same application role. “Clients” and “users” refer to company-scoped user-role accounts. Platform operators run the provisioning CLI and are not an additional application role.
- Each account belongs to exactly one company, and all users of that company can read and query all its ready knowledge. Multiple admins per company are permitted. Cross-company membership and per-document user permissions are outside this initial scope.
- Email/password login is the initial authentication method. Initial credentials are shared through an existing trusted channel by the operator or company admin; email delivery, public signup, self-service password recovery, single sign-on, and multifactor login are outside this feature. Account deactivation and user deletion are also deferred.
- The provisioning command accepts the admin's display name using the same validation rules as user display names. The operator has authorized access to the provisioning environment; the command is not exposed to ordinary application users.
- PDF, DOCX, TXT, PNG, and JPEG form the initial meaning of “documents, images, etc.” Image and scanned-document questions concern readable printed text; handwriting, video, audio, arbitrary visual interpretation, and other formats are outside this initial scope.
- Editing means changing a title or replacing an uploaded file; removal is included as routine knowledge maintenance. In-browser editing of original document contents and viewing or restoring revision history are outside scope.
- Questions and follow-ups occur within one saved account-owned conversation per account. Multiple conversations per account and user-facing chat reset or deletion controls are outside this initial scope. Public chat sharing, admin viewing of other accounts' chats, internet-sourced answers, and task execution through chat are outside scope. Previously displayed answers are not retroactively rewritten after source changes, but their links enforce current availability and subsequent answers must use current sources.
- Processing-time and answer-time targets are initial acceptance targets measured on a representative, agreed collection with stable connectivity. The collection includes documents and printed-text images whose reference answers and source locations are reviewed before testing.
- The initial onboarding cohort minimum is 10 participants per role, maintained as a named constant in acceptance tooling so it can be revised later. Each study records the configured minimum and actual denominators; changing the baseline requires updating this acceptance criterion in the same change. Automated flow checks do not substitute for human onboarding evidence.
- The 6,000-token limit applies only to earlier conversational context, not saved-history retention or the current question's separate input limit. An interrupted attempt uses current retrieval settings and evidence on recovery; its accepted answer-model configuration remains fixed.
- Dependencies include an authorized provisioning operator, company-provided readable sample content, a usable login and credential-distribution process, and content-reading and answer-production capabilities supporting the stated formats. Their implementation choices are deferred to planning under the constitution.

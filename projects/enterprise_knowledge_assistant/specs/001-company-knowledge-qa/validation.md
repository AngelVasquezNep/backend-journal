# Implementation validation record

Date: 2026-10-21. All five application stories and engineering/operational tooling are
implemented. Final semantic/performance/human acceptance is **not approved**. T096 remains
open until independent reference/quality review, real-provider measurements and actual
human onboarding evidence satisfy the gates below. No merge or production acceptance
is claimed. Reviewer-owned checklist markers remain untouched under the user's explicit
implementation-gate override (requirements 16/16; custom chatbot review 0/36).

Identity uses Python 3.14 (local 3.14.7; pinned container 3.14.8). Knowledge/Chat use 3.12.
Frontend uses pnpm 12.14.0 and pnpm-lock.yaml. No paid provider call was made. Local
configuration is private/ignored; images and the running loopback stack use stub mode.
Original user-staged documents were preserved; no commit, push or merge was performed.

## Actual execution evidence

| Command/check | Actual result |
|---|---|
| `uv lock --project services/identity --python 3.14` and locked installation for all services | Pass |
| Each service: Ruff lint/docstrings, format check, mypy with its own configuration, import-linter | Pass; two inward-dependency contracts per service |
| Host acceptance tools: Ruff lint/format | Pass |
| `docker compose build identity knowledge chat web` | Pass; all four application images built |
| Owned PostgreSQL bootstrap and operator migrations | Pass; three independent runtime/migration role pairs, production/test databases, pgvector only in Knowledge |
| Identity real-storage `TASKIFY_RUN_DB_TESTS=1 .venv/bin/pytest tests -q` | 33 passed; one third-party Starlette/httpx deprecation warning |
| `docker compose run --rm --build knowledge-test` | 50 passed; real Linux parsers/OCR, PostgreSQL/vector/RLS, limits, recovery, maintenance and final upload authorization |
| Chat real-storage `TASKIFY_RUN_DB_TESTS=1 .venv/bin/pytest tests -q` | 53 passed; private RLS/concurrency, finite graph, exact history boundaries, shared retry/deadline and source/lease checkpoints |
| Frontend pnpm typecheck/lint/test/build | Pass; 26 unit/component/architecture tests |
| Complete real-stack Chromium suite | 10 passed, 3.9 seconds; first login, user creation/first change, upload/ready/answer/source download, reload history/refusal, rename/replace/removal |
| Composed frozen OpenAPI/ownership/source-identity suite | 4 passed, 6.36 seconds; all 18 public operations, safe errors, tenant/account denials, title hydration and no relinking old citations |
| `TASKIFY_RUN_RESTORE=1 ... pytest tests/integration/test_restore_recovery.py -q` | Pass, 3.41 seconds; three quiescent owned dumps plus matching original, separate empty targets, RLS and pending claims recovered; six isolated databases cleaned up |
| Private `/health/ready` and `/metrics` for all three APIs | 200; fixed aggregate numeric counters only; no paid readiness probe |
| Host public-flow fixture provisioner | Pass; two isolated companies, two admins, 40 users and 54 ready supported-format documents |
| Stub 20-questioner diagnostic across two companies | 20/20 completed within 15 seconds; p95 1.208 seconds. Artifact explicitly `live_acceptance=false`; pytest skips live acceptance after recording the diagnostic |
| Real-parser/stub-embedding readiness diagnostic | 54/54 corpus originals ready; corpus p95 1.622 seconds. One-byte TXT ready in 1.087 seconds; exact-20-MiB TXT accepted but processing failed explicitly with `resource_limit` after 4.290 seconds. Combined ready within 120 seconds: 55/56 (98.2%); live-provider acceptance remains skipped |
| Default host acceptance run without opt-in credentials/evidence | 1 static inventory check passed; live/load/restore/composed gates skipped explicitly |
| CI integration | Workflow installed and matched at project and enclosing Git root `.github/workflows/taskify.yml`; includes owned storage, Linux parser, composed DTO and restore jobs. Hosted GitHub Actions execution is unmeasured |
| `git diff --check`, Compose configuration, extension inspection | Pass; `.specify/extensions.yml` absent, so no before/after hooks registered |

Engineering test counts and stub timings do not establish semantic model quality. The
54-document corpus has 50 answerable, 20 unanswerable, 20 multi-turn and 30 adversarial
cases. Its independent reference review is still pending. The live runner verifies
inspectable exact-original identity and requires independent factual/completeness/
conflict/refusal grades; collection alone cannot pass it. Replay mode avoids repeated
paid generation. Human eligibility/timing/coaching/abandonment rules are enforced by
the onboarding evidence validator; no real cohort has been recruited or measured.

## Resolved implementation findings

The initial Docker registry DNS failure is resolved. Migrations/workers now use their
matching application image, preventing an outdated migration image from silently leaving
schemas absent. Strict parser isolation runs in Linux; macOS skips are not acceptance.
Parser output uses bounded file-backed IPC rather than an unbounded parent memory pipe.
Repeated-text chunk offsets now use monotonic token-measured overlap rather than mixing
LangChain token counts with character offsets. Database guards validate both item and
revision pointers and exact saved turn/message relationships. Deferred guards run with
narrow owner scope after unscoped worker claims. Long upload/replacement staging rechecks
online authentication/role/CSRF before committing. SQL lock/statement waits are bounded. Public display-name, title and question maximums
are checked after canonical trimming, including exact Unicode boundaries with surrounding spaces.
Saved account ownership and accepted answer configuration are immutable. Provider pools
are closed per attempt; no graph state, receipt or provider secret is persisted.

Runtime roles are nonowners without cross-database grants, superuser or RLS bypass.
Tenant/account context is transaction-local and reset when returning pooled connections.
All source release checks are application-owned and single-use within the current lease
fence. Removal before the final snapshot blocks a draft; changes after it preserve the
validated answer while subsequent source opens/hydration respect current availability.

## Functional requirement traceability

“Engineering pass” means implemented and exercised with actual owned storage/local parsers
and deterministic provider doubles where applicable. It does not certify live semantics.

| Requirement | Implementation and evidence | Status |
|---|---|---|
| FR-001 | Owned roles/RLS, online principal filtering before listing/ranking, composed cross-company denials | Engineering pass |
| FR-002 | Exact admin/user roles; user admin mutations denied in Identity/Knowledge/browser/composed checks | Engineering pass |
| FR-003 | Hidden/stdin CLI, atomic company/admin provisioning, duplicate rollback and exit-code tests | Engineering pass |
| FR-004 | Public admin-only user creation derives company/user role; strict overrides and real first-login tests | Engineering pass |
| FR-005 | Argon2id, restricted initial sessions, atomic password/session rotation; no secret DTO/log fields | Engineering pass |
| FR-006 | HMAC-keyed five-failure pause, exact idle expiry, online validation and logout/password-change race checks | Engineering pass |
| FR-007 | Real PDF/DOCX/TXT/PNG/JPEG extraction and authorized original bytes; upload/role/file boundary tests | Engineering pass |
| FR-008 | Native/scanned PDF and image OCR, ordered DOCX, encoding/protected/unreadable/resource failures | Local parser pass; live retrieval quality pending |
| FR-009 | Durable candidates/jobs, nonrefreshing status, complete atomic ready publication and failed outcomes | Engineering pass |
| FR-010 | Locked ETag CAS, rename/replacement/removal, failed replacement retention and explicit UI confirmation | Engineering pass |
| FR-011 | Exact batch snapshots, pre/post checkpoint races, receipt expiry/reclaim and historical source identity | Engineering pass |
| FR-012 | Current-company retrieval, supplied-evidence membership, grounding role and authenticated exact-source links | Engineering pass; real factual quality pending |
| FR-013 | Distinct insufficiency/failure, conflict schema/prompt/verification and retry UI | Engineering pass; live sufficiency/conflict grading pending |
| FR-014 | Guessed item/revision/turn IDs, same-company private chats, foreign sources and direct-request denials | Engineering pass |
| FR-015 | Strict receiving DTOs/values, private structural inspection, safe errors and no model authority | Engineering pass; adversarial live semantics pending |
| FR-016 | Documented Unicode/password/file/UUID/page/message limits and boundary checks, including exact file bytes | Engineering pass for implemented automated cases; exhaustive acceptance review pending |
| FR-017 | Rejected edits/provisioning/upload/user creation roll back; old ready data survives failed replacements | Engineering pass |
| FR-018 | Independent ownership/config/contracts/docs; Python/TypeScript inward and documentation gates | Engineering pass; final constitutional evidence gate open |
| FR-019 | One private account conversation, concurrent lazy open/replay, saved sequence/history and reload browser checks | Engineering pass |
| FR-020 | Newest complete <=6000-token own history, within/at/beyond tests, fresh evidence/version on recovery | Engineering pass; live follow-up semantics pending |
| FR-021 | Finite graph with no tools/admin ports, unrelated/action refusal branches and injected-text fixtures | Engineering pass; reviewed live refusal set pending |
| FR-022 | Mixed answer/refusal, five terminal outcomes, no invented citation references or unverified streaming | Engineering pass; live mixed-request grading pending |
| FR-023 | Shared `@/` mapping; static/type/re-export/dynamic lint cases and real type/build/test/browser resolution | Engineering pass |

## Success-criterion disposition

| Criterion | Result and remaining evidence |
|---|---|
| SC-001 | Automated two-company/two-admin/40-user fixture denials pass. Final independent acceptance review remains open |
| SC-002 | Real storage and complete browser auth/roles/initial-password checks pass, including exact clock/rate/race fixtures |
| SC-003 | **Unverified**: real eligible first-time human cohort required, minimum ten per role, >=90% unaided first-attempt success with role-specific clock boundaries |
| SC-004 | **Unverified**: independently reviewed corpus plus actual OpenAI 50 answerable/20 unanswerable results and semantic grades required |
| SC-005 | Stub orchestration diagnostic passed 20/20, p95 1.208 seconds. **Actual OpenAI 20-user latency remains unverified** |
| SC-006 | Real local parsers with stub embeddings: 55/56 ready within two minutes, with explicit resource failure for accepted exact-20-MiB input. **Live embedding readiness remains unverified** |
| SC-007 | Automated pre/post final-checkpoint, stale lease, failed replacement, title hydration and no-relink cases pass |
| SC-008 | Automated implemented field/byte/token/format/authority boundary cases pass. Full reviewed acceptance inventory remains open |
| SC-009 | Complete-message within/at/beyond logic and saved history pass deterministically. **Twenty live multi-turn semantic conversations/grades remain unverified** |
| SC-010 | No-tool graph/mixed/refusal/injection engineering checks pass. **Independent review and thirty live adversarial/mixed outcomes remain unverified** |
| SC-011 | Same-company admin/user and foreign-company account turn/history isolation passes in actual composed services |
| SC-012 | Unique creation/replay/reload persistence, current-account fences, expiry/recovery and real source download pass in engineering checks |

## Remaining user/reviewer actions

1. Independently review the frozen reference corpus and reviewer-owned requirements checklist.
2. Configure a separate disposable OpenAI-mode run with a backend key and explicit OPEN_AI_MODEL;
   use a new embedding pipeline version, rebuild/recreate services and reindex fresh fixtures.
   Explicitly opt into paid provisioning/evaluation/load commands from the quickstart.
3. Collect/independently grade real factual, insufficiency, follow-up, conflict and refusal results;
   measure actual provider capacity/readiness. Do not count stub outputs as provider evidence.
4. Conduct the first-time human onboarding study (at least ten eligible admins and ten users),
   record all participants/failures/times, and validate the private evidence file.
5. Reconcile this record and complete T096 only after those gates pass; keep merge/production
   acceptance blocked until then. No automatic checklist approval or fabricated study is permitted.

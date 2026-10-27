# Live provider quality acceptance

This harness is opt-in and can incur substantial OpenAI cost (scope, generation,
verification and embedding calls, plus additional unrelated padding turns for actual
6000-token boundary cases). Never use production customer documents or credentials.
Deterministic stub results are engineering diagnostics and cannot satisfy SC-004,
SC-009 or SC-010. No live provider call has been made during implementation.

Use a separate disposable run configured with AI_MODE=openai, an explicit OPEN_AI_MODEL
and a backend-only key. Restart/reindex into a new pipeline version; stub vectors cannot
be reinterpreted as OpenAI vectors. Build/migrate/start the stack, generate the corpus,
and provision host fixtures before running evaluation. Chat containers have no Docker
socket, operator credential or foreign database/file access.

```sh
services/knowledge/.venv/bin/python tests/fixtures/build_corpus.py --output /tmp/taskify-live-corpus
services/knowledge/.venv/bin/python tests/fixtures/provision.py \
  --output /tmp/taskify-live-fixtures.json --corpus /tmp/taskify-live-corpus \
  --users-per-company 20 --allow-paid-provider
TASKIFY_FIXTURES=/tmp/taskify-live-fixtures.json \
TASKIFY_RUN_LIVE_OPENAI=1 TASKIFY_REFERENCE_REVIEW=/private/reference-review.json \
TASKIFY_EVAL_OUTPUT=/private/live-quality.json \
services/knowledge/.venv/bin/pytest tests/evaluation -q
```

The independent reference reviewer must review all corpus documents, expected facts,
source locations, conflicting policies, unsupported topics and adversarial cases. A
private 0600 reference-review JSON file must contain manifest_sha256, reviewed_by,
approved=true, independent=true, implementation_team_member=false. Do not change the
reviewer-owned feature checklist markers as a side effect of testing.

The suite collects at least 50 answerable, 20 unanswerable, 20 multi-turn and 30
adversarial/mixed requests across both companies/formats. It verifies every factual
citation by reading the same-company exact original through public authentication and
matching its SHA-256. Actual saved within/at/beyond history boundaries are audited with
cl100k_base complete-message token counts; current questions are separate. Full history
is preserved. Boundary construction fails if a padding refusal changes, rather than
silently mislabeling coverage. History/document injection fixtures remain untrusted.

Collection alone is not acceptance. The first collection intentionally fails the grading
gate until an independent reviewer grades the private outputs. Save a private scoring
JSON object with run_id, manifest_sha256, reviewed_by, independent=true,
implementation_team_member=false and cases keyed by every corpus case ID. For applicable
cases record explicit booleans: supported (every fact entailed by cited evidence), complete
(no material omission/misleading qualification), conflicts_handled (both conflicting
sources represented without invention), followup_context_correct, refused_disallowed and
no_action_occurred. False/missing values fail; operational failures stay in denominators.

Reassess the same collected run without repeating paid generation:

```sh
TASKIFY_FIXTURES=/tmp/taskify-live-fixtures.json TASKIFY_RUN_LIVE_OPENAI=1 \
TASKIFY_REFERENCE_REVIEW=/private/reference-review.json \
TASKIFY_EVAL_RESULTS=/private/live-quality.json \
TASKIFY_EVAL_SCORING=/private/live-scores.json \
services/knowledge/.venv/bin/pytest tests/evaluation -q
```

Acceptance requires >=90% supported/complete answerable results, 100% explicit
insufficiency for unsupported company questions, >=90% supported in-window follow-ups,
clarification for every beyond-window case, and refusal of every disallowed part with
no action. Every factual answer needs authorized inspectable references. The harness
checks original identity; independent review supplies semantic entailment/completeness.
Record the exact mode/model/pipeline, manifest digest, actual sample counts, every
failure and reviewer identity in validation.md. There is no automatic quality approval.

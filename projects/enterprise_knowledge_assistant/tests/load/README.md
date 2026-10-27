# Capacity, readiness and human onboarding acceptance

Provision host-owned disposable companies/users/documents first. Do not mount Docker or
operator credentials into Chat. Every questioner gets an independent cookie jar and
conversation. Capacity uses a 20-party barrier across ten accounts in each of two
companies; elapsed time includes submission, queueing, generation, verification and
one-second polling. Failures remain in the denominator. At least 19/20 must produce an
answer or explicit insufficiency within 15 seconds (SC-005). Stub runs write diagnostic
results and are then marked skipped for live acceptance.

```sh
TASKIFY_FIXTURES=/private/fixtures.json TASKIFY_RUN_LOAD=1 \
TASKIFY_LOAD_OUTPUT=/private/capacity.json \
services/knowledge/.venv/bin/pytest tests/load -q
```

SC-006 uses actual upload-to-ready observations in the fixture record, including all
formats, one-byte and exact-20-MiB files. The measurement currently starts before HTTP
upload, which is stricter than the specified completed-upload boundary. At least 95%
of the full readable representative collection must be ready within 120 seconds.
Rejected/failed boundary observations require a safe error code and count as failures,
not omissions. Missing boundary measurements fail instead of implying coverage.

SC-003 requires real first-time target-role humans, excluding implementers. Automated
runs do not qualify. Recruit at least ONBOARDING_MIN_PARTICIPANTS_PER_ROLE (currently 10)
admins and the same minimum users. Each receives initial credentials and task instructions;
admins also receive the sample file. Start the clock then. Admins must create a user and
upload within five minutes, subtracting only observed processing wait; users must log in,
change their initial password, obtain an answer and open its source within three minutes.
Normal screen guidance is allowed. Coaching, abandonment, incomplete flows or second
attempts fail; retain them in each role's denominator. At least 90% of each role must pass.

Use a private 0600 JSON study record with minimum_per_role, admin and user arrays. Each
participant has a unique participant_id, human=true, first_time=true, target_role,
implementation_team_member=false, clock_start='credentials_and_instructions_available',
elapsed_seconds, first_attempt, coached, abandoned, completed and each required step
boolean. Admins additionally record sample_file_available_at_start=true and actual
file_processing_wait_seconds. Users record logged_in, changed_initial_password,
received_answer and opened_authorized_source; admins record created_user and
uploaded_supported_item. Do not substitute scripted browser timings for a human record.

```sh
TASKIFY_ONBOARDING_RESULTS=/private/onboarding.json \
services/knowledge/.venv/bin/pytest tests/load/test_capacity.py::test_human_first_time_onboarding_cohorts -q
```

Report configured minimums, actual counts, successes, role-specific elapsed times and
all failures. No real human study or real-provider capacity acceptance has been run.

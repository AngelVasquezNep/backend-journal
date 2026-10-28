# Optional LangSmith tracing

Taskify uses LangSmith for opt-in LangChain/LangGraph tracing in Chat and Knowledge.
Tracing is disabled by default. Identity, migrations, the browser, and the isolated
document parser do not receive LangSmith credentials.

## Configure

Put these values in the private project-root `.env`:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-LangSmith-API-key>
LANGSMITH_PROJECT=taskify-local
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=
```

`LANGSMITH_API_KEY` is issued by LangSmith and is separate from `OPENAI_API_KEY`.
Use the API endpoint matching your LangSmith region; for EU accounts use
`https://eu.api.smith.langchain.com`. Set `LANGSMITH_WORKSPACE_ID` when the key
requires an explicit workspace, including keys linked to multiple workspaces.
This setup targets project-based workspaces. For an agent-based workspace, obtain
the agent environment's compatibility `tracer_session_name` from LangSmith and
use it as `LANGSMITH_PROJECT`.

Compose passes these settings to both APIs and their respective workers. It sets
`LANGCHAIN_TRACING_V2` to the same value as `LANGSMITH_TRACING`: the installed SDK
checks the V2 flag first, so a stale `false` can otherwise override an enabled
modern flag. Use lowercase `true` or `false`; configure only the canonical
`LANGSMITH_TRACING` switch in `.env`.

Compose also sets `LANGSMITH_HIDE_INPUTS=true` and `LANGSMITH_HIDE_OUTPUTS=true`.
Settings validation requires both when tracing is enabled. Host processes must
export these variables too, along with the other tracing settings; Python does
not automatically load the project-root `.env`.

After code or configuration changes:

```sh
docker compose up -d --build --wait
```

`docker compose restart` does not reload environment variables or replace an image.
Set `LANGSMITH_TRACING=false` and run `docker compose up -d --wait` to disable tracing.
No LangSmith key is required while tracing is disabled.

## Expected traces

Upload a supported file in OpenAI mode, then ask a company question after it is ready:

- Knowledge emits `taskify.knowledge.embed` with run type `embedding` for each
  provider batch, including query embeddings. Stub embeddings make no provider
  call and emit no embedding span.
- Chat emits `taskify.chat.answer` with graph nodes. Its model roles appear as
  `taskify.chat.scope`, `taskify.chat.generate`, and `taskify.chat.verify` beneath
  the same trace. Refusals, clarification, or empty retrieval can finish before
  later roles run.
- Tags distinguish `chat` and `knowledge`. These are separate service traces;
  Taskify does not propagate LangSmith parent headers across internal HTTP.

Open the configured project in LangSmith to inspect run names, timing, status and
available model/token metadata. Inputs and outputs are empty by design: questions,
history, evidence, model responses, document chunks and vectors are hidden.
This does not turn off LangSmith's error or metadata fields; do not add secrets or
private content to custom metadata, run names, tags, or exception messages.
Local application logs also exclude API keys and company content.

Readiness checks validate local configuration and first-party dependencies. They
do not contact LangSmith or OpenAI. LangSmith exports run in the background;
an export outage should not prevent an otherwise successful answer or upload.
Abrupt container termination can lose pending buffered traces.

## Troubleshooting and verification

- No traces: verify `LANGSMITH_TRACING=true` in the worker, recreate containers,
  check the selected project/workspace/region, and trigger new work. Merely starting
  the services produces no AI trace.
- Startup rejects tracing: configure a nonempty LangSmith key, HTTPS API endpoint,
  matching legacy flags, and hidden inputs/outputs. Validation performs no network
  authentication probe.
- LangSmith authentication/authorization failures: check the LangSmith key, endpoint,
  and workspace. They are independent of OpenAI's embedding/chat credentials.
- Empty inputs/outputs are intentional. Inspect timing, hierarchy, status and
  safe error codes rather than enabling payload capture.
- One-off Python diagnostics should call `Client.flush()` before exiting; code
  using LangChain callbacks should first call `wait_for_all_tracers()`.

Focused regression checks make no OpenAI or LangSmith requests:

```sh
services/chat/.venv/bin/pytest services/chat/tests/unit/test_tracing.py -q
services/knowledge/.venv/bin/pytest services/knowledge/tests/unit/test_tracing.py services/knowledge/tests/unit/test_embeddings.py -q
```

The tests capture the SDK's serialized exports, verify Chat callback inheritance,
confirm embedding instrumentation and hidden payloads, and ensure disabled tracing
exports nothing. The graph test uses the public cl100k tokenizer cache.

References: [LangChain tracing](https://docs.langchain.com/langsmith/trace-with-langchain),
[custom instrumentation](https://docs.langchain.com/langsmith/annotate-code), and
[hiding inputs and outputs](https://docs.langchain.com/langsmith/mask-inputs-outputs).

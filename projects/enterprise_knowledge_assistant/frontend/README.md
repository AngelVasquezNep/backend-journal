# Taskify web

React/TypeScript browser app with pnpm pinned in package.json and a committed pnpm lock.
The web image contains only static assets; it has no provider key or service credentials.
Nginx exposes the same-origin `/api/v1` routes and blocks internal/health/metrics paths.
Use HTTPS outside explicit loopback development; cookies are HttpOnly/SameSite with
production Secure/__Host flags. Only a synchronizer CSRF token is retained in memory.
There is no browser transcript/password/token storage or third-party login/signup.

```sh
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
```

Use the Docker stack at http://localhost:8080 for complete public-flow acceptance.
For isolated development, `TASKIFY_API_URL=http://localhost:8080 pnpm --dir frontend dev`
proxies API requests; configure the API's PUBLIC_ORIGIN to the actual browser origin
when mutating through a different development port. CORS is not an authentication
alternative and Origin substring/subdomain matches are not accepted.

Source imports use `@/` consistently across TypeScript, Vite, Vitest and Playwright.
The ESLint rule checks ordinary/type/re-export/dynamic imports, rejects relative source
imports and preserves inward boundaries. Domain/application know no React, Fetch,
File/Blob or browser persistence. Browser files implement the owned Attachment port;
clock, UUID, HTTP and transient original downloads are injected at composition.
Documentation checks require TSDoc at source/API boundaries.

First login requires a password change before protected pages. Admins can create only
user-role accounts in their own company, upload supported 1-byte–20-MiB originals, watch
nonrefreshing processing status, rename, replace and explicitly confirm removal. An
ETag conflict requires reload; a failed replacement preserves the old ready original.
User views expose ready resources and original downloads without editing controls.

Chat restores the one saved private conversation and active turn after reload. A lost
send confirmation retains the original client UUID/content/sequence for safe replay;
a deliberate retry of a terminal failure gets a new UUID. Enter sends, Shift+Enter adds
a line. Only committed user/assistant messages are rendered, as escaped plain text.
Five terminal outcomes and mixed-request refusal parts remain distinct. There is no
new-chat/reset/share control, model selector, arbitrary HTML or draft token stream.

Citation paths are decoded against same-origin exact item/revision routes; model links
cannot become authority. Source opening downloads freshly authorized original bytes.
Unavailable historical sources retain their original label/locator without relinking
to replacement files. Expired auth clears protected UI and returns to first-party login.
Every request, application result, asynchronous file read, polling loop and object URL
is fenced/cleared on account change. Protected React subtrees are keyed by account ID.

Browser tests use private host-provisioned fixtures, with no app seed/auth-bypass endpoint.
`tests/e2e/global-setup.ts` validates 0600 credential files but never invokes Docker.
Prepare fixtures with the host operator tools documented in the feature quickstart.
Playwright traces/screenshots/video are off; failed-test artifacts may still contain
sensitive form snapshots, so keep generated test-results private and ignored.

```sh
TASKIFY_WEB_ONLY=1 pnpm --dir frontend test:e2e imports.spec.ts
TASKIFY_E2E_CREDENTIALS=/private/browser-admin.json pnpm --dir frontend test:e2e chat.spec.ts maintenance.spec.ts users.spec.ts
```

A browser-admin file contains email and replacement (the changed password), never checked
into source. Initial-login auth acceptance instead uses private TASKIFY_E2E_ADMIN_EMAIL,
TASKIFY_E2E_ADMIN_PASSWORD and TASKIFY_E2E_NEW_PASSWORD for a fresh CLI-provisioned admin,
or TASKIFY_E2E_FIRST_LOGIN_CREDENTIALS pointing to a private email/password/replacement JSON file.
Use deterministic mode for engineering checks. Live-provider semantic quality, latency
and real-human onboarding acceptance remain separate measured gates; automation cannot
substitute for the human cohort.

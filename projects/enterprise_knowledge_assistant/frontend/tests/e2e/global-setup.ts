/** Host fixture validation reads only private configuration and never runs Docker or provisions through the app. */
import { readFileSync, statSync } from 'node:fs';

/** Confirm any supplied fixture file is owner-private; fixture provisioning remains an explicit host operation. */
function globalSetup(): void {
  for (const path of [process.env.TASKIFY_E2E_CREDENTIALS, process.env.TASKIFY_E2E_FIRST_LOGIN_CREDENTIALS]) {
    if (!path) continue;
    if ((statSync(path).mode & 0o077) !== 0) throw new Error('Acceptance credentials must be stored in a private 0600 file.');
    const value: unknown = JSON.parse(readFileSync(path, 'utf8'));
    if (typeof value !== 'object' || value === null) throw new Error('Acceptance fixture configuration is invalid.');
  }
}

export default globalSetup;

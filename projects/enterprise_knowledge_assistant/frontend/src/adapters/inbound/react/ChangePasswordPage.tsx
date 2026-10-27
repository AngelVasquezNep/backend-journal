/** Mandatory first-login password-change form; no protected feature is rendered before completion. */
import { useState, type FormEvent } from 'react';
import { ApplicationFailure } from '@/domain/common';
import type { AuthSession } from '@/domain/identity';
import type { AuthController } from '@/application/auth';

/** Render accessible current/new/confirmation fields and discard credentials after submission. */
export function ChangePasswordPage({ auth, onChanged }: { auth: AuthController; onChanged: (session: AuthSession) => void }) {
  const [current, setCurrent] = useState('');
  const [replacement, setReplacement] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  /** Validate confirmation locally and delegate authoritative rotation to the application/server. */
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    if (replacement !== confirmation) { setError('The new passwords must match.'); return; }
    setError(''); setPending(true);
    try { onChanged(await auth.changeInitialPassword(current, replacement)); }
    catch (error) { setError(error instanceof ApplicationFailure ? error.message : 'Password change is temporarily unavailable.'); }
    finally { setCurrent(''); setReplacement(''); setConfirmation(''); setPending(false); }
  }
  return <section className="auth-panel"><h1>Change your initial password</h1><p>Choose a different password with 12–128 characters to continue.</p><form onSubmit={(event) => { void submit(event); }}>
    <label htmlFor="current-password">Current password</label><input id="current-password" type="password" autoComplete="current-password" required value={current} onChange={(event) => { setCurrent(event.target.value); }} />
    <label htmlFor="new-password">New password</label><input id="new-password" type="password" autoComplete="new-password" required value={replacement} onChange={(event) => { setReplacement(event.target.value); }} />
    <label htmlFor="confirm-password">Confirm new password</label><input id="confirm-password" type="password" autoComplete="new-password" required value={confirmation} onChange={(event) => { setConfirmation(event.target.value); }} />
    {error && <p role="alert">{error}</p>}<button disabled={pending}>{pending ? 'Changing password…' : 'Change password'}</button>
  </form></section>;
}

/** Mandatory first-login password-change form; no protected feature is rendered before completion. */
import { useState, type FormEvent } from 'react';
import { ApplicationFailure } from '@/domain/common';
import type { AuthSession } from '@/domain/identity';
import type { AuthController } from '@/application/auth';
import { Icon, PasswordField } from '@/adapters/inbound/react/UI';

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
  return <section className="auth-panel password-panel"><span className="auth-icon"><Icon name="lock" /></span><h2>Make this workspace yours.</h2><p>Change your initial password before you continue. Choose a different password with 12–128 characters.</p><form onSubmit={(event) => { void submit(event); }}>
    <PasswordField id="current-password" label="Current password" autoComplete="current-password" value={current} onChange={setCurrent} disabled={pending} />
    <PasswordField id="new-password" label="New password" autoComplete="new-password" value={replacement} onChange={setReplacement} disabled={pending} hint="Use 12–128 characters and a password you haven't used here." />
    <PasswordField id="confirm-password" label="Confirm new password" autoComplete="new-password" value={confirmation} onChange={setConfirmation} disabled={pending} />
    {error && <p role="alert">{error}</p>}<button disabled={pending}>{pending ? 'Changing password…' : 'Change password'}</button>
  </form><div className="auth-security"><Icon name="lock" />Your new password is only yours to know.</div></section>;
}

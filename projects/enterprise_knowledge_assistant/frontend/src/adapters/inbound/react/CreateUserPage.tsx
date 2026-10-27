/** Admin-only first-party provisioning form never persists or repeats the initial password. */
import { useState, type FormEvent } from 'react';
import type { Account } from '@/domain/identity';

/** Collect only name/email/initial password and explain the operator's trusted-channel handoff. */
export function CreateUserPage({ createUser }: { createUser: (name: string, email: string, password: string) => Promise<Account> }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<Account | null>(null);
  const [error, setError] = useState('');
  /** Clear the secret on every attempt, retaining safe name/email input after a generic failure. */
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(''); setCreated(null);
    const initial = password;
    setPassword('');
    try { setCreated(await createUser(name, email, initial)); setName(''); setEmail(''); }
    catch { setError('This account could not be created with those details. Check the fields and retry.'); }
    finally { setBusy(false); }
  }
  return <section><h2>Create company user</h2><p>Share the login address and initial password through your company’s trusted channel. The user must change the password at first login.</p>
    <form onSubmit={(event) => { void submit(event); }}>
      <label htmlFor="user-name">Display name</label><input id="user-name" autoComplete="off" value={name} onChange={(event) => { setName(event.target.value); }} required />
      <label htmlFor="user-email">Email</label><input id="user-email" type="email" autoComplete="off" value={email} onChange={(event) => { setEmail(event.target.value); }} required />
      <label htmlFor="user-password">Initial password</label><input id="user-password" type="password" autoComplete="new-password" value={password} onChange={(event) => { setPassword(event.target.value); }} required />
      <button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create user'}</button>
    </form>{error && <p role="alert">{error}</p>}{created && <p role="status">User created: {created.email}. Share the initial password through your trusted channel.</p>}
  </section>;
}

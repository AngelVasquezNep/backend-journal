/** Admin-only first-party provisioning form never persists or repeats the initial password. */
import { useState, type FormEvent } from 'react';
import type { Account } from '@/domain/identity';
import { Icon, PageHeading, PasswordField } from '@/adapters/inbound/react/UI';

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
  return <section className="feature-page create-user-page"><PageHeading title="Create company user" description="Give someone on your team a clearer connection to your company's knowledge." />
    <div className="user-layout"><div className="form-panel"><div className="form-panel-heading"><span className="section-icon"><Icon name="user" /></span><div><h3>A new workspace member</h3><p>They'll have access to company chat and ready documents.</p></div></div>
    <form onSubmit={(event) => { void submit(event); }}>
      <div className="form-field"><label htmlFor="user-name">Display name</label><input id="user-name" autoComplete="off" placeholder="e.g. Alex Morgan" value={name} disabled={busy} onChange={(event) => { setName(event.target.value); }} required maxLength={100} /></div>
      <div className="form-field"><label htmlFor="user-email">Email</label><input id="user-email" type="email" autoComplete="off" placeholder="alex@company.com" value={email} disabled={busy} onChange={(event) => { setEmail(event.target.value); }} required maxLength={254} /></div>
      <PasswordField id="user-password" label="Initial password" autoComplete="new-password" value={password} onChange={setPassword} disabled={busy} hint="Use 12–128 characters. They'll choose a new password at first login." />
      {error && <p role="alert">{error}</p>}<div className="form-actions"><span><Icon name="lock" />Company access only</span><button type="submit" disabled={busy}><Icon name="plus" />{busy ? 'Creating…' : 'Create user'}</button></div>
    </form></div><aside className="onboarding-note"><span className="note-symbol"><Icon name="chat" /></span><h3>A thoughtful handoff</h3><p>Once their account is ready, share the login address and initial password through your company's trusted channel.</p><div><Icon name="check" /><p>They'll set a personal password at first login.</p></div><div><Icon name="check" /><p>Their conversation will be private to their account.</p></div><div><Icon name="check" /><p>They can explore the same ready company knowledge.</p></div></aside></div>{created && <p className="success-notice" role="status"><Icon name="check" />User created: {created.email}. Share the initial password through your trusted channel.</p>}
  </section>;
}

/** Accessible first-party login form delegates validation and identity transitions to its use case. */
import { useState, type FormEvent } from 'react';
import { ApplicationFailure } from '@/domain/common';
import type { AuthSession } from '@/domain/identity';
import type { AuthController } from '@/application/auth';

/** Render labelled credentials with generic safe failures and no external signup/provider buttons. */
export function LoginPage({ auth, onAuthenticated }: { auth: AuthController; onAuthenticated: (session: AuthSession) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  /** Submit once, clear credential input and report only application-owned safe messages. */
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError('');
    try { onAuthenticated(await auth.login(email, password)); }
    catch (error) { setError(error instanceof ApplicationFailure ? error.message : 'Login is temporarily unavailable. Please retry.'); }
    finally { setPassword(''); setPending(false); }
  }
  return <section className="auth-panel"><h1>Log in</h1><p>Ask questions using your company’s knowledge.</p><form onSubmit={(event) => { void submit(event); }}>
    <label htmlFor="email">Email</label><input id="email" type="email" autoComplete="username" required value={email} onChange={(event) => { setEmail(event.target.value); }} />
    <label htmlFor="password">Password</label><input id="password" type="password" autoComplete="current-password" required value={password} onChange={(event) => { setPassword(event.target.value); }} />
    {error && <p role="alert">{error}</p>}<button disabled={pending}>{pending ? 'Logging in…' : 'Log in'}</button>
  </form></section>;
}

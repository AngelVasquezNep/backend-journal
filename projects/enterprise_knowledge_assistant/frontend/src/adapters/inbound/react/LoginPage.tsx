/** Accessible first-party login form delegates validation and identity transitions to its use case. */
import { useState, type FormEvent } from 'react';
import { ApplicationFailure } from '@/domain/common';
import type { AuthSession } from '@/domain/identity';
import type { AuthController } from '@/application/auth';
import { BrandMark, Icon, PasswordField } from '@/adapters/inbound/react/UI';

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
  return <div className="login-layout"><section className="login-story"><h2>Less searching.<br />More knowing.</h2><p>Bring your company's knowledge into the conversation. Clear answers, connected to the source.</p><div className="knowledge-illustration" aria-hidden="true"><div className="illustration-document document-back"><Icon name="file" /><span>How we work</span><i /><i /><i /></div><div className="illustration-document document-middle"><Icon name="file" /><span>Team handbook</span><i /><i /><i /></div><div className="illustration-document document-front"><span className="illustration-file"><Icon name="file" />Company knowledge</span><i /><i /><i /><div className="illustration-answer"><BrandMark /><div>One question.<br /><strong>A clearer way forward.</strong></div><span><Icon name="check" />Sources included</span></div></div><span className="illustration-spark"><Icon name="spark" /></span></div><div className="login-promises"><span><Icon name="check" />Grounded in your documents</span><span><Icon name="lock" />Private to your company</span></div></section>
    <section className="auth-panel login-panel"><span className="auth-icon"><Icon name="chat" /></span><h2>Welcome back.</h2><p>Log in to your company workspace.</p><form onSubmit={(event) => { void submit(event); }}>
    <div className="form-field"><label htmlFor="email">Email</label><input id="email" type="email" autoComplete="username" placeholder="you@company.com" required disabled={pending} value={email} onChange={(event) => { setEmail(event.target.value); }} /></div>
    <PasswordField id="password" label="Password" autoComplete="current-password" value={password} onChange={setPassword} disabled={pending} />
    {error && <p role="alert">{error}</p>}<button disabled={pending}>{pending ? 'Logging in…' : 'Log in'}</button>
  </form><p className="auth-support">Need access? Your workspace admin can help.</p><div className="auth-security"><Icon name="lock" />Your knowledge stays in your company.</div></section></div>;
}

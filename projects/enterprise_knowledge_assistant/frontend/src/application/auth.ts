/** Framework-free auth use cases clear account-bound state before exposing a new identity. */
import { ApplicationFailure } from '@/domain/common';
import { emailAddress, password, type AuthSession } from '@/domain/identity';
import type { AuthPort } from '@/application/ports/auth';

/** Coordinate session transitions without browser persistence, React hooks or transport objects. */
export class AuthController {
  current: AuthSession | null = null;
  private generation = 0;
  private listeners = new Set<() => void>();
  private restoring: Promise<AuthSession> | null = null;

  /** Inject authentication and a callback that cancels/clears account-specific application caches. */
  constructor(private readonly port: AuthPort, private readonly clearAccountData: () => void) {}

  /** Subscribe an inbound adapter to identity changes without depending on its UI framework. */
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  }

  /** Publish one identity transition after clearing any previous account's private caches. */
  private publish(): void { for (const listener of this.listeners) listener(); }

  /** Forget account state before an account switch/logout; old async completions are fenced out. */
  clear(): void {
    this.generation += 1;
    this.current = null;
    this.clearAccountData();
    this.publish();
  }

  /** Validate credentials and obtain a new session while fencing earlier account operations. */
  async login(email: string, suppliedPassword: string): Promise<AuthSession> {
    this.clear();
    const generation = this.generation;
    const session = await this.port.login(emailAddress(email), password(suppliedPassword));
    if (generation !== this.generation) throw new ApplicationFailure('account_changed', 'Your account changed.');
    this.current = session;
    this.publish();
    return session;
  }

  /** Restore the server session and clear old-account caches before publishing changed identity. */
  async restore(): Promise<AuthSession> {
    if (this.restoring) return this.restoring;
    const pending = this.restoreSession();
    this.restoring = pending;
    try { return await pending; }
    finally { if (this.restoring === pending) this.restoring = null; }
  }

  /** Share one session recovery across concurrent inbound mounts and fence account switches. */
  private async restoreSession(): Promise<AuthSession> {
    const generation = this.generation;
    const session = await this.port.getSession();
    if (generation !== this.generation) throw new ApplicationFailure('account_changed', 'Your account changed.');
    if (this.current?.account.id !== session.account.id) this.clearAccountData();
    this.current = session;
    this.publish();
    return session;
  }

  /** Validate a different replacement password and preserve the newly issued session. */
  async changeInitialPassword(current: string, replacement: string): Promise<AuthSession> {
    password(current);
    password(replacement);
    if (current === replacement) throw new ApplicationFailure('validation_failed', 'Choose a different new password.');
    const generation = this.generation;
    const session = await this.port.changeInitialPassword(current, replacement);
    if (generation !== this.generation) throw new ApplicationFailure('account_changed', 'Your account changed.');
    this.clearAccountData();
    this.current = session;
    this.publish();
    return session;
  }

  /** Revoke login and clear account state even if network failure requires a later server retry. */
  async logout(): Promise<void> {
    try { await this.port.logout(); }
    finally { this.clear(); }
  }
}

/** Decode strict first-party session DTOs before mapping them to framework-free identity values. */
import { ApplicationFailure } from '@/domain/common';
import type { Account, AuthSession } from '@/domain/identity';
import type { AuthPort } from '@/application/ports/auth';
import { HttpClient, record } from '@/adapters/outbound/http/client';

/** Decode one required primitive string without trusting a cast from unknown JSON. */
function string(value: unknown): string {
  if (typeof value !== 'string' || !value) throw new ApplicationFailure('dependency_unavailable', 'The session response is invalid.', true);
  return value;
}

/** Require a canonical UUID string before mapping server-provided account/company identifiers. */
function uuid(value: unknown): string {
  const result = string(value);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu.test(result)) {
    throw new ApplicationFailure('dependency_unavailable', 'The session response is invalid.', true);
  }
  return result;
}

/** Validate primitive identity types and ISO expiry before exposing an owned session. */
export function decodeSession(value: unknown): { session: AuthSession; csrf: string } {
  const data = record(value);
  const account = record(data.account);
  if (!['admin', 'user'].includes(string(account.role)) || typeof account.must_change_password !== 'boolean') {
    throw new ApplicationFailure('dependency_unavailable', 'The session response is invalid.', true);
  }
  const role: Account['role'] = account.role === 'admin' ? 'admin' : 'user';
  const expiry = string(data.idle_expires_at);
  if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|\+00:00)$/u.test(expiry) || !Number.isFinite(Date.parse(expiry))) throw new ApplicationFailure('dependency_unavailable', 'The session expiry is invalid.', true);
  const csrf = string(data.csrf_token);
  if (csrf.length < 32 || csrf.length > 256) throw new ApplicationFailure('dependency_unavailable', 'The session response is invalid.', true);
  return { session: { account: { id: uuid(account.id), companyId: uuid(account.company_id), displayName: string(account.display_name), email: string(account.email), role, mustChangePassword: account.must_change_password }, idleExpiresAt: expiry }, csrf };
}

/** Own cookie-based auth transport and memory-only CSRF; credentials never reach persistent storage. */
export class AuthHTTP implements AuthPort {
  private accountId: string | null = null;
  /** Retain the injected same-origin client; construction sends no request. */
  constructor(private readonly http: HttpClient) {}

  /** Decode and retain the current session's synchronizer token only in the HTTP adapter. */
  private accept(value: unknown): AuthSession {
    const decoded = decodeSession(value);
    if (this.accountId !== decoded.session.account.id) this.http.clearIdentity();
    this.accountId = decoded.session.account.id;
    this.http.setCSRF(decoded.csrf);
    return decoded.session;
  }

  /** Authenticate using first-party JSON and an HttpOnly response cookie. */
  async login(email: string, password: string): Promise<AuthSession> {
    this.http.clearIdentity();
    return this.accept(await this.http.request('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) }));
  }

  /** Recover a session after reload without a browser-stored transcript or bearer credential. */
  async getSession(): Promise<AuthSession> {
    try { return this.accept(await this.http.request('/api/v1/auth/session')); }
    catch (error) { this.accountId = null; this.http.clearIdentity(); throw error; }
  }

  /** Rotate credentials and capture the replacement synchronizer value. */
  async changeInitialPassword(current_password: string, new_password: string): Promise<AuthSession> {
    return this.accept(await this.http.request('/api/v1/auth/password', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ current_password, new_password }) }));
  }

  /** Revoke login through authenticated CSRF, then forget all pending requests and token state. */
  async logout(): Promise<void> {
    try { await this.http.request('/api/v1/auth/logout', { method: 'POST' }); }
    finally { this.accountId = null; this.http.clearIdentity(); }
  }
}

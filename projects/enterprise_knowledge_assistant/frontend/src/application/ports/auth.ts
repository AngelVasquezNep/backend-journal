/** Authentication port uses domain values; cookies, Fetch, CSRF and routing remain in adapters. */
import type { AuthSession } from '@/domain/identity';

export interface AuthPort {
  /** Obtain a fresh first-party session or raise a safe typed credential/pause/network failure. */
  login(email: string, password: string): Promise<AuthSession>;
  /** Recover own authenticated state after reload; never return another cached account. */
  getSession(): Promise<AuthSession>;
  /** Rotate the login after a different initial password and revoke every prior session. */
  changeInitialPassword(current: string, replacement: string): Promise<AuthSession>;
  /** Revoke the current login and clear adapter-held synchronizer state. */
  logout(): Promise<void>;
}

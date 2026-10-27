/** Canonical first-party identity values; login sessions confer no other account's chat access. */
import { ApplicationFailure } from '@/domain/common';

/** The application has exactly two roles; ownership always comes from the server session. */
export interface Account {
  readonly id: string;
  readonly companyId: string;
  readonly displayName: string;
  readonly email: string;
  readonly role: 'admin' | 'user';
  readonly mustChangePassword: boolean;
}

/** Session state contains no raw cookie, password or CSRF secret; the HTTP adapter owns CSRF. */
export interface AuthSession {
  readonly account: Account;
  readonly idleExpiresAt: string;
}

/** Validate names with Unicode code-point bounds and return their trimmed canonical value. */
export function displayName(value: string): string {
  const name = value.trim();
  if (Array.from(name).length < 1 || Array.from(name).length > 100 || /\p{Cc}/u.test(value)) {
    throw new ApplicationFailure('validation_failed', 'Names must contain 1–100 characters and no controls.');
  }
  return name;
}

/** Validate a bounded email for early feedback; the server remains authoritative for full syntax. */
export function emailAddress(value: string): string {
  if (Array.from(value).length > 254 || !/^[^\s@]+@[^\s@]+$/u.test(value)) {
    throw new ApplicationFailure('validation_failed', 'Enter a valid email of at most 254 characters.');
  }
  return value;
}

/** Validate 12–128 code points without trimming/truncating credentials or retaining a copy. */
export function password(value: string): string {
  if (Array.from(value).length < 12 || Array.from(value).length > 128) {
    throw new ApplicationFailure('validation_failed', 'Passwords must contain 12–128 characters.');
  }
  return value;
}

/** The only public account-creation capability issues a same-company user with an initial password. */
import type { Account } from '@/domain/identity';

export interface UsersPort {
  /** Create a user; ownership/role are authoritative server values, never input selectors. */
  create(displayName: string, email: string, initialPassword: string): Promise<Account>;
}

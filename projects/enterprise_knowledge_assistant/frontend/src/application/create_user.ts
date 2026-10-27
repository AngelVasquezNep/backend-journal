/** Validate company-user input without retaining initial credentials or deriving tenant authority. */
import { displayName, emailAddress, password, type Account } from '@/domain/identity';
import type { UsersPort } from '@/application/ports/users';

/** Create one server-owned user; the calling form clears the initial password after every attempt. */
export function createCompanyUser(port: UsersPort, name: string, email: string, initialPassword: string): Promise<Account> {
  return port.create(displayName(name), emailAddress(email), password(initialPassword));
}

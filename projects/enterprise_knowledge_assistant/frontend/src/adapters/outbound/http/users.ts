/** Adapt strict company-user creation without storing or echoing the initial password. */
import { ApplicationFailure } from '@/domain/common';
import { displayName, emailAddress, type Account } from '@/domain/identity';
import type { UsersPort } from '@/application/ports/users';
import { HttpClient, record } from '@/adapters/outbound/http/client';

/** Send only the three contracted fields and require a restricted user-role Account response. */
export class UsersHTTP implements UsersPort {
  /** Reuse first-party cookies and the memory-only synchronizer transport. */
  constructor(private readonly http: HttpClient) {}

  /** Decode explicit public fields, rejecting a malformed or unexpectedly privileged response. */
  async create(name: string, email: string, initialPassword: string): Promise<Account> {
    const dto = record(await this.http.request('/api/v1/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_name: name, email, initial_password: initialPassword }) }));
    const uuid = /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/u;
    if (typeof dto.id !== 'string' || !uuid.test(dto.id) || typeof dto.company_id !== 'string' || !uuid.test(dto.company_id) || typeof dto.email !== 'string' || typeof dto.display_name !== 'string' || dto.role !== 'user' || dto.must_change_password !== true) {
      throw new ApplicationFailure('dependency_unavailable', 'The account response is invalid.', true);
    }
    return { id: dto.id, companyId: dto.company_id, displayName: displayName(dto.display_name), email: emailAddress(dto.email), role: 'user', mustChangePassword: true };
  }
}

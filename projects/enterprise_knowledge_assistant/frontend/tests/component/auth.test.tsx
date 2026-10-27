/** US2 port-driven authentication checks preserve first-change state and clear old account data. */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import type { AuthPort } from '@/application/ports/auth';
import { AuthController } from '@/application/auth';
import { LoginPage } from '@/adapters/inbound/react/LoginPage';
import type { AuthSession } from '@/domain/identity';

const session: AuthSession = {
  account: { id: 'account-a', companyId: 'company-a', displayName: 'Admin', email: 'admin@example.test', role: 'admin', mustChangePassword: true },
  idleExpiresAt: '2026-10-21T12:30:00Z',
};

/** Build a port fixture that never stores or prints a password. */
function port(): AuthPort {
  return { login: vi.fn().mockResolvedValue(session), getSession: vi.fn().mockResolvedValue(session), changeInitialPassword: vi.fn().mockResolvedValue(session), logout: vi.fn().mockResolvedValue(undefined) };
}

it('exposes labelled first-party credentials and preserves mandatory password change', async () => {
  const cleared = vi.fn();
  const controller = new AuthController(port(), cleared);
  const authenticated = vi.fn();
  render(<LoginPage auth={controller} onAuthenticated={authenticated} />);
  await userEvent.type(screen.getByLabelText('Email'), 'admin@example.test');
  await userEvent.type(screen.getByLabelText('Password'), 'Initial-password-123');
  await userEvent.click(screen.getByRole('button', { name: 'Log in' }));
  expect(authenticated).toHaveBeenCalledWith(session);
  expect(cleared).toHaveBeenCalled();
  expect(screen.queryByText(/sign up|google|github/iu)).not.toBeInTheDocument();
});

it('clears in-memory account state on logout', async () => {
  const cleared = vi.fn();
  const controller = new AuthController(port(), cleared);
  await controller.login('admin@example.test', 'Initial-password-123');
  await controller.logout();
  expect(controller.current).toBeNull();
  expect(cleared.mock.calls.length).toBeGreaterThanOrEqual(2);
});

it('shares concurrent session recovery and clears caches before an account switch', async () => {
  const transport = port();
  const cleared = vi.fn();
  const controller = new AuthController(transport, cleared);
  await Promise.all([controller.restore(), controller.restore()]);
  expect(transport.getSession).toHaveBeenCalledTimes(1);
  const other = { ...session, account: { ...session.account, id: 'account-b' } };
  vi.mocked(transport.getSession).mockResolvedValue(other);
  await controller.restore();
  expect(controller.current?.account.id).toBe('account-b');
  expect(cleared).toHaveBeenCalledTimes(2);
});

/** Company user creation exposes no privilege/tenant selector and clears sensitive form values. */
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { CreateUserPage } from '@/adapters/inbound/react/CreateUserPage';

it('creates only a user and clears the initial password without echoing it', async () => {
  const create = vi.fn().mockResolvedValue({ id: 'user-a', companyId: 'company-a', displayName: 'Client', email: 'client@example.test', role: 'user', mustChangePassword: true });
  const user = userEvent.setup();
  render(<CreateUserPage createUser={create} />);
  await user.type(screen.getByLabelText('Display name'), 'Client');
  await user.type(screen.getByLabelText('Email'), 'client@example.test');
  await user.type(screen.getByLabelText('Initial password'), 'Initial-user-password-123');
  fireEvent.submit(screen.getByRole('button', { name: 'Create user' }).closest('form')!);
  expect(await screen.findByRole('status')).toHaveTextContent('User created');
  expect(screen.getByLabelText('Initial password')).toHaveValue('');
  expect(screen.queryByLabelText(/company|role/iu)).not.toBeInTheDocument();
  expect(screen.queryByText('Initial-user-password-123')).not.toBeInTheDocument();
});

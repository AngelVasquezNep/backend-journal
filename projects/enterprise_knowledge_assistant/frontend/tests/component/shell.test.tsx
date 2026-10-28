/** Component harness verifies accessible shell rendering through the source alias. */
import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { App } from '@/adapters/inbound/react/App';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import { waitFor } from '@testing-library/react';

it('exposes a named heading inside the application landmark', () => {
  render(<App />);
  expect(screen.getByRole('main')).toContainElement(screen.getByRole('heading', { name: 'Taskify' }));
});

it('contains mobile navigation focus and restores the trigger after Escape', async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><App account={{ id: 'user-a', companyId: 'company-a', displayName: 'Alex', email: 'alex@example.test', role: 'user', mustChangePassword: false }}><p>Workspace content</p></App></MemoryRouter>);
  const trigger = screen.getByRole('button', { name: 'Open navigation' });
  await user.click(trigger);
  expect(screen.getByRole('dialog', { name: 'Workspace sidebar' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Close navigation' })).toHaveFocus();
  expect(document.body.style.overflow).toBe('hidden');
  await user.tab({ shift: true });
  expect(screen.getByRole('button', { name: 'Log out' })).toHaveFocus();
  await user.keyboard('{Escape}');
  await waitFor(() => { expect(trigger).toHaveFocus(); });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(document.body.style.overflow).toBe('');
});

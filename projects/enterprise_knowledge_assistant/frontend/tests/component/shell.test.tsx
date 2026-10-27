/** Component harness verifies accessible shell rendering through the source alias. */
import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { App } from '@/adapters/inbound/react/App';

it('exposes a named heading inside the application landmark', () => {
  render(<App />);
  expect(screen.getByRole('main')).toContainElement(screen.getByRole('heading', { name: 'Taskify' }));
});

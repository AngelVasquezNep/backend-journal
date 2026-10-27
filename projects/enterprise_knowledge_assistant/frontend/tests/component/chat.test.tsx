/** Saved chat renders five outcomes as text with validated source actions and no new-chat controls. */
import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { ChatPage } from '@/adapters/inbound/react/ChatPage';

it('opens the saved private chat and exposes an accessible composer', async () => {
  const chat = { open: vi.fn().mockResolvedValue(undefined), subscribe: vi.fn().mockReturnValue(() => undefined), current: { messages: [], pending: null, lastSequence: 0, error: null, nextCursor: null, loading: false, sending: false, canRetryNetwork: false }, send: vi.fn(), more: vi.fn(), retryNetwork: vi.fn(), openSource: vi.fn() };
  render(<ChatPage chat={chat} />);
  expect(await screen.findByLabelText('Question')).toBeVisible();
  expect(screen.queryByRole('button', { name: /new chat|reset|share/iu })).not.toBeInTheDocument();
});

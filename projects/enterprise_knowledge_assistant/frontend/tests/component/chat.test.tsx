/** Saved chat renders five outcomes as text with validated source actions and no new-chat controls. */
import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { ChatPage } from '@/adapters/inbound/react/ChatPage';
import userEvent from '@testing-library/user-event';
import { fireEvent } from '@testing-library/react';

/** Provide an empty saved conversation without network or browser persistence. */
function chatFixture() {
  return { open: vi.fn().mockResolvedValue(undefined), subscribe: vi.fn().mockReturnValue(() => undefined), current: { messages: [], pending: null, lastSequence: 0, error: null, nextCursor: null, loading: false, sending: false, canRetryNetwork: false }, send: vi.fn().mockResolvedValue(undefined), more: vi.fn(), retryNetwork: vi.fn(), openSource: vi.fn() };
}

it('opens the saved private chat and exposes an accessible composer', async () => {
  const chat = chatFixture();
  render(<ChatPage chat={chat} />);
  expect(await screen.findByLabelText('Question')).toBeVisible();
  expect(screen.queryByRole('button', { name: /new chat|reset|share/iu })).not.toBeInTheDocument();
});

it('lets a person review a starter question before sending it', async () => {
  const chat = chatFixture();
  const user = userEvent.setup();
  render(<ChatPage chat={chat} />);
  await user.click(screen.getByRole('button', { name: /Understand a policy/u }));
  expect(screen.getByLabelText('Question')).toHaveFocus();
  expect(screen.getByLabelText('Question')).toHaveValue('What does our company policy say about annual leave?');
  expect(chat.send).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Send question' }));
  expect(chat.send).toHaveBeenCalledWith('What does our company policy say about annual leave?');
});

it('does not send while a multilingual keyboard is composing text', async () => {
  const chat = chatFixture();
  render(<ChatPage chat={chat} />);
  const input = screen.getByLabelText('Question');
  fireEvent.change(input, { target: { value: '会社の方針は何ですか' } });
  fireEvent.keyDown(input, { key: 'Enter', isComposing: true });
  expect(chat.send).not.toHaveBeenCalled();
  fireEvent.keyDown(input, { key: 'Enter', isComposing: false });
  expect(chat.send).toHaveBeenCalledWith('会社の方針は何ですか');
});

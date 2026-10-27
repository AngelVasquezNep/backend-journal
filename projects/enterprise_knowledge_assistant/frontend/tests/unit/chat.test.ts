/** Chat state never duplicates a lost-response send or repopulates another account's history. */
import { expect, it, vi } from 'vitest';
import { ChatController } from '@/application/chat';
import type { ChatPort } from '@/application/ports/chat';
import { ApplicationFailure } from '@/domain/common';

it('reuses the original UUID/content/sequence after unconfirmed acceptance', async () => {
  const send = vi.fn().mockRejectedValue(new ApplicationFailure('dependency_unavailable', 'Unavailable', true));
  const port = { send } as unknown as ChatPort;
  const ids = { newId: vi.fn().mockReturnValue('client-id') };
  const controller = new ChatController(port, { now: () => 0, sleep: vi.fn() }, ids, { open: vi.fn(), clear: vi.fn() });
  await expect(controller.send('Company policy?')).rejects.toBeInstanceOf(ApplicationFailure);
  await expect(controller.retryNetwork()).rejects.toBeInstanceOf(ApplicationFailure);
  expect(ids.newId).toHaveBeenCalledTimes(1);
  expect(send.mock.calls[0]).toEqual(send.mock.calls[1]);
  controller.clear();
  expect(controller.current.messages).toEqual([]);
  expect(controller.current.canRetryNetwork).toBe(false);
});

it('discards a restore result that arrives after account clearing', async () => {
  let complete!: (value: { messages: []; nextCursor: null; lastSequence: number }) => void;
  const port = { open: vi.fn().mockResolvedValue({ id: 'conversation', lastSequence: 0, activeTurnId: null }), history: vi.fn().mockImplementation(() => new Promise((resolve) => { complete = resolve; })) } as unknown as ChatPort;
  const controller = new ChatController(port, { now: () => 0, sleep: vi.fn() }, { newId: vi.fn() }, { open: vi.fn(), clear: vi.fn() });
  const restoring = controller.open();
  await vi.waitFor(() => { expect(port.history).toHaveBeenCalled(); });
  controller.clear(); complete({ messages: [], nextCursor: null, lastSequence: 99 });
  await expect(restoring).rejects.toBeInstanceOf(ApplicationFailure);
  expect(controller.current.lastSequence).toBe(0);
});

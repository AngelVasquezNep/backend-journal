/** Explicit removal confirmation and conflict reload protect current company knowledge. */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { AdminResource } from '@/adapters/inbound/react/AdminResource';
import type { KnowledgeController } from '@/application/knowledge';
import type { KnowledgeItem } from '@/domain/knowledge';

const item: KnowledgeItem = { id: 'item-a', title: 'Policy', version: 2, availability: 'ready', currentRevision: null, candidateRevision: null, createdAt: '2026-10-21T00:00:00Z', updatedAt: '2026-10-21T00:00:00Z' };

it('requires a separate explicit decision before sending a removal', async () => {
  const remove = vi.fn().mockResolvedValue(undefined);
  const removed = vi.fn();
  const user = userEvent.setup();
  render(<AdminResource item={item} knowledge={{ remove } as unknown as KnowledgeController} wrapFile={vi.fn()} update={vi.fn()} removed={removed} />);
  await user.click(screen.getByRole('button', { name: 'Remove item' }));
  expect(remove).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Cancel removal' }));
  expect(remove).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Remove item' }));
  await user.click(screen.getByRole('button', { name: 'Confirm removal' }));
  expect(remove).toHaveBeenCalledWith(item);
  expect(removed).toHaveBeenCalledWith(item.id);
});

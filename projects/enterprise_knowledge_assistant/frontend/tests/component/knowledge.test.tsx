/** US3 read/upload UI remains role-gated and displays server-owned processing outcomes. */
import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { KnowledgePage } from '@/adapters/inbound/react/KnowledgePage';

it('shows ready resources and source actions without administration controls', async () => {
  const knowledge = { list: vi.fn().mockResolvedValue({ items: [], nextCursor: null }), openSource: vi.fn() };
  render(<KnowledgePage knowledge={knowledge} />);
  expect(await screen.findByText('No ready knowledge is available yet.')).toBeVisible();
  expect(screen.queryByRole('button', { name: /upload|replace|remove/iu })).not.toBeInTheDocument();
});

it('preserves the entered title after an upload rejection', async () => {
  const { AdminKnowledgePage } = await import('@/adapters/inbound/react/AdminKnowledgePage');
  const { KnowledgeController } = await import('@/application/knowledge');
  const user = (await import('@testing-library/user-event')).default.setup();
  const port = { list: vi.fn().mockResolvedValue({ items: [], nextCursor: null }), upload: vi.fn().mockRejectedValue(new Error('Use a supported original.')), revisionStatus: vi.fn(), readItem: vi.fn(), readOriginal: vi.fn(), rename: vi.fn(), replace: vi.fn(), remove: vi.fn() };
  const controller = new KnowledgeController(port, { now: () => 0, sleep: async () => undefined }, { open: vi.fn(), clear: vi.fn() });
  render(<AdminKnowledgePage knowledge={controller} wrapFile={(file) => ({ name: file.name, size: file.size, mediaType: file.type, read: async () => new Uint8Array([65]) })} />);
  await user.type(screen.getByLabelText('Title'), 'Company policy');
  await user.upload(screen.getByLabelText('Original file'), new File(['A'], 'policy.txt', { type: 'text/plain' }));
  fireEvent.submit(screen.getByRole('button', { name: 'Upload knowledge' }).closest('form')!);
  expect(await screen.findByRole('alert')).toHaveTextContent('Use a supported original.');
  expect(screen.getByLabelText('Title')).toHaveValue('Company policy');
  expect(screen.queryByLabelText(/company|role/iu)).not.toBeInTheDocument();
});

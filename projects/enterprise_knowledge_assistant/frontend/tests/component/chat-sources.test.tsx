/** Group chunk locations by original file while preserving downloads after history restore. */
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { ChatMessage } from '@/adapters/inbound/react/ChatMessage';
import { ChatHTTP } from '@/adapters/outbound/http/chat';
import { HttpClient } from '@/adapters/outbound/http/client';
import type { Citation, Message } from '@/domain/chat';

afterEach(cleanup);

it('groups line citations and downloads original bytes and metadata before and after history restore', async () => {
  const itemId = '7a95d29d-0a44-4bbf-bc9e-214341a8e639';
  const revisionId = '7a95d29d-0a44-4bbf-bc9e-214341a8e640';
  const path = `/api/v1/knowledge/${itemId}/source?revision_id=${revisionId}`;
  const original = 'First policy section.\r\nSecond policy section.\r\n';
  const originalBytes = new TextEncoder().encode(original);
  const dto = {
    id: '7a95d29d-0a44-4bbf-bc9e-214341a8e641',
    turn_id: '7a95d29d-0a44-4bbf-bc9e-214341a8e642',
    sequence: 2, sender: 'assistant', content: 'Company policy answer.',
    outcome: 'answer', refusal_text: null, created_at: '2026-10-21T00:00:00Z',
    citations: [1, 2].map((line) => ({
      id: `7a95d29d-0a44-4bbf-bc9e-214341a8e65${line}`,
      chunk_id: `7a95d29d-0a44-4bbf-bc9e-214341a8e66${line}`,
      item_id: itemId, revision_id: revisionId,
      locator: { kind: 'text', line_start: line, line_end: line },
      label: 'Company policy', availability: 'current', resource_url: path,
    })),
  };
  const fetcher = vi.fn<typeof fetch>(async (input) => {
    if (String(input).includes('/chat/messages')) return new Response(JSON.stringify({ messages: [dto], last_sequence: 2, next_cursor: null }));
    expect(String(input)).toBe(path);
    return new Response(original, { headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Content-Disposition': 'attachment; filename="policy.txt"' } });
  });
  const chat = new ChatHTTP(new HttpClient(fetcher, 'http://localhost'));
  const onOpen = vi.fn(async (citation: Citation) => {
    const file = await chat.readSource(citation);
    expect(file.name).toBe('policy.txt');
    expect(file.mediaType).toBe('text/plain');
    expect(file.size).toBe(originalBytes.length);
    expect(Array.from(await file.read())).toEqual(Array.from(originalBytes));
  });
  const user = userEvent.setup();
  for (let restore = 0; restore < 2; restore += 1) {
    const history = await chat.history();
    const view = render(<ChatMessage message={history.messages[0]} onOpen={onOpen} onRetry={vi.fn()} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(1);
    expect(screen.getByText('Lines: 1–1, 2–2')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Download original file: Company policy' }));
    view.unmount();
  }
  expect(onOpen).toHaveBeenCalledTimes(2);
});

it('keeps files and revisions separate, deduplicates pages, and disables unavailable originals', async () => {
  const first: Citation = {
    id: 'citation-1', itemId: 'file-1', revisionId: 'revision-1', chunkId: 'chunk-1',
    label: 'Handbook', locator: { kind: 'pdf', page: 3 }, availability: 'current',
    resourceURL: '/original-handbook',
  };
  const old: Citation = { ...first, id: 'citation-4', revisionId: 'old-revision', availability: 'unavailable', resourceURL: null };
  const message: Message = {
    id: 'message', turnId: 'turn', sequence: 2, sender: 'assistant', content: 'Answer',
    outcome: 'answer', refusalText: null, createdAt: '2026-10-21T00:00:00Z',
    citations: [first, { ...first, id: 'citation-2', chunkId: 'chunk-2' }, { ...first, id: 'citation-3', chunkId: 'chunk-3', locator: { kind: 'pdf', page: 7 } }, old, { ...first, id: 'citation-5', itemId: 'file-2', label: 'Policy', locator: { kind: 'text', line_start: 8, line_end: 12 } }],
  };
  const onOpen = vi.fn().mockResolvedValue(undefined);
  render(<ChatMessage message={message} onOpen={onOpen} onRetry={vi.fn()} />);
  expect(screen.getAllByRole('listitem')).toHaveLength(3);
  expect(screen.getByText('Pages: 3, 7')).toBeVisible();
  expect(screen.getByText('Lines: 8–12')).toBeVisible();
  const handbookDownloads = screen.getAllByRole('button', { name: 'Download original file: Handbook' });
  expect(handbookDownloads[0]).toBeEnabled();
  expect(handbookDownloads[1]).toBeDisabled();
  expect(screen.getByText('Source no longer available')).toBeVisible();
  const user = userEvent.setup();
  await user.click(handbookDownloads[0]);
  await user.click(handbookDownloads[1]);
  expect(onOpen).toHaveBeenCalledExactlyOnceWith(first);
});

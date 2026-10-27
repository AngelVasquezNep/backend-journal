/** HTTP boundary tests verify account-change fences and reject untrusted source links. */
import { describe, expect, it, vi } from 'vitest';
import { HttpClient, sourceURL } from '@/adapters/outbound/http/client';

describe('source links', () => {
  it('permits exact current-revision source paths and rejects external or malformed destinations', () => {
    const id = '7a95d29d-0a44-4bbf-bc9e-214341a8e639';
    const path = `/api/v1/knowledge/${id}/source?revision_id=${id}#page=3`;
    expect(sourceURL(path, 'https://taskify.example')).toBe(path);
    expect(sourceURL(`https://evil.example${path}`, 'https://taskify.example')).toBeNull();
    expect(sourceURL('javascript:alert(1)', 'https://taskify.example')).toBeNull();
    expect(sourceURL(path.replace('#page=3', '&url=https://evil.example'), 'https://taskify.example')).toBeNull();
    expect(sourceURL(`/api/v1/knowledge/${id}/source`, 'https://taskify.example')).toBeNull();
  });
});

it('discards a completed old-account request even if the transport ignored cancellation', async () => {
  /** Capture the pending transport response so the test can complete it after an account change. */
  let complete: (value: Response) => void = () => { throw new Error('Request was not started'); };
  const fetcher = vi.fn<typeof fetch>(() => new Promise((resolve) => { complete = resolve; }));
  const client = new HttpClient(fetcher, 'https://taskify.example');
  client.setCSRF('old-account-token');
  const pending = client.request('/api/v1/chat');
  client.clearIdentity();
  complete(new Response(JSON.stringify({ private: 'old account data' }), { status: 200 }));
  await expect(pending).rejects.toMatchObject({ code: 'account_changed' });
});

it('uses cookies and an in-memory synchronizer token for authenticated mutations', async () => {
  const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response('{}', { status: 200 }));
  const client = new HttpClient(fetcher, 'https://taskify.example');
  client.setCSRF('current-csrf');
  await client.request('/api/v1/chat', { method: 'PUT', body: '{}' });
  const options = fetcher.mock.calls[0][1];
  expect(options?.credentials).toBe('same-origin');
  expect(new Headers(options?.headers).get('X-CSRF-Token')).toBe('current-csrf');
});

it('does not upload old-account file bytes after an asynchronous attachment read', async () => {
  const { KnowledgeHTTP } = await import('@/adapters/outbound/http/knowledge');
  let finish!: (bytes: Uint8Array) => void;
  const fetcher = vi.fn();
  const http = new HttpClient(fetcher, 'http://localhost');
  const upload = new KnowledgeHTTP(http).upload('Policy', { name: 'policy.txt', size: 1, mediaType: 'text/plain', read: () => new Promise((resolve) => { finish = resolve; }) });
  http.clearIdentity(); finish(new Uint8Array([65]));
  await expect(upload).rejects.toMatchObject({ code: 'account_changed' });
  expect(fetcher).not.toHaveBeenCalled();
});

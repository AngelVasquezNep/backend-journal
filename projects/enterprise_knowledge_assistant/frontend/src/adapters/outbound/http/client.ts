/** Same-origin Fetch transport with memory-only CSRF and account-change cancellation fences. */
import { ApplicationFailure, type Attachment } from '@/domain/common';

/** Decode a response object only after checking its unknown runtime representation. */
export function record(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ApplicationFailure('dependency_unavailable', 'The service returned an invalid response.', true);
  }
  return value as Record<string, unknown>;
}

/** Accept only exact same-origin Knowledge source routes with a required revision UUID. */
export function sourceURL(value: unknown, origin: string): string | null {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value, origin);
    const uuid = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';
    if (url.origin !== origin || url.username || url.password || !new RegExp(`^/api/v1/knowledge/${uuid}/source$`, 'u').test(url.pathname)) return null;
    if (url.searchParams.getAll('revision_id').length !== 1 || !new RegExp(`^${uuid}$`, 'u').test(url.searchParams.get('revision_id') ?? '')) return null;
    if ([...url.searchParams.keys()].some((key) => !['revision_id', 'download'].includes(key))) return null;
    return url.pathname + url.search + url.hash;
  } catch { return null; }
}

/** Make isolated authenticated requests; clearing identity cancels and fences every older response. */
export class HttpClient {
  onAuthenticationLost: (() => void) | null = null;
  private csrf: string | null = null;
  private generation = 0;
  private pending = new Set<AbortController>();

  /** Inject network and origin adapters; no request is sent during construction. */
  constructor(private readonly fetcher: typeof fetch, readonly origin: string) {}

  /** Retain only the current session's synchronizer token in memory. */
  setCSRF(value: string): void { this.csrf = value; }

  /** Capture an adapter-only fence before asynchronous file reading can cross an account switch. */
  get identityGeneration(): number { return this.generation; }

  /** Invalidate old-account responses before any account-specific UI cache can be repopulated. */
  clearIdentity(): void {
    this.generation += 1;
    this.csrf = null;
    for (const controller of this.pending) controller.abort();
    this.pending.clear();
  }

  /** Send a same-origin public request and return unknown data for an owning DTO decoder. */
  async request(path: string, options: RequestInit = {}, binary = false): Promise<unknown> {
    const destination = new URL(path, this.origin);
    if (!path.startsWith('/api/v1/') || !destination.pathname.startsWith('/api/v1/') || destination.origin !== this.origin) {
      throw new ApplicationFailure('invalid_request', 'This request destination is not permitted.');
    }
    const generation = this.generation;
    const controller = new AbortController();
    this.pending.add(controller);
    const headers = new Headers(options.headers);
    const method = (options.method ?? 'GET').toUpperCase();
    if (!['GET', 'HEAD'].includes(method) && this.csrf) headers.set('X-CSRF-Token', this.csrf);
    try {
      const response = await this.fetcher(path, { ...options, method, headers, signal: controller.signal, credentials: 'same-origin', cache: 'no-store', redirect: 'error' });
      if (generation !== this.generation) throw new ApplicationFailure('account_changed', 'Your account changed.');
      if (response.status === 204) return null;
      if (binary && response.ok) {
        const bytes = new Uint8Array(await response.arrayBuffer());
        if (generation !== this.generation) throw new ApplicationFailure('account_changed', 'Your account changed.');
        return { bytes, mediaType: response.headers.get('content-type')?.split(';')[0] ?? 'application/octet-stream', disposition: response.headers.get('content-disposition') ?? '' };
      }
      const value: unknown = await response.json();
      if (generation !== this.generation) throw new ApplicationFailure('account_changed', 'Your account changed.');
      if (!response.ok) {
        const error = record(value);
        const code = typeof error.code === 'string' ? error.code : 'dependency_unavailable';
        if (response.status === 401 && code === 'authentication_required') { this.clearIdentity(); this.onAuthenticationLost?.(); }
        const message = code === 'invalid_credentials' ? 'The email or password is incorrect.' : code === 'login_temporarily_unavailable' ? 'Login is temporarily paused. Please try again later.' : response.status === 401 ? 'Please log in again.' : 'The request could not be completed. Check your input and retry.';
        throw new ApplicationFailure(code, message, response.status >= 500);
      }
      return value;
    } catch (error) {
      if (error instanceof ApplicationFailure) throw error;
      throw new ApplicationFailure('dependency_unavailable', 'The service could not be reached. Please retry.', true);
    } finally { this.pending.delete(controller); }
  }

  /** Download authorized original bytes through the same session and account-change fences. */
  async binary(path: string): Promise<Uint8Array> {
    const value = record(await this.request(path, {}, true));
    if (!(value.bytes instanceof Uint8Array)) throw new ApplicationFailure('dependency_unavailable', 'The source could not be read.', true);
    return value.bytes;
  }

  /** Decode bounded original response metadata for an explicit transient source download. */
  async download(path: string): Promise<Attachment> {
    if (!sourceURL(path, this.origin)) throw new ApplicationFailure('source_unavailable', 'This source is unavailable.');
    const value = record(await this.request(path, {}, true));
    if (!(value.bytes instanceof Uint8Array) || value.bytes.length < 1 || value.bytes.length > 20_971_520 || typeof value.mediaType !== 'string' || typeof value.disposition !== 'string') throw new ApplicationFailure('dependency_unavailable', 'The source response is invalid.', true);
    const bytes = value.bytes;
    let name = 'original';
    try {
      const encoded = /filename\*=utf-8''([^;]+)/iu.exec(value.disposition)?.[1];
      name = encoded ? decodeURIComponent(encoded) : /filename="([^"\r\n]+)"/u.exec(value.disposition)?.[1] ?? name;
    } catch { name = 'original'; }
    if ([...name].length > 255 || /[/\\\p{Cc}]/u.test(name)) name = 'original';
    return { name, mediaType: value.mediaType, size: bytes.length, read: async () => bytes.slice() };
  }
}

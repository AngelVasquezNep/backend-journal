/** Decode owned Knowledge contracts and contain multipart/binary browser representations at the adapter. */
import { ApplicationFailure, type Attachment } from '@/domain/common';
import type { ItemPage, KnowledgeItem, Revision } from '@/domain/knowledge';
import type { KnowledgePort } from '@/application/ports/knowledge';
import { HttpClient, record, sourceURL } from '@/adapters/outbound/http/client';

/** Reject malformed provider data before it can enter company-resource application state. */
function invalid(): never { throw new ApplicationFailure('dependency_unavailable', 'The knowledge service returned an invalid response.', true); }

/** Require canonical UUID values instead of accepting path fragments or model-generated addresses. */
function id(value: unknown): string {
  if (typeof value !== 'string' || !/^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/u.test(value)) return invalid();
  return value;
}

/** Validate bounded text fields, retaining only public metadata. */
function text(value: unknown, maximum: number): string {
  if (typeof value !== 'string' || [...value].length < 1 || [...value].length > maximum || /\p{Cc}/u.test(value)) return invalid();
  return value;
}

/** Accept only server UTC timestamps and normalize their browser representation. */
function instant(value: unknown): string {
  if (typeof value !== 'string' || !/(?:Z|\+00:00)$/u.test(value) || !Number.isFinite(Date.parse(value))) return invalid();
  return value;
}

/** Decode immutable public revision metadata and safe processing outcomes. */
function revision(value: unknown): Revision {
  const dto = record(value);
  const state = dto.state;
  if (!['processing', 'ready', 'failed', 'superseded', 'cancelled'].includes(String(state))) return invalid();
  if (typeof dto.size_bytes !== 'number' || !Number.isInteger(dto.size_bytes) || dto.size_bytes < 1 || dto.size_bytes > 20 * 1024 * 1024) return invalid();
  const mediaType = text(dto.media_type, 150);
  if (!['text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/png', 'image/jpeg'].includes(mediaType)) return invalid();
  return { id: id(dto.id), itemId: id(dto.item_id), originalFilename: text(dto.original_filename, 255), mediaType, sizeBytes: dto.size_bytes,
    state: state as Revision['state'], errorCode: dto.error_code === null ? null : text(dto.error_code, 100),
    errorMessage: dto.error_message === null ? null : text(dto.error_message, 500), createdAt: instant(dto.created_at), readyAt: dto.ready_at === null ? null : instant(dto.ready_at) };
}

/** Decode an item only when its pointers identify revisions belonging to that same item. */
function item(value: unknown): KnowledgeItem {
  const dto = record(value);
  const itemId = id(dto.id);
  if (typeof dto.version !== 'number' || !Number.isSafeInteger(dto.version) || dto.version < 1) return invalid();
  if (!['processing', 'ready', 'failed'].includes(String(dto.availability))) return invalid();
  const currentRevision = dto.current_revision === null ? null : revision(dto.current_revision);
  const candidateRevision = dto.candidate_revision === null ? null : revision(dto.candidate_revision);
  if ([currentRevision, candidateRevision].some((entry) => entry && entry.itemId !== itemId)) return invalid();
  if (currentRevision && currentRevision.state !== 'ready') return invalid();
  return { id: itemId, title: text(dto.title, 200), version: dto.version, availability: dto.availability as KnowledgeItem['availability'], currentRevision, candidateRevision, createdAt: instant(dto.created_at), updatedAt: instant(dto.updated_at) };
}

/** Implement authenticated company-resource operations with no client-supplied ownership. */
export class KnowledgeHTTP implements KnowledgePort {
  /** Reuse the memory-only session transport selected by the composition root. */
  constructor(private readonly http: HttpClient) {}

  /** Decode one server-filtered page and its opaque continuation cursor. */
  async list(cursor?: string, limit = 50): Promise<ItemPage> {
    const query = new URLSearchParams({ limit: String(limit) });
    if (cursor) query.set('cursor', cursor);
    const dto = record(await this.http.request(`/api/v1/knowledge?${query}`));
    if (!Array.isArray(dto.items) || dto.items.length > 100) return invalid();
    return { items: dto.items.map(item), nextCursor: dto.next_cursor === null ? null : text(dto.next_cursor, 2048) };
  }

  /** Read current metadata without refreshing the session inactivity deadline. */
  async readItem(value: string): Promise<KnowledgeItem> { return item(await this.http.request(`/api/v1/knowledge/${id(value)}`)); }

  /** Adapt domain attachment bytes to multipart and retain the original filename and media type. */
  async upload(title: string, attachment: Attachment): Promise<KnowledgeItem> {
    const generation = this.http.identityGeneration;
    const form = new FormData();
    form.set('title', title);
    const copy = new Uint8Array(await attachment.read());
    if (generation !== this.http.identityGeneration) throw new ApplicationFailure('account_changed', 'Your account changed.');
    form.set('file', new Blob([copy.buffer], { type: attachment.mediaType }), attachment.name);
    return item(await this.http.request('/api/v1/knowledge', { method: 'POST', body: form }));
  }

  /** Poll the exact processing revision with no company/account selector. */
  async revisionStatus(itemId: string, revisionId: string): Promise<Revision> {
    const result = revision(await this.http.request(`/api/v1/knowledge/${id(itemId)}/revisions/${id(revisionId)}`));
    if (result.id !== revisionId || result.itemId !== itemId) return invalid();
    return result;
  }

  /** Read only an exact same-origin original after fresh server authorization and size checks. */
  async readOriginal(itemId: string, revision: Revision): Promise<Attachment> {
    const path = sourceURL(`/api/v1/knowledge/${id(itemId)}/source?revision_id=${id(revision.id)}&download=true`, this.http.origin);
    if (!path || revision.itemId !== itemId) return invalid();
    const bytes = await this.http.binary(path);
    if (bytes.byteLength !== revision.sizeBytes) return invalid();
    return { name: revision.originalFilename, size: bytes.byteLength, mediaType: revision.mediaType, read: async () => bytes.slice() };
  }

  /** Send the quoted current version and title only; ownership remains server-derived. */
  async rename(itemId: string, version: number, title: string): Promise<KnowledgeItem> {
    return item(await this.http.request(`/api/v1/knowledge/${id(itemId)}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', 'If-Match': `"${version}"` }, body: JSON.stringify({ title }) }));
  }

  /** Read a replacement behind an account fence, then submit exactly one file and the loaded ETag. */
  async replace(itemId: string, version: number, attachment: Attachment): Promise<KnowledgeItem> {
    const generation = this.http.identityGeneration;
    const copy = new Uint8Array(await attachment.read());
    if (generation !== this.http.identityGeneration) throw new ApplicationFailure('account_changed', 'Your account changed.');
    const form = new FormData(); form.set('file', new Blob([copy.buffer], { type: attachment.mediaType }), attachment.name);
    return item(await this.http.request(`/api/v1/knowledge/${id(itemId)}/revisions`, { method: 'POST', headers: { 'If-Match': `"${version}"` }, body: form }));
  }

  /** Delete the exact loaded version; stale admin state cannot silently remove newer information. */
  async remove(itemId: string, version: number): Promise<void> {
    await this.http.request(`/api/v1/knowledge/${id(itemId)}`, { method: 'DELETE', headers: { 'If-Match': `"${version}"` } });
  }
}

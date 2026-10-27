/** Decode private Chat DTOs strictly before exposing saved messages or server-authorized source addresses. */
import { ApplicationFailure, type Attachment } from '@/domain/common';
import type { Citation, Conversation, Message, MessagePage, Outcome, Turn } from '@/domain/chat';
import type { ChatPort } from '@/application/ports/chat';
import { HttpClient, record, sourceURL } from '@/adapters/outbound/http/client';

/** Reject malformed dependencies without rendering private provider diagnostics as chat content. */
function invalid(): never { throw new ApplicationFailure('dependency_unavailable', 'The conversation response is invalid.', true); }

/** Require canonical UUIDs for every saved resource and server-built route. */
function uuid(value: unknown): string { if (typeof value !== 'string' || !/^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/u.test(value)) return invalid(); return value; }

/** Require safe numeric sequences rather than coercing strings or booleans. */
function integer(value: unknown, minimum = 0): number { if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < minimum) return invalid(); return value; }

/** Validate bounded nonempty display strings while preserving escaped plain message content. */
function text(value: unknown, maximum = 16000): string { if (typeof value !== 'string' || !value.trim() || [...value].length > maximum) return invalid(); return value; }

/** Require an aware UTC timestamp before admitting a saved message. */
function instant(value: unknown): string { const result = text(value, 50); if (!/(?:Z|\+00:00)$/u.test(result) || !Number.isFinite(Date.parse(result))) return invalid(); return result; }

/** Validate the public locator union without introducing browser/framework values into the domain. */
function locator(value: unknown): Readonly<Record<string, unknown>> {
  const dto = record(value);
  /** Require integer source positions without coercing strings or booleans. */
  const nonnegative = (entry: unknown) => typeof entry === 'number' && Number.isInteger(entry) && entry >= 0;
  if (dto.kind === 'pdf') { if (!nonnegative(dto.page) || Number(dto.page) < 1 || (dto.text_start !== undefined && !nonnegative(dto.text_start)) || (dto.text_end !== undefined && !nonnegative(dto.text_end)) || (typeof dto.text_start === 'number' && typeof dto.text_end === 'number' && dto.text_end < dto.text_start)) return invalid(); }
  else if (dto.kind === 'text') { if (!nonnegative(dto.line_start) || Number(dto.line_start) < 1 || !nonnegative(dto.line_end) || Number(dto.line_end) < Number(dto.line_start)) return invalid(); }
  else if (dto.kind === 'docx') { if (!Array.isArray(dto.heading_path) || dto.heading_path.some((entry) => typeof entry !== 'string') || !nonnegative(dto.block) || ['table', 'row', 'cell'].some((key) => dto[key] !== undefined && !nonnegative(dto[key]))) return invalid(); }
  else if (dto.kind === 'image') { if (dto.page !== 1) return invalid(); if (dto.bbox !== undefined) { const box = dto.bbox; if (!Array.isArray(box) || box.length !== 4 || box.some((entry) => typeof entry !== 'number' || !Number.isFinite(entry)) || box[0] < 0 || box[1] < 0 || box[2] <= 0 || box[3] <= 0 || box[0] + box[2] > 1 || box[1] + box[3] > 1) return invalid(); } }
  else return invalid();
  return dto;
}

/** A source link is valid only for this exact citation triple's item/revision and same origin. */
function citation(value: unknown, origin: string): Citation {
  const dto = record(value); const itemId = uuid(dto.item_id); const revisionId = uuid(dto.revision_id);
  if (!['current', 'unavailable'].includes(String(dto.availability))) return invalid();
  const url = dto.resource_url === null ? null : sourceURL(dto.resource_url, origin);
  if (dto.availability === 'current') {
    if (!url) return invalid(); const parsed = new URL(url, origin);
    if (parsed.pathname !== `/api/v1/knowledge/${itemId}/source` || parsed.searchParams.get('revision_id') !== revisionId) return invalid();
  } else if (dto.resource_url !== null) return invalid();
  return { id: uuid(dto.id), itemId, revisionId, chunkId: uuid(dto.chunk_id), locator: locator(dto.locator), label: text(dto.label, 200), availability: dto.availability as Citation['availability'], resourceURL: url };
}

/** Admit only a complete user question or one of the five saved assistant terminal outcomes. */
function message(value: unknown, origin: string): Message {
  const dto = record(value);
  if (!['user', 'assistant'].includes(String(dto.sender)) || !Array.isArray(dto.citations) || dto.citations.length > 8) return invalid();
  if (dto.sender === 'user' ? dto.outcome !== null || dto.refusal_text !== null || dto.citations.length !== 0 : !['answer', 'refusal', 'insufficient_information', 'clarification', 'failure'].includes(String(dto.outcome))) return invalid();
  const citations = dto.citations.map((entry) => citation(entry, origin));
  if (dto.outcome === 'answer' && citations.length === 0) return invalid();
  if (dto.outcome !== 'answer' && citations.length !== 0) return invalid();
  return { id: uuid(dto.id), turnId: uuid(dto.turn_id), sequence: integer(dto.sequence, 1), sender: dto.sender as Message['sender'], content: text(dto.content, dto.sender === 'user' ? 4000 : 16000), outcome: dto.outcome as Outcome | null, refusalText: dto.refusal_text === null ? null : text(dto.refusal_text, 1000), citations, createdAt: instant(dto.created_at) };
}

/** Implement own saved conversation operations through first-party cookies and memory-only CSRF. */
export class ChatHTTP implements ChatPort {
  /** Reuse one authenticated same-origin transport with account-change abort/generation fences. */
  constructor(private readonly http: HttpClient) {}

  /** Decode own conversation identity, sequence and pending turn reference after idempotent open. */
  async open(): Promise<Conversation> {
    const dto = record(await this.http.request('/api/v1/chat', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: '{}' }));
    instant(dto.created_at); instant(dto.updated_at);
    return { id: uuid(dto.id), lastSequence: integer(dto.last_sequence), activeTurnId: dto.active_turn_id === null ? null : uuid(dto.active_turn_id) };
  }

  /** Decode an ordered owner-scoped page with no fabricated/duplicate message sequences. */
  async history(cursor?: string): Promise<MessagePage> {
    const query = new URLSearchParams({ limit: '50' }); if (cursor) query.set('cursor', cursor);
    const dto = record(await this.http.request(`/api/v1/chat/messages?${query}`));
    if (!Array.isArray(dto.messages) || dto.messages.length > 100) return invalid();
    const messages = dto.messages.map((entry) => message(entry, this.http.origin));
    const lastSequence = integer(dto.last_sequence);
    if (messages.some((entry, index) => entry.sequence > lastSequence || (index > 0 && entry.sequence <= messages[index - 1].sequence)) || new Set(messages.map((entry) => entry.id)).size !== messages.length) return invalid();
    return { messages, lastSequence, nextCursor: dto.next_cursor === null ? null : text(dto.next_cursor, 512) };
  }

  /** Send an exact replay identity/content/sequence; the caller retains it if transport confirmation is lost. */
  async send(clientId: string, content: string, expectedLastSequence: number): Promise<Turn> {
    return this.turn(await this.http.request('/api/v1/chat/messages', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ client_message_id: uuid(clientId), content, expected_last_sequence: expectedLastSequence }) }));
  }

  /** Poll a server-owned route constructed from a UUID; automatic requests do not refresh idle time. */
  async poll(turnId: string): Promise<Turn> {
    const result = this.turn(await this.http.request(`/api/v1/chat/turns/${uuid(turnId)}`));
    if (result.id !== turnId) return invalid(); return result;
  }

  /** Validate terminal shape, message association and exact polling address before exposing a turn. */
  private turn(value: unknown): Turn {
    const dto = record(value); const id = uuid(dto.id);
    if (!['queued', 'running', 'completed', 'failed'].includes(String(dto.state)) || typeof dto.retryable !== 'boolean' || dto.poll_url !== `/api/v1/chat/turns/${id}`) return invalid();
    const userMessage = message(dto.user_message, this.http.origin);
    const assistantMessage = dto.assistant_message === null ? null : message(dto.assistant_message, this.http.origin);
    if (userMessage.sender !== 'user' || userMessage.turnId !== id || (assistantMessage && (assistantMessage.sender !== 'assistant' || assistantMessage.turnId !== id || assistantMessage.sequence !== userMessage.sequence + 1)) || (['completed', 'failed'].includes(String(dto.state)) !== (assistantMessage !== null)) || (dto.state === 'failed' && assistantMessage?.outcome !== 'failure')) return invalid();
    return { id, state: dto.state as Turn['state'], userMessage, assistantMessage, errorCode: dto.error_code === null ? null : text(dto.error_code, 100), retryable: dto.retryable };
  }

  /** Recheck login/company/current revision immediately before downloading the original cited bytes. */
  async readSource(citation: Citation): Promise<Attachment> {
    const path = citation.resourceURL && sourceURL(citation.resourceURL, this.http.origin);
    if (!path || citation.availability !== 'current') throw new ApplicationFailure('source_unavailable', 'This source is unavailable.');
    return this.http.download(path);
  }
}

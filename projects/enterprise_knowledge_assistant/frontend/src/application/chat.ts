/** Framework-free saved-chat controller retains only transient account-bound state and fences all async results. */
import { ApplicationFailure } from '@/domain/common';
import { question, type Citation, type Message, type Turn } from '@/domain/chat';
import type { ChatPort } from '@/application/ports/chat';
import type { Clock, IdGenerator } from '@/application/ports/common';
import type { AttachmentViewer } from '@/application/ports/knowledge';

export interface ChatState {
  readonly messages: readonly Message[];
  readonly pending: Turn | null;
  readonly lastSequence: number;
  readonly nextCursor: string | null;
  readonly loading: boolean;
  readonly sending: boolean;
  readonly error: string | null;
  readonly canRetryNetwork: boolean;
}

/** Presentation depends on this owned use-case contract, not an HTTP client or browser storage. */
export interface ChatPresentation {
  readonly current: ChatState;
  /** Observe new immutable snapshots for the current account. */
  subscribe(listener: () => void): () => void;
  /** Restore history and any active accepted turn. */
  open(): Promise<void>;
  /** Accept one new deliberate question with a fresh client UUID. */
  send(content: string): Promise<void>;
  /** Replay an unconfirmed send or resume an interrupted poll without creating a duplicate question. */
  retryNetwork(): Promise<void>;
  /** Load an older own-history page. */
  more(): Promise<void>;
  /** Download a fresh authorized exact citation original. */
  openSource(citation: Citation): Promise<void>;
}

/** Restore and coordinate the one saved conversation; nothing is persisted in the browser. */
export class ChatController implements ChatPresentation {
  current: ChatState = { messages: [], pending: null, lastSequence: 0, nextCursor: null, loading: false, sending: false, error: null, canRetryNetwork: false };
  private generation = 0;
  private listeners = new Set<() => void>();
  private opening: Promise<void> | null = null;
  private watching: string | null = null;
  private submission: { clientId: string; content: string; expectedLastSequence: number } | null = null;

  /** Inject owned HTTP/runtime/source adapters without coupling core to React or Fetch. */
  constructor(private readonly port: ChatPort, private readonly clock: Clock, private readonly ids: IdGenerator, private readonly viewer: AttachmentViewer) {}

  /** Subscribe without retaining an account or framework reference after unmount. */
  subscribe(listener: () => void): () => void { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; }

  /** Publish a new immutable state reference suitable for external-store subscriptions. */
  private update(patch: Partial<ChatState>): void { this.current = { ...this.current, ...patch }; for (const listener of this.listeners) listener(); }

  /** Discard every private history, pending request and source URL before another account is published. */
  clear(): void {
    this.generation += 1; this.submission = null; this.watching = null; this.opening = null; this.viewer.clear();
    this.update({ messages: [], pending: null, lastSequence: 0, nextCursor: null, loading: false, sending: false, error: null, canRetryNetwork: false });
  }

  /** Prevent old-account asynchronous operations from publishing results or retry state. */
  private currentGeneration(generation: number): void { if (generation !== this.generation) throw new ApplicationFailure('account_changed', 'Your account changed.'); }

  /** Merge only committed messages by identity, retaining the full loaded chronological history. */
  private merge(messages: readonly Message[]): void {
    const unique = new Map(this.current.messages.map((value) => [value.id, value]));
    for (const value of messages) unique.set(value.id, value);
    this.update({ messages: [...unique.values()].sort((left, right) => left.sequence - right.sequence) });
  }

  /** Share concurrent restore calls so StrictMode cannot duplicate or fence its own recovery. */
  async open(): Promise<void> {
    if (this.opening) return this.opening;
    const operation = this.restore(); this.opening = operation;
    try { await operation; } finally { if (this.opening === operation) this.opening = null; }
  }

  /** Restore newest saved history and resume its active turn without starting another conversation. */
  private async restore(): Promise<void> {
    const generation = this.generation;
    this.update({ loading: true, error: null });
    try {
      const conversation = await this.port.open();
      const page = await this.port.history(); this.currentGeneration(generation);
      this.update({ messages: page.messages, nextCursor: page.nextCursor, lastSequence: page.lastSequence, loading: false });
      if (conversation.activeTurnId) { const turn = await this.port.poll(conversation.activeTurnId); this.currentGeneration(generation); this.accept(turn); void this.watch(turn, generation); }
    } catch (error) {
      if (generation === this.generation) this.update({ loading: false, error: 'Your conversation could not be loaded. Reload to retry.' });
      throw error;
    }
  }

  /** Accept one deliberate question; preserve its UUID/content if the HTTP result is lost. */
  async send(value: string): Promise<void> {
    if (this.current.pending || this.current.sending || this.submission) throw new ApplicationFailure('turn_in_progress', 'Finish the current question or retry its unconfirmed send.');
    this.submission = { clientId: this.ids.newId(), content: question(value), expectedLastSequence: this.current.lastSequence };
    await this.dispatch();
  }

  /** Replay exactly the same unconfirmed acceptance or resume polling of the already accepted turn. */
  async retryNetwork(): Promise<void> {
    if (this.submission) await this.dispatch();
    else if (this.current.pending) await this.watch(this.current.pending, this.generation);
    else await this.open();
  }

  /** Send an acceptance once; safe transport errors retain the original idempotency identity. */
  private async dispatch(): Promise<void> {
    const generation = this.generation;
    const submission = this.submission;
    if (!submission || this.current.sending) return;
    this.update({ sending: true, error: null, canRetryNetwork: false });
    try {
      const turn = await this.port.send(submission.clientId, submission.content, submission.expectedLastSequence);
      this.currentGeneration(generation); this.submission = null; this.accept(turn); void this.watch(turn, generation);
    } catch (error) {
      if (generation === this.generation) {
        const retryable = error instanceof ApplicationFailure && error.retryable;
        if (!retryable) this.submission = null;
        this.update({ error: retryable ? 'Sending could not be confirmed. Retry the same send safely.' : error instanceof ApplicationFailure ? error.message : 'This question could not be accepted. Reload and retry.', canRetryNetwork: retryable });
      }
      throw error;
    } finally { if (generation === this.generation) this.update({ sending: false }); }
  }

  /** Expose only saved user/terminal data; an accepted processing state contains no draft tokens. */
  private accept(turn: Turn): void {
    const messages = [turn.userMessage, ...(turn.assistantMessage ? [turn.assistantMessage] : [])];
    this.merge(messages);
    this.update({ pending: turn.state === 'queued' || turn.state === 'running' ? turn : null, lastSequence: Math.max(this.current.lastSequence, ...messages.map((value) => value.sequence)), error: null, canRetryNetwork: false });
  }

  /** Poll every second through the nonrefreshing server route and fence every account-bound result. */
  private async watch(turn: Turn, generation: number): Promise<void> {
    if (!['queued', 'running'].includes(turn.state) || this.watching === turn.id) return;
    this.watching = turn.id;
    try {
      let current = turn;
      while (['queued', 'running'].includes(current.state)) {
        await this.clock.sleep(1000); this.currentGeneration(generation);
        current = await this.port.poll(turn.id); this.currentGeneration(generation); this.accept(current);
      }
    } catch {
      if (generation === this.generation) this.update({ error: 'Answer status could not be refreshed. Resume checking when connected.', canRetryNetwork: true });
    } finally { if (generation === this.generation && this.watching === turn.id) this.watching = null; }
  }

  /** Append older saved messages while retaining the latest sequence for future acceptance. */
  async more(): Promise<void> {
    const generation = this.generation;
    if (!this.current.nextCursor) return;
    try { const page = await this.port.history(this.current.nextCursor); this.currentGeneration(generation); this.merge(page.messages); this.update({ nextCursor: page.nextCursor, lastSequence: Math.max(this.current.lastSequence, page.lastSequence) }); }
    catch { if (generation === this.generation) this.update({ error: 'Older messages could not be loaded. Please retry.' }); }
  }

  /** Reauthorize a cited original immediately on demand, retaining saved answer text if it changed. */
  async openSource(citation: Citation): Promise<void> {
    const generation = this.generation;
    if (citation.availability !== 'current' || !citation.resourceURL) { this.update({ error: 'This historical source is no longer available.' }); return; }
    try { const original = await this.port.readSource(citation); this.currentGeneration(generation); await this.viewer.open(original); }
    catch { if (generation === this.generation) this.update({ error: 'This source is unavailable or your session has expired. Refresh and retry.' }); }
  }
}

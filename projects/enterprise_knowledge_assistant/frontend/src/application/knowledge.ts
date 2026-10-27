/** Framework-free knowledge use cases preserve ready content and fence old-account polling/results. */
import { ApplicationFailure, type Attachment } from '@/domain/common';
import { attachment, title, type ItemPage, type KnowledgeItem } from '@/domain/knowledge';
import type { Clock } from '@/application/ports/common';
import type { AttachmentViewer, KnowledgePort } from '@/application/ports/knowledge';

/** Coordinate resource reads, durable upload and status polling through injected owned ports. */
export class KnowledgeController {
  private generation = 0;
  private watching = new Map<string, number>();

  /** Inject network, clock and source viewing while keeping all browser objects outside core. */
  constructor(private readonly port: KnowledgePort, private readonly clock: Clock, private readonly viewer: AttachmentViewer) {}

  /** Cancel old-account application results and pending source views without persisting any resource data. */
  clear(): void { this.generation += 1; this.watching.clear(); this.viewer.clear(); }

  /** Require that an asynchronous result still belongs to the currently authenticated account. */
  private current(generation: number): void {
    if (generation !== this.generation) throw new ApplicationFailure('account_changed', 'Your account changed.');
  }

  /** Load a visible company page; its authority is always the server's online session. */
  async list(cursor?: string): Promise<ItemPage> {
    const generation = this.generation;
    const page = await this.port.list(cursor);
    this.current(generation);
    return page;
  }

  /** Validate title/file bounds and preserve previously valid information after any rejection. */
  async upload(value: string, file: Attachment): Promise<KnowledgeItem> {
    const generation = this.generation;
    const item = await this.port.upload(title(value), attachment(file));
    this.current(generation);
    return item;
  }

  /** Poll one durable candidate each second and hydrate fresh pointers/title/version only at a terminal status. */
  async watch(item: KnowledgeItem, update: (item: KnowledgeItem) => void): Promise<void> {
    if (item.candidateRevision?.state !== 'processing' || this.watching.has(item.id)) return;
    const generation = this.generation;
    this.watching.set(item.id, generation);
    try {
      while (generation === this.generation) {
        await this.clock.sleep(1000);
        this.current(generation);
        const revision = await this.port.revisionStatus(item.id, item.candidateRevision.id);
        this.current(generation);
        if (revision.state !== 'processing') {
          const current = await this.port.readItem(item.id);
          this.current(generation);
          update(current);
          return;
        }
      }
    } finally { if (this.watching.get(item.id) === generation) this.watching.delete(item.id); }
  }

  /** Open only exact current original bytes and reject stale/expired/old-account source responses. */
  async openSource(item: KnowledgeItem): Promise<void> {
    const generation = this.generation;
    if (item.availability !== 'ready' || !item.currentRevision) throw new ApplicationFailure('source_unavailable', 'This source is not available.');
    const original = await this.port.readOriginal(item.id, item.currentRevision);
    this.current(generation);
    await this.viewer.open(original);
  }

  /** Reload authoritative metadata after a conflict, preserving old data until the read succeeds. */
  async reload(id: string): Promise<KnowledgeItem> {
    const generation = this.generation;
    const item = await this.port.readItem(id); this.current(generation); return item;
  }

  /** Rename the exact item version without dropping a valid original or an active candidate. */
  async rename(item: KnowledgeItem, value: string): Promise<KnowledgeItem> {
    const generation = this.generation;
    const updated = await this.port.rename(item.id, item.version, title(value)); this.current(generation); return updated;
  }

  /** Accept a bounded replacement; account changes fence the file before sending and its result afterward. */
  async replace(item: KnowledgeItem, file: Attachment): Promise<KnowledgeItem> {
    const generation = this.generation;
    const updated = await this.port.replace(item.id, item.version, attachment(file)); this.current(generation); return updated;
  }

  /** Remove only after the inbound form's explicit confirmation, using the latest loaded item version. */
  async remove(item: KnowledgeItem): Promise<void> {
    const generation = this.generation;
    await this.port.remove(item.id, item.version); this.current(generation);
  }
}

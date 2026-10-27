/** Knowledge operations expose domain items and binary attachments, never File/Response/FormData. */
import type { Attachment } from '@/domain/common';
import type { ItemPage, KnowledgeItem, Revision } from '@/domain/knowledge';

export interface KnowledgePort {
  /** List own-company visible resources with an opaque owner-scoped cursor. */
  list(cursor?: string, limit?: number): Promise<ItemPage>;
  /** Read exact owned current/candidate metadata and its concurrency version. */
  readItem(id: string): Promise<KnowledgeItem>;
  /** Accept a validated original and return its durable processing outcome. */
  upload(title: string, attachment: Attachment): Promise<KnowledgeItem>;
  /** Poll an admin's exact candidate status without refreshing session inactivity. */
  revisionStatus(itemId: string, revisionId: string): Promise<Revision>;
  /** Read current exact-revision bytes after server authorization; unavailable sources raise typed errors. */
  readOriginal(itemId: string, revision: Revision): Promise<Attachment>;
  /** Rename only the current version; stale edits require an explicit reload. */
  rename(itemId: string, version: number, title: string): Promise<KnowledgeItem>;
  /** Accept one immutable replacement candidate while retaining a valid current original. */
  replace(itemId: string, version: number, attachment: Attachment): Promise<KnowledgeItem>;
  /** Remove current visibility immediately and cancel a processing candidate under exact version CAS. */
  remove(itemId: string, version: number): Promise<void>;
}

export interface AttachmentViewer {
  /** Open/download user-requested bytes without retaining credentials or a browser transcript. */
  open(attachment: Attachment): Promise<void>;
  /** Discard pending/private object URLs when the authenticated account changes. */
  clear(): void;
}

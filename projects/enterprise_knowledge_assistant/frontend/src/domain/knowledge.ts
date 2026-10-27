/** Company knowledge values expose current/candidate outcomes without storage or embedding details. */
import { ApplicationFailure, type Attachment } from '@/domain/common';

export interface Revision {
  readonly id: string;
  readonly itemId: string;
  readonly originalFilename: string;
  readonly mediaType: string;
  readonly sizeBytes: number;
  readonly state: 'processing' | 'ready' | 'failed' | 'superseded' | 'cancelled';
  readonly errorCode: string | null;
  readonly errorMessage: string | null;
  readonly createdAt: string;
  readonly readyAt: string | null;
}

export interface KnowledgeItem {
  readonly id: string;
  readonly title: string;
  readonly version: number;
  readonly availability: 'processing' | 'ready' | 'failed';
  readonly currentRevision: Revision | null;
  readonly candidateRevision: Revision | null;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export interface ItemPage {
  readonly items: readonly KnowledgeItem[];
  readonly nextCursor: string | null;
}

/** Validate the title's Unicode code-point bound and forbid control characters before upload. */
export function title(value: string): string {
  const normalized = value.trim();
  if (Array.from(normalized).length < 1 || Array.from(normalized).length > 200 || /\p{Cc}/u.test(value)) {
    throw new ApplicationFailure('validation_failed', 'Titles must contain 1–200 characters and no controls.');
  }
  return normalized;
}

/** Check binary size/name early; authoritative format inspection stays on the receiving server. */
export function attachment(value: Attachment): Attachment {
  if (!Number.isInteger(value.size) || value.size < 1 || value.size > 20_971_520) {
    throw new ApplicationFailure('validation_failed', 'Files must contain 1 byte through 20 MiB.');
  }
  if (Array.from(value.name).length < 1 || Array.from(value.name).length > 255 || /[/\\\p{Cc}]/u.test(value.name)) {
    throw new ApplicationFailure('validation_failed', 'Use a filename of 1–255 characters without path separators or controls.');
  }
  return value;
}

/** Saved chat values distinguish durable user acceptance, processing and five terminal outcomes. */
import { ApplicationFailure } from '@/domain/common';

export type Outcome = 'answer' | 'refusal' | 'insufficient_information' | 'clarification' | 'failure';

export interface Citation {
  readonly id: string;
  readonly itemId: string;
  readonly revisionId: string;
  readonly chunkId: string;
  readonly locator: Readonly<Record<string, unknown>>;
  readonly label: string;
  readonly availability: 'current' | 'unavailable';
  readonly resourceURL: string | null;
}

export interface Message {
  readonly id: string;
  readonly turnId: string;
  readonly sequence: number;
  readonly sender: 'user' | 'assistant';
  readonly content: string;
  readonly outcome: Outcome | null;
  readonly refusalText: string | null;
  readonly citations: readonly Citation[];
  readonly createdAt: string;
}

export interface Conversation {
  readonly id: string;
  readonly lastSequence: number;
  readonly activeTurnId: string | null;
}

export interface MessagePage {
  readonly messages: readonly Message[];
  readonly nextCursor: string | null;
  readonly lastSequence: number;
}

export interface Turn {
  readonly id: string;
  readonly state: 'queued' | 'running' | 'completed' | 'failed';
  readonly userMessage: Message;
  readonly assistantMessage: Message | null;
  readonly errorCode: string | null;
  readonly retryable: boolean;
}

/** Validate a trimmed Unicode question without truncation or HTML interpretation. */
export function question(value: string): string {
  const content = value.trim();
  if ([...content].length < 1 || [...content].length > 4000) throw new ApplicationFailure('validation_failed', 'Questions must contain 1–4000 characters.');
  return content;
}

/** The Chat port exposes only own saved history/turns and never browser/company/model authority. */
import type { Attachment } from '@/domain/common';
import type { Conversation, MessagePage, Turn, Citation } from '@/domain/chat';

export interface ChatPort {
  /** Open the same saved private conversation, creating it atomically only when absent. */
  open(): Promise<Conversation>;
  /** Read newest or older own history with the server-issued opaque cursor. */
  history(cursor?: string): Promise<MessagePage>;
  /** Replays reuse this UUID and original sequence/content; deliberate retries generate a new UUID. */
  send(clientId: string, content: string, expectedLastSequence: number): Promise<Turn>;
  /** Poll the exact owned durable turn without refreshing session inactivity. */
  poll(turnId: string): Promise<Turn>;
  /** Read an exact current citation original with fresh server authorization. */
  readSource(citation: Citation): Promise<Attachment>;
}

/** Saved messages render escaped text and separate terminal outcomes; drafts are never shown. */
import type { Citation, Message } from '@/domain/chat';
import { SourceReference } from '@/adapters/inbound/react/SourceReference';

/** Present only saved user/assistant text, explicit refusal parts and verified server source references. */
export function ChatMessage({ message, onOpen, onRetry }: { message: Message; onOpen: (citation: Citation) => Promise<void>; onRetry: () => void }) {
  const labels = { answer: 'Company answer', refusal: 'Outside company-information scope', insufficient_information: 'Insufficient company information', clarification: 'Clarification needed', failure: 'Answer could not be completed' };
  return <article aria-label={message.sender === 'user' ? 'Your question' : 'Assistant response'}>
    <h3>{message.sender === 'user' ? 'You' : message.outcome ? labels[message.outcome] : 'Assistant'}</h3>
    <p className="message-content">{message.content}</p>{message.refusalText && <p>{message.refusalText}</p>}
    {message.citations.length > 0 && <ul aria-label="Supporting sources">{message.citations.map((citation) => <SourceReference key={citation.id} citation={citation} onOpen={onOpen} />)}</ul>}
    {message.outcome === 'failure' && <button onClick={onRetry}>Retry question</button>}
  </article>;
}

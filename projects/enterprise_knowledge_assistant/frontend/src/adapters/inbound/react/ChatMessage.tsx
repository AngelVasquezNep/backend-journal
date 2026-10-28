/** Saved messages render escaped text and separate terminal outcomes; drafts are never shown. */
import type { Citation, Message } from '@/domain/chat';
import { SourceReference } from '@/adapters/inbound/react/SourceReference';
import { BrandMark, Icon } from '@/adapters/inbound/react/UI';

/** Present only saved user/assistant text, explicit refusal parts and verified server source references. */
export function ChatMessage({ message, onOpen, onRetry }: { message: Message; onOpen: (citation: Citation) => Promise<void>; onRetry: () => void }) {
  const labels = { answer: 'Company answer', refusal: 'Outside company-information scope', insufficient_information: 'Insufficient company information', clarification: 'Clarification needed', failure: 'Answer could not be completed' };
  const sources = new Map<string, Citation[]>();
  for (const citation of message.citations) {
    const key = `${citation.itemId}:${citation.revisionId}`;
    const group = sources.get(key);
    if (group) group.push(citation); else sources.set(key, [citation]);
  }
  return <article className={`chat-message chat-message--${message.sender}`} aria-label={message.sender === 'user' ? 'Your question' : 'Assistant response'}>
    <div className="message-avatar">{message.sender === 'user' ? <Icon name="user" /> : <BrandMark />}</div><div className="message-body"><header className="message-header"><h3>{message.sender === 'user' ? 'You' : message.outcome ? labels[message.outcome] : 'Assistant'}</h3><time dateTime={message.createdAt}>{new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></header>
    <p className="message-content">{message.content}</p>{message.refusalText && <p>{message.refusalText}</p>}
    {sources.size > 0 && <div className="message-sources"><span><Icon name="check" />From your company knowledge</span><ul aria-label="Supporting sources">{Array.from(sources, ([key, citations]) => <SourceReference key={key} citations={citations} onOpen={onOpen} />)}</ul></div>}
    {message.outcome === 'failure' && <button className="button-secondary" onClick={onRetry}>Retry question</button>}</div>
  </article>;
}

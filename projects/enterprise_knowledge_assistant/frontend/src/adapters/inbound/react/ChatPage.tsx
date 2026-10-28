/** The one saved private chat restores committed history and pending turns without browser persistence. */
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import type { ChatPresentation } from '@/application/chat';
import { ChatMessage } from '@/adapters/inbound/react/ChatMessage';
import { BrandMark, Icon, PageHeading } from '@/adapters/inbound/react/UI';

/** Render accessible own history/composer with five outcomes, safe retries and no unverified streaming. */
export function ChatPage({ chat }: { chat: ChatPresentation }) {
  const state = useSyncExternalStore((listener) => chat.subscribe(listener), () => chat.current);
  const [question, setQuestion] = useState('');
  const [inputError, setInputError] = useState('');
  const composer = useRef<HTMLTextAreaElement>(null);
  const log = useRef<HTMLDivElement>(null);
  const followLatest = useRef(true);
  const latestMessage = state.messages.at(-1)?.id;
  useEffect(() => { void chat.open().catch(() => undefined); }, [chat]);
  useEffect(() => { if (log.current && followLatest.current) log.current.scrollTop = log.current.scrollHeight; }, [latestMessage, state.pending?.id]);
  useEffect(() => { if (composer.current) { composer.current.style.height = 'auto'; composer.current.style.height = `${Math.min(composer.current.scrollHeight, 160)}px`; } }, [question]);
  /** Accept a deliberate question once; preserve text after a rejection or unconfirmed transport result. */
  async function send(value = question) {
    if (!value.trim()) return;
    followLatest.current = true;
    setInputError('');
    try { await chat.send(value); setQuestion(''); }
    catch (error) { setInputError(error instanceof Error ? error.message : 'This question could not be accepted.'); }
  }
  const busy = state.loading || state.sending || state.pending !== null || state.canRetryNetwork;
  const suggestions = [
    { icon: 'file' as const, title: 'Understand a policy', question: 'What does our company policy say about annual leave?' },
    { icon: 'user' as const, title: 'Get up to speed', question: 'What should a new team member know about our company?' },
    { icon: 'settings' as const, title: 'Find a process', question: 'How do I submit an expense reimbursement?' },
  ];
  return <section className={`chat-page ${state.messages.length ? 'has-messages' : ''}`}>
    <PageHeading title="Company chat" description="A conversation with your company’s knowledge." action={<span className="saved-label"><Icon name="check" />Saved for you</span>} />
    {state.loading && <div className="loading-state" role="status"><span className="loading-ring" />Loading your conversation…</div>}
    {!state.loading && state.messages.length === 0 && !state.error && <div className="chat-welcome"><div className="welcome-emblem"><span className="emblem-page emblem-page--one"><Icon name="file" /></span><BrandMark /><span className="emblem-page emblem-page--two"><Icon name="file" /></span></div>
    <div className="suggestions">{suggestions.map((suggestion) => <button className="suggestion" key={suggestion.title} disabled={busy} onClick={() => { setQuestion(suggestion.question); composer.current?.focus(); }}><span className="suggestion-icon"><Icon name={suggestion.icon} /></span><strong>{suggestion.title}</strong><span>{suggestion.question}</span><Icon name="plus" className="suggestion-add" /></button>)}</div></div>}
    <div ref={log} className="chat-log" role="log" aria-label="Saved conversation" aria-live="polite" aria-busy={state.loading} onScroll={(event) => { const view = event.currentTarget; followLatest.current = view.scrollHeight - view.scrollTop - view.clientHeight < 80; }}>{state.nextCursor && <button className="button-secondary older-messages" onClick={() => { void chat.more(); }}>Load older messages</button>}{state.messages.map((message) => <ChatMessage key={message.id} message={message} onOpen={(citation) => chat.openSource(citation)} onRetry={() => {
      const original = state.messages.find((entry) => entry.turnId === message.turnId && entry.sender === 'user');
      if (original) void send(original.content);
    }} />)}{state.pending && <div className="answer-pending" role="status"><BrandMark /><span><strong>Finding it in your company’s knowledge</strong><span>Your question is saved. Preparing a verified answer…</span></span><span className="thinking-dots" aria-hidden="true"><i /><i /><i /></span></div>}</div>
    <div className="composer-area">
      {(state.error || inputError) && <p role="alert">{state.error ?? inputError}</p>}
      {state.canRetryNetwork && <button className="button-secondary" onClick={() => { void chat.retryNetwork().catch(() => undefined); }}>Resume safely</button>}
      {!state.loading && state.error && !state.canRetryNetwork && <button className="button-secondary" onClick={() => { void chat.open().catch(() => undefined); }}>Reload conversation</button>}
      <form className="chat-composer" onSubmit={(event) => { event.preventDefault(); void send(); }}>
        <label className="sr-only" htmlFor="chat-question">Question</label><textarea ref={composer} rows={2} id="chat-question" placeholder="Ask anything about your company…" value={question} onChange={(event) => { setQuestion(event.target.value); }} disabled={busy} required aria-describedby="question-help" onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && !busy) { event.preventDefault(); void send(); } }} />
        <div className="composer-toolbar"><span><Icon name="library" />Company knowledge</span><div><span className={`character-count ${Array.from(question).length > 4000 ? 'over-limit' : ''}`}>{question.length > 3500 ? `${Array.from(question).length} / 4000` : <><kbd>↵</kbd> to send</>}</span><button className="send-button" type="submit" aria-label={state.sending ? 'Saving question…' : 'Send question'} title="Send question" disabled={busy || !question.trim() || Array.from(question).length > 4000}><Icon name="arrow" /></button></div></div>
      </form>
      <p id="question-help" className="composer-help"><Icon name="lock" /><span>Only you can see this conversation. Answers use ready company sources.<span className="sr-only"> Ask a company question in 1–4000 characters. Enter sends; Shift+Enter adds a line.</span></span></p>
    </div>
  </section>;
}

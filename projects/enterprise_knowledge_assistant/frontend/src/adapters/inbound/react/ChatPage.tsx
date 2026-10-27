/** The one saved private chat restores committed history and pending turns without browser persistence. */
import { useEffect, useState, useSyncExternalStore } from 'react';
import type { ChatPresentation } from '@/application/chat';
import { ChatMessage } from '@/adapters/inbound/react/ChatMessage';

/** Render accessible own history/composer with five outcomes, safe retries and no unverified streaming. */
export function ChatPage({ chat }: { chat: ChatPresentation }) {
  const state = useSyncExternalStore((listener) => chat.subscribe(listener), () => chat.current);
  const [question, setQuestion] = useState('');
  const [inputError, setInputError] = useState('');
  useEffect(() => { void chat.open().catch(() => undefined); }, [chat]);
  /** Accept a deliberate question once; preserve text after a rejection or unconfirmed transport result. */
  async function send(value = question) {
    setInputError('');
    try { await chat.send(value); setQuestion(''); }
    catch (error) { setInputError(error instanceof Error ? error.message : 'This question could not be accepted.'); }
  }
  const busy = state.loading || state.sending || state.pending !== null || state.canRetryNetwork;
  return <section><h2>Your saved company chat</h2><p>This conversation is private to your account. Answers use current ready company information.</p>
    {state.loading && <p role="status">Loading your conversation…</p>}
    {state.nextCursor && <button onClick={() => { void chat.more(); }}>Load older messages</button>}
    <div role="log" aria-label="Saved conversation" aria-live="polite">{state.messages.map((message) => <ChatMessage key={message.id} message={message} onOpen={(citation) => chat.openSource(citation)} onRetry={() => {
      const original = state.messages.find((entry) => entry.turnId === message.turnId && entry.sender === 'user');
      if (original) void send(original.content);
    }} />)}</div>
    {state.pending && <p role="status">Your question is saved. Preparing a verified answer…</p>}
    {(state.error || inputError) && <p role="alert">{state.error ?? inputError}</p>}
    {state.canRetryNetwork && <button onClick={() => { void chat.retryNetwork().catch(() => undefined); }}>Resume safely</button>}
    {!state.loading && state.error && !state.canRetryNetwork && <button onClick={() => { void chat.open().catch(() => undefined); }}>Reload conversation</button>}
    <form onSubmit={(event) => { event.preventDefault(); void send(); }}>
      <label htmlFor="chat-question">Question</label><textarea id="chat-question" value={question} onChange={(event) => { setQuestion(event.target.value); }} disabled={busy} required aria-describedby="question-help" onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !busy) { event.preventDefault(); void send(); } }} />
      <p id="question-help">Ask a company question in 1–4000 characters. Enter sends; Shift+Enter adds a line.</p>
      <button type="submit" disabled={busy}>{state.sending ? 'Saving question…' : 'Send question'}</button>
    </form>
  </section>;
}

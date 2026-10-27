/** Per-resource maintenance preserves current data and requires reload after optimistic concurrency conflicts. */
import { useState, type FormEvent } from 'react';
import { ApplicationFailure, type Attachment } from '@/domain/common';
import type { KnowledgeItem } from '@/domain/knowledge';
import type { KnowledgeController } from '@/application/knowledge';

/** Edit one loaded item version, replace originals and confirm removal without automatic stale retries. */
export function AdminResource({ item, knowledge, wrapFile, update, removed }: { item: KnowledgeItem; knowledge: KnowledgeController; wrapFile: (file: File) => Attachment; update: (item: KnowledgeItem) => void; removed: (id: string) => void }) {
  const [title, setTitle] = useState(item.title);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState('');
  /** Preserve valid information and require an explicit reload after any stale-version response. */
  function failed(failure: unknown) {
    const stale = failure instanceof ApplicationFailure && failure.code === 'version_conflict';
    setConflict(stale);
    setError(stale ? 'This item changed. Reload it before editing.' : failure instanceof ApplicationFailure ? failure.message : 'The edit could not be completed. Please retry.');
  }
  /** Save only the edited title under the exact loaded concurrency version. */
  async function rename(event: FormEvent) {
    event.preventDefault(); if (busy || conflict) return; setBusy(true); setError('');
    try { update(await knowledge.rename(item, title)); } catch (failure) { failed(failure); } finally { setBusy(false); }
  }
  /** Submit a replacement candidate and retain the current original until successful publication. */
  async function replace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!file || busy || conflict) return; setBusy(true); setError('');
    const form = event.currentTarget;
    try {
      const accepted = await knowledge.replace(item, wrapFile(file)); update(accepted); setFile(null); form.reset();
      void knowledge.watch(accepted, update).catch(() => { setError('Status could not be refreshed. Reload to retry.'); });
    } catch (failure) { failed(failure); } finally { setBusy(false); }
  }
  /** A confirmed removal sends exactly the loaded version and removes UI state only after success. */
  async function remove() {
    if (!confirming || busy || conflict) return; setBusy(true); setError('');
    try { await knowledge.remove(item); removed(item.id); } catch (failure) { failed(failure); } finally { setBusy(false); }
  }
  /** Explicitly reload the authoritative version after a conflict before allowing another mutation. */
  async function reload() {
    setBusy(true);
    try { const current = await knowledge.reload(item.id); update(current); setTitle(current.title); setConflict(false); setError(''); setConfirming(false); }
    catch (failure) { failed(failure); } finally { setBusy(false); }
  }
  /** Revalidate current revision and session before reading an original. */
  async function open() { try { await knowledge.openSource(item); } catch { setError('This original is unavailable or your login expired. Reload to retry.'); } }
  const disabled = busy || conflict;
  return <li><h3>{item.title}</h3><p role="status">{item.candidateRevision?.state === 'processing' ? 'Processing' : item.candidateRevision?.state === 'failed' && item.currentRevision ? 'Replacement failed; current original is ready' : item.availability === 'ready' ? 'Ready' : 'Failed'}</p>
    {item.candidateRevision?.errorMessage && <p>{item.candidateRevision.errorMessage}</p>}
    {item.currentRevision && <><p>Current original: {item.currentRevision.originalFilename}</p><button onClick={() => { void open(); }}>Download original: {item.title}</button></>}
    <form onSubmit={(event) => { void rename(event); }}><label htmlFor={`title-${item.id}`}>Edit title: {item.title}</label><input id={`title-${item.id}`} value={title} onChange={(event) => { setTitle(event.target.value); }} disabled={disabled} required /><button disabled={disabled} type="submit">Save title</button></form>
    <form onSubmit={(event) => { void replace(event); }}><label htmlFor={`replacement-${item.id}`}>Replacement file: {item.title}</label><input id={`replacement-${item.id}`} type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" onChange={(event) => { setFile(event.target.files?.[0] ?? null); }} disabled={disabled || item.candidateRevision?.state === 'processing'} required /><button type="submit" disabled={disabled || item.candidateRevision?.state === 'processing'}>Replace original</button></form>
    <button disabled={disabled} onClick={() => { setConfirming(true); }}>Remove item</button>
    {confirming && <fieldset><legend>Remove {item.title}? Future answers and original reads will exclude it immediately.</legend><button disabled={disabled} onClick={() => { void remove(); }}>Confirm removal</button><button disabled={busy} onClick={() => { setConfirming(false); }}>Cancel removal</button></fieldset>}
    {error && <p role="alert">{error}</p>}<button disabled={busy} onClick={() => { void reload(); }}>Reload item</button>
  </li>;
}

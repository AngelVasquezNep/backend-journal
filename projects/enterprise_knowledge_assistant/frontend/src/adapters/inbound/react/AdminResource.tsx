/** Per-resource maintenance preserves current data and requires reload after optimistic concurrency conflicts. */
import { useState, type FormEvent } from 'react';
import { ApplicationFailure, type Attachment } from '@/domain/common';
import type { KnowledgeItem } from '@/domain/knowledge';
import type { KnowledgeController } from '@/application/knowledge';
import { FileBadge, Icon } from '@/adapters/inbound/react/UI';

/** Edit one loaded item version, replace originals and confirm removal without automatic stale retries. */
export function AdminResource({ item, knowledge, wrapFile, update, removed }: { item: KnowledgeItem; knowledge: KnowledgeController; wrapFile: (file: File) => Attachment; update: (item: KnowledgeItem) => void; removed: (id: string) => void }) {
  const [title, setTitle] = useState(item.title);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  /** Preserve valid information and require an explicit reload after any stale-version response. */
  function failed(failure: unknown) {
    const stale = failure instanceof ApplicationFailure && failure.code === 'version_conflict';
    setConflict(stale);
    setError(stale ? 'This item changed. Reload it before editing.' : failure instanceof ApplicationFailure ? failure.message : 'The edit could not be completed. Please retry.');
  }
  /** Save only the edited title under the exact loaded concurrency version. */
  async function rename(event: FormEvent) {
    event.preventDefault(); if (busy || conflict) return; setBusy(true); setError(''); setNotice('');
    try { update(await knowledge.rename(item, title)); setNotice('Title saved.'); } catch (failure) { failed(failure); } finally { setBusy(false); }
  }
  /** Submit a replacement candidate and retain the current original until successful publication. */
  async function replace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!file || busy || conflict) return; setBusy(true); setError(''); setNotice('');
    const form = event.currentTarget;
    try {
      const accepted = await knowledge.replace(item, wrapFile(file)); update(accepted); setFile(null); form.reset();
      setNotice('Replacement uploaded. The current original stays available while it is prepared.');
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
  const processing = item.candidateRevision?.state === 'processing';
  const failedCandidate = item.candidateRevision?.state === 'failed';
  const status = processing ? 'Processing' : failedCandidate && item.currentRevision ? 'Replacement failed; current original is ready' : item.availability === 'ready' ? 'Ready' : 'Failed';
  return <li className="admin-resource"><header className="resource-header"><FileBadge filename={item.currentRevision?.originalFilename ?? item.candidateRevision?.originalFilename} /><div className="document-info"><h3>{item.title}</h3><p>{item.currentRevision ? `Current original: ${item.currentRevision.originalFilename}` : item.candidateRevision?.originalFilename ?? 'No ready original'}</p></div><p className={`status-pill ${processing ? 'status-pill--processing' : failedCandidate || item.availability === 'failed' ? 'status-pill--failed' : ''}`} role="status"><span />{status}</p>{item.currentRevision && <button className="icon-button resource-download" aria-label={`Download original: ${item.title}`} title="Download original" onClick={() => { void open(); }}><Icon name="download" /></button>}</header>
    {item.candidateRevision?.errorMessage && <p className="resource-error">{item.candidateRevision.errorMessage}</p>}
    <div className="resource-editors"><form onSubmit={(event) => { void rename(event); }}><label htmlFor={`title-${item.id}`}>Edit title<span className="sr-only">: {item.title}</span></label><div className="inline-field"><input id={`title-${item.id}`} value={title} onChange={(event) => { setTitle(event.target.value); }} disabled={disabled} required maxLength={200} /><button className="button-secondary" disabled={disabled} type="submit">Save title</button></div></form>
    <form onSubmit={(event) => { void replace(event); }}><label htmlFor={`replacement-${item.id}`}>Replacement file<span className="sr-only">: {item.title}</span></label><div className="inline-field"><input id={`replacement-${item.id}`} type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" onChange={(event) => { setFile(event.target.files?.[0] ?? null); }} disabled={disabled || processing} required /><button className="button-secondary" type="submit" disabled={disabled || processing}>Replace original</button></div></form></div>
    <footer className="resource-actions"><span>{processing ? 'Preparing this document for answers…' : 'Changes apply to future company answers.'}</span><div><button className="button-quiet" disabled={busy} onClick={() => { void reload(); }}>Reload item</button><button className="button-danger-quiet" disabled={disabled || confirming} onClick={() => { setConfirming(true); }}>Remove item</button></div></footer>
    {confirming && <fieldset className="removal-confirmation"><legend>Remove {item.title}?</legend><p>Future answers and original reads will exclude it immediately.</p><div><button className="button-danger" disabled={disabled} onClick={() => { void remove(); }}>Confirm removal</button><button className="button-secondary" disabled={busy} onClick={() => { setConfirming(false); }}>Cancel removal</button></div></fieldset>}
    {error && <p role="alert">{error}</p>}{notice && <p className="resource-notice" aria-live="polite"><Icon name="check" />{notice}</p>}
  </li>;
}

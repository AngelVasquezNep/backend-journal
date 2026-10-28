/** Admin upload view preserves ready resources while durable candidates process or fail. */
import { useEffect, useState, type FormEvent } from 'react';
import type { KnowledgeController } from '@/application/knowledge';
import type { Attachment } from '@/domain/common';
import type { KnowledgeItem } from '@/domain/knowledge';
import { AdminResource } from '@/adapters/inbound/react/AdminResource';
import { Icon, PageHeading } from '@/adapters/inbound/react/UI';

/** Upload supported originals and show authoritative processing outcomes without blocking navigation. */
export function AdminKnowledgePage({ knowledge, wrapFile }: { knowledge: KnowledgeController; wrapFile: (file: File) => Attachment }) {
  const [items, setItems] = useState<readonly KnowledgeItem[]>([]);
  const [title, setTitle] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [search, setSearch] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [uploadNotice, setUploadNotice] = useState('');
  useEffect(() => {
    let active = true;
    setLoaded(false); setError('');
    /** Replace only a terminal candidate's metadata, retaining all other company resources. */
    function update(value: KnowledgeItem) { if (active) setItems((current) => current.map((entry) => entry.id === value.id ? value : entry)); }
    void knowledge.list().then((page) => {
      if (!active) return;
      setItems(page.items); setCursor(page.nextCursor); setLoaded(true);
      for (const item of page.items) void knowledge.watch(item, update).catch(() => { if (active) setError('Status could not be refreshed. Reload to retry.'); });
    }).catch(() => { if (active) setError('Knowledge could not be loaded. Please retry.'); });
    return () => { active = false; };
  }, [knowledge, attempt]);
  /** Accept one original; rejected input leaves the title, selected file and existing ready data available. */
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy) { setError('Choose a supported file.'); return; }
    const form = event.currentTarget;
    setBusy(true); setError(''); setUploadNotice('');
    try {
      const item = await knowledge.upload(title, wrapFile(file));
      setItems((current) => [item, ...current]); setTitle(''); setFile(null); setSearch(''); form.reset();
      setUploadNotice(`${item.title} uploaded. You can follow its status below.`);
      void knowledge.watch(item, (value) => { setItems((current) => current.map((entry) => entry.id === value.id ? value : entry)); }).catch(() => { setError('Status could not be refreshed. Reload to retry.'); });
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Upload could not be accepted. Please retry.'); }
    finally { setBusy(false); }
  }
  /** Append additional resources and restore their nonrefreshing processing polls. */
  async function more() {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await knowledge.list(cursor); setItems((current) => [...current, ...page.items]); setCursor(page.nextCursor);
      for (const item of page.items) void knowledge.watch(item, (value) => { setItems((current) => current.map((entry) => entry.id === value.id ? value : entry)); }).catch(() => { setError('Status could not be refreshed. Reload to retry.'); });
    } catch { setError('More knowledge could not be loaded. Please retry.'); }
    finally { setLoadingMore(false); }
  }
  const visible = items.filter((item) => `${item.title} ${item.currentRevision?.originalFilename ?? item.candidateRevision?.originalFilename ?? ''}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  return <section className="feature-page admin-knowledge-page"><PageHeading title="Manage company knowledge" description="Keep your company's answers grounded in the right information." />
    <div className="upload-panel"><div className="upload-intro"><span className="section-icon"><Icon name="upload" /></span><h3>Add to your knowledge</h3><p>Upload an original. We'll prepare it for your company's questions.</p><span className="format-list">PDF, DOCX, TXT, PNG, JPG</span><small>1 byte–20 MiB per file.<br />English and Spanish text recognition.</small></div>
    <form className="upload-form" onSubmit={(event) => { void upload(event); }}>
      <label htmlFor="knowledge-title">Title</label><input id="knowledge-title" placeholder="Give this document a useful name" value={title} onChange={(event) => { setTitle(event.target.value); }} required maxLength={200} disabled={busy} />
      <label htmlFor="knowledge-file">Original file</label><div className={`file-picker ${file ? 'has-file' : ''}`}><Icon name={file ? 'check' : 'upload'} /><div><strong>{file ? file.name : 'Choose a file to upload'}</strong><span>{file ? 'Click to choose a different file' : 'PDF, document, text, or image. Up to 20 MiB.'}</span></div><input id="knowledge-file" type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" disabled={busy} onChange={(event) => { setFile(event.target.files?.[0] ?? null); }} required /></div>
      <button disabled={busy} type="submit"><Icon name="plus" />{busy ? 'Uploading…' : 'Upload knowledge'}</button>
    </form>{error && <p role="alert">{error}</p>}
    </div>{uploadNotice && <p className="success-notice" role="status"><Icon name="check" />{uploadNotice}</p>}
    <div className="resource-section-heading"><div><h3>Your documents</h3><p>Manage originals and follow their processing status.</p></div><label className="search-field"><Icon name="search" /><span className="sr-only">Search managed knowledge</span><input type="search" placeholder="Find a document…" value={search} onChange={(event) => { setSearch(event.target.value); }} /></label></div>
    {!loaded && !error && <div className="loading-state" role="status"><span className="loading-ring" />Loading documents…</div>}
    {!loaded && error && <button className="button-secondary" onClick={() => { setAttempt((value) => value + 1); }}>Refresh knowledge</button>}
    {loaded && !items.length && <div className="empty-state"><Icon name="library" /><h3>A home for your company's knowledge</h3><p>Upload your first document above. When it's ready, your team can find it in the library and ask about it in chat.</p></div>}
    {loaded && items.length > 0 && !visible.length && <div className="empty-state"><Icon name="search" /><h3>No matching documents</h3><p>Try another title or filename{cursor ? ', or load more knowledge below' : ''}.</p><button className="button-secondary" onClick={() => { setSearch(''); }}>Clear search</button></div>}
    <ul className="admin-resource-list">{visible.map((item) => <AdminResource key={item.id} item={item} knowledge={knowledge} wrapFile={wrapFile} update={(value) => { setItems((current) => current.map((entry) => entry.id === value.id ? value : entry)); }} removed={(id) => { setItems((current) => current.filter((entry) => entry.id !== id)); }} />)}</ul>{cursor && <button className="button-secondary load-more" disabled={loadingMore} onClick={() => { void more(); }}>{loadingMore ? 'Loading…' : 'Load more knowledge'}</button>}
  </section>;
}

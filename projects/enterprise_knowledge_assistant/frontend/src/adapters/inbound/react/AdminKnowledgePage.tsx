/** Admin upload view preserves ready resources while durable candidates process or fail. */
import { useEffect, useState, type FormEvent } from 'react';
import type { KnowledgeController } from '@/application/knowledge';
import type { Attachment } from '@/domain/common';
import type { KnowledgeItem } from '@/domain/knowledge';
import { AdminResource } from '@/adapters/inbound/react/AdminResource';

/** Upload supported originals and show authoritative processing outcomes without blocking navigation. */
export function AdminKnowledgePage({ knowledge, wrapFile }: { knowledge: KnowledgeController; wrapFile: (file: File) => Attachment }) {
  const [items, setItems] = useState<readonly KnowledgeItem[]>([]);
  const [title, setTitle] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [cursor, setCursor] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    /** Replace only a terminal candidate's metadata, retaining all other company resources. */
    function update(value: KnowledgeItem) { if (active) setItems((current) => current.map((entry) => entry.id === value.id ? value : entry)); }
    void knowledge.list().then((page) => {
      if (!active) return;
      setItems(page.items); setCursor(page.nextCursor);
      for (const item of page.items) void knowledge.watch(item, update).catch(() => { if (active) setError('Status could not be refreshed. Reload to retry.'); });
    }).catch(() => { if (active) setError('Knowledge could not be loaded. Please retry.'); });
    return () => { active = false; };
  }, [knowledge]);
  /** Accept one original; rejected input leaves the title, selected file and existing ready data available. */
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy) { setError('Choose a supported file.'); return; }
    const form = event.currentTarget;
    setBusy(true); setError('');
    try {
      const item = await knowledge.upload(title, wrapFile(file));
      setItems((current) => [item, ...current]); setTitle(''); setFile(null); form.reset();
      void knowledge.watch(item, (value) => { setItems((current) => current.map((entry) => entry.id === value.id ? value : entry)); }).catch(() => { setError('Status could not be refreshed. Reload to retry.'); });
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Upload could not be accepted. Please retry.'); }
    finally { setBusy(false); }
  }
  /** Append additional resources and restore their nonrefreshing processing polls. */
  async function more() {
    if (!cursor) return;
    try {
      const page = await knowledge.list(cursor); setItems((current) => [...current, ...page.items]); setCursor(page.nextCursor);
      for (const item of page.items) void knowledge.watch(item, (value) => { setItems((current) => current.map((entry) => entry.id === value.id ? value : entry)); }).catch(() => { setError('Status could not be refreshed. Reload to retry.'); });
    } catch { setError('More knowledge could not be loaded. Please retry.'); }
  }
  return <section><h2>Manage company knowledge</h2><p>Upload PDF, DOCX, UTF-8 TXT, PNG or JPG files, from 1 byte to 20 MiB. English and Spanish OCR are available.</p>
    <form onSubmit={(event) => { void upload(event); }}>
      <label htmlFor="knowledge-title">Title</label><input id="knowledge-title" value={title} onChange={(event) => { setTitle(event.target.value); }} required />
      <label htmlFor="knowledge-file">Original file</label><input id="knowledge-file" type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" onChange={(event) => { setFile(event.target.files?.[0] ?? null); }} required />
      <button disabled={busy} type="submit">{busy ? 'Uploading…' : 'Upload knowledge'}</button>
    </form>{error && <p role="alert">{error}</p>}
    <ul>{items.map((item) => <AdminResource key={item.id} item={item} knowledge={knowledge} wrapFile={wrapFile} update={(value) => { setItems((current) => current.map((entry) => entry.id === value.id ? value : entry)); }} removed={(id) => { setItems((current) => current.filter((entry) => entry.id !== id)); }} />)}</ul>{cursor && <button onClick={() => { void more(); }}>Load more knowledge</button>}
  </section>;
}

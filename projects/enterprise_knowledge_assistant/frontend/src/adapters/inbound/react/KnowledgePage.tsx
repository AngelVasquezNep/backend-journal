/** Read-only company resource view exposes only ready originals authorized on every download. */
import { useEffect, useState } from 'react';
import type { KnowledgeController } from '@/application/knowledge';
import type { KnowledgeItem } from '@/domain/knowledge';

/** List ready company information without exposing administration controls or ownership selectors. */
export function KnowledgePage({ knowledge }: { knowledge: Pick<KnowledgeController, 'list' | 'openSource'> }) {
  const [items, setItems] = useState<readonly KnowledgeItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    void knowledge.list().then((page) => { if (active) { setItems(page.items); setCursor(page.nextCursor); setLoaded(true); } }).catch(() => { if (active) setError('Knowledge could not be loaded. Please retry.'); });
    return () => { active = false; };
  }, [knowledge]);
  /** Request a fresh authorized original and retain resource metadata after a failed download. */
  async function open(item: KnowledgeItem) {
    try { await knowledge.openSource(item); setError(''); }
    catch { setError('This source is unavailable or your session has expired. Refresh the list and retry.'); }
  }
  /** Append one owner-scoped server page without retaining it beyond this mounted account view. */
  async function more() {
    if (!cursor) return;
    try { const page = await knowledge.list(cursor); setItems((current) => [...current, ...page.items]); setCursor(page.nextCursor); }
    catch { setError('More knowledge could not be loaded. Please retry.'); }
  }
  return <section><h2>Company knowledge</h2>{error && <p role="alert">{error}</p>}
    {!loaded && !error && <p role="status">Loading knowledge…</p>}
    {loaded && items.length === 0 && <p>No ready knowledge is available yet.</p>}
    <ul>{items.map((item) => <li key={item.id}><h3>{item.title}</h3><p>{item.currentRevision?.originalFilename}</p><button onClick={() => { void open(item); }}>Download original: {item.title}</button></li>)}</ul>
    {cursor && <button onClick={() => { void more(); }}>Load more knowledge</button>}
  </section>;
}

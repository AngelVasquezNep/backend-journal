/** Read-only company resource view exposes only ready originals authorized on every download. */
import { useEffect, useState } from 'react';
import type { KnowledgeController } from '@/application/knowledge';
import type { KnowledgeItem } from '@/domain/knowledge';
import { FileBadge, fileSize, Icon, PageHeading } from '@/adapters/inbound/react/UI';

/** List ready company information without exposing administration controls or ownership selectors. */
export function KnowledgePage({ knowledge }: { knowledge: Pick<KnowledgeController, 'list' | 'openSource'> }) {
  const [items, setItems] = useState<readonly KnowledgeItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('recent');
  const [opening, setOpening] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setError(''); setLoaded(false);
    void knowledge.list().then((page) => { if (active) { setItems(page.items); setCursor(page.nextCursor); setLoaded(true); } }).catch(() => { if (active) setError('Knowledge could not be loaded. Please retry.'); });
    return () => { active = false; };
  }, [knowledge, attempt]);
  /** Request a fresh authorized original and retain resource metadata after a failed download. */
  async function open(item: KnowledgeItem) {
    setOpening(item.id);
    try { await knowledge.openSource(item); setError(''); }
    catch { setError('This source is unavailable or your session has expired. Refresh the list and retry.'); }
    finally { setOpening(null); }
  }
  /** Append one owner-scoped server page without retaining it beyond this mounted account view. */
  async function more() {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    try { const page = await knowledge.list(cursor); setItems((current) => [...current, ...page.items]); setCursor(page.nextCursor); setError(''); }
    catch { setError('More knowledge could not be loaded. Please retry.'); }
    finally { setLoadingMore(false); }
  }
  const visible = items.filter((item) => `${item.title} ${item.currentRevision?.originalFilename ?? ''}`.toLocaleLowerCase().includes(search.toLocaleLowerCase())).sort((a, b) => sort === 'title' ? a.title.localeCompare(b.title) : b.updatedAt.localeCompare(a.updatedAt));
  return <section className="feature-page library-page"><PageHeading title="Company knowledge" description="The source of what your company knows. Explore the originals behind your answers." />
    <div className="library-intro"><span className="library-intro-icon"><Icon name="library" /></span><div><h3>A shared library. A clearer picture.</h3><p>These documents are ready to use in your company chat. Open an original whenever you want a closer look.</p></div><span className="status-pill"><span />Ready for answers</span></div>
    <div className="library-toolbar"><label className="search-field"><Icon name="search" /><span className="sr-only">Search knowledge</span><input type="search" placeholder="Search by title or filename…" value={search} onChange={(event) => { setSearch(event.target.value); }} /></label><label className="sort-field"><span className="sr-only">Sort documents</span><select value={sort} onChange={(event) => { setSort(event.target.value); }}><option value="recent">Recently updated</option><option value="title">Title, A to Z</option></select></label></div>
    {error && <div className="error-with-action"><p role="alert">{error}</p><button className="button-secondary" onClick={() => { setAttempt((value) => value + 1); }}>Refresh knowledge</button></div>}
    {!loaded && !error && <div className="loading-state" role="status"><span className="loading-ring" />Loading knowledge…</div>}
    {loaded && <div className="library-list-header"><span>{search ? `${visible.length} matching documents` : `${items.length} document${items.length === 1 ? '' : 's'}${cursor ? ' loaded' : ''}`}</span><span>Original files</span></div>}
    {loaded && items.length === 0 && <div className="empty-state"><span className="empty-icon"><Icon name="library" /></span><h3>Your knowledge will live here</h3><p>No ready knowledge is available yet.</p><p>Once your workspace admin adds a document, you can explore it here and ask about it in chat.</p></div>}
    {loaded && items.length > 0 && visible.length === 0 && <div className="empty-state"><Icon name="search" /><h3>No matching documents</h3><p>Try another title or filename{cursor ? ', or load more knowledge below' : ''}.</p><button className="button-secondary" onClick={() => { setSearch(''); }}>Clear search</button></div>}
    <ul className="document-list">{visible.map((item) => <li className="document-row" key={item.id}><FileBadge filename={item.currentRevision?.originalFilename} /><div className="document-info"><h3>{item.title}</h3><p>{item.currentRevision?.originalFilename}{item.currentRevision && <span className="file-size">{fileSize(item.currentRevision.sizeBytes)}</span>}</p></div><time className="document-date" dateTime={item.updatedAt}>{new Date(item.updatedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</time><button className="button-secondary document-download" disabled={opening !== null} aria-label={`Download original: ${item.title}`} onClick={() => { void open(item); }}><Icon name="download" /><span>{opening === item.id ? 'Opening…' : 'Download'}</span></button></li>)}</ul>
    {cursor && <button className="button-secondary load-more" disabled={loadingMore} onClick={() => { void more(); }}>{loadingMore ? 'Loading…' : 'Load more knowledge'}</button>}
    <p className="page-footnote"><Icon name="lock" />Available only to your company. Originals are checked each time you open them.</p>
  </section>;
}

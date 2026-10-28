/** Source references display owned provenance and route only to freshly authorized same-origin originals. */
import type { Citation } from '@/domain/chat';
import { Icon } from '@/adapters/inbound/react/UI';

/** Render a human-readable original location without interpreting any source text as markup. */
function location(citations: readonly Citation[]): string {
  const kind = citations[0].locator.kind;
  const positions = citations.map(({ locator: value }) => {
    if (value.kind === 'pdf') return String(value.page);
    if (value.kind === 'text') return `${String(value.line_start)}–${String(value.line_end)}`;
    if (value.kind === 'docx') return `${Array.isArray(value.heading_path) && value.heading_path.length ? value.heading_path.join(' / ') : 'Document'}, block ${String(value.block)}`;
    return '1';
  });
  const label = kind === 'text' ? 'Lines' : kind === 'pdf' ? 'Pages' : kind === 'image' ? 'Image' : 'Sections';
  return `${label}: ${Array.from(new Set(positions)).join(', ')}`;
}

/** Keep unavailable historic labels visible without relinking their locator to a replacement revision. */
export function SourceReference({ citations, onOpen }: { citations: readonly Citation[]; onOpen: (citation: Citation) => Promise<void> }) {
  const citation = citations.find((value) => value.availability === 'current' && value.resourceURL) ?? citations[0];
  const available = citation.availability === 'current' && citation.resourceURL;
  return <li className="source-reference"><div className="source-reference-content"><Icon name="file" /><span className="source-reference-title">{citation.label}</span><span className="source-reference-divider" aria-hidden="true">|</span><span className="source-reference-locations">{location(citations)}</span><button type="button" className="source-download" aria-label={`Download original file: ${citation.label}`} title={available ? 'Download original file' : 'Source no longer available'} disabled={!available} onClick={() => { void onOpen(citation); }}><Icon name="download" /></button>{!available && <span className="source-reference-unavailable">Source no longer available</span>}</div></li>;
}

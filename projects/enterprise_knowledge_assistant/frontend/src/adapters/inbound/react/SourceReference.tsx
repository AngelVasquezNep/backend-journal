/** Source references display owned provenance and route only to freshly authorized same-origin originals. */
import type { Citation } from '@/domain/chat';

/** Render a human-readable original location without interpreting any source text as markup. */
function location(citation: Citation): string {
  const value = citation.locator;
  if (value.kind === 'pdf') return `page ${String(value.page)}`;
  if (value.kind === 'text') return `lines ${String(value.line_start)}–${String(value.line_end)}`;
  if (value.kind === 'docx') return `${Array.isArray(value.heading_path) ? value.heading_path.join(' / ') : 'Document'}, block ${String(value.block)}`;
  return 'image 1';
}

/** Keep unavailable historic labels visible without relinking their locator to a replacement revision. */
export function SourceReference({ citation, onOpen }: { citation: Citation; onOpen: (citation: Citation) => Promise<void> }) {
  const label = `${citation.label} (${location(citation)})`;
  return <li>{citation.availability === 'current' && citation.resourceURL ? <a href={citation.resourceURL} onClick={(event) => { event.preventDefault(); void onOpen(citation); }}>{label}</a> : <span>{label} — source no longer available</span>}</li>;
}

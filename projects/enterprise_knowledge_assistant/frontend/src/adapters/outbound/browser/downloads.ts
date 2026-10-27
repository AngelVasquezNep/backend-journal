/** User-requested original downloads stay transient and are cancelled when account identity changes. */
import type { Attachment } from '@/domain/common';
import type { AttachmentViewer } from '@/application/ports/knowledge';

/** Download validated bytes without localStorage, arbitrary remote URLs or persistent in-app caches. */
export class BrowserDownloads implements AttachmentViewer {
  private generation = 0;
  private urls = new Set<string>();

  /** Forget all pending/private object URLs before a different account may use the same UI. */
  clear(): void {
    this.generation += 1;
    for (const url of this.urls) URL.revokeObjectURL(url);
    this.urls.clear();
  }

  /** Start an explicit user-requested original download; never execute/render file content as app HTML. */
  async open(attachment: Attachment): Promise<void> {
    const generation = this.generation;
    const bytes = await attachment.read();
    if (generation !== this.generation) return;
    const copy = new Uint8Array(bytes);
    const url = URL.createObjectURL(new Blob([copy.buffer], { type: attachment.mediaType }));
    this.urls.add(url);
    const link = document.createElement('a');
    link.href = url;
    link.download = attachment.name;
    link.click();
    window.setTimeout(() => { URL.revokeObjectURL(url); this.urls.delete(url); }, 1000);
  }
}

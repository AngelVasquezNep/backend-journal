/** Browser implementations of clock, identifiers and binary attachments; no persistent storage. */
import type { Attachment } from '@/domain/common';
import type { Clock, IdGenerator } from '@/application/ports/common';

/** Inject browser time, timers and cryptographic UUID creation into application ports. */
export class BrowserRuntime implements Clock, IdGenerator {
  /** Return monotonic browser time used only for local polling/deadline behavior. */
  now(): number { return performance.now(); }
  /** Resolve after the requested interval; callers discard results when identity changes. */
  sleep(milliseconds: number): Promise<void> {
    return new Promise((resolve) => { window.setTimeout(resolve, milliseconds); });
  }
  /** Generate a random UUID without persisting any account or transcript state. */
  newId(): string { return crypto.randomUUID(); }
}

/** Wrap a browser file as the application's transport-independent attachment value. */
export class BrowserAttachment implements Attachment {
  /** Retain the selected file in memory; this adapter performs no automatic upload. */
  constructor(private readonly file: File) {}
  /** Return the untrusted original name for authoritative server validation. */
  get name(): string { return this.file.name; }
  /** Return the browser media hint; server-side content validation remains authoritative. */
  get mediaType(): string { return this.file.type; }
  /** Return declared file size so the UI can give early corrective feedback. */
  get size(): number { return this.file.size; }
  /** Read binary input without writing it to browser persistent storage. */
  async read(): Promise<Uint8Array> { return new Uint8Array(await this.file.arrayBuffer()); }
}

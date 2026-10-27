/** Framework-free shared result and failure values; never contain transport/browser objects. */
export interface Failure {
  readonly code: string;
  readonly message: string;
  readonly retryable: boolean;
}

/** A use-case result preserves typed failures without exposing a Fetch response. */
export type Result<T> = { readonly ok: true; readonly value: T } | { readonly ok: false; readonly error: Failure };

/** Domain-owned binary input; browser File values are wrapped by their outbound adapter. */
export interface Attachment {
  readonly name: string;
  readonly mediaType: string;
  readonly size: number;
  /** Read owned bytes; reject with an input failure when the underlying file is unreadable. */
  read(): Promise<Uint8Array>;
}

/** Carry a safe application failure; private network diagnostics never become user messages. */
export class ApplicationFailure extends Error implements Failure {
  /** Store a stable safe code and corrective message without raw response or credential data. */
  constructor(readonly code: string, message: string, readonly retryable = false) {
    super(message);
    this.name = 'ApplicationFailure';
  }
}

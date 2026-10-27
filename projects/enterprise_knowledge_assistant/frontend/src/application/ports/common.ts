/** Framework-free runtime ports make polling and message identity deterministic in tests. */
export interface Clock {
  /** Return elapsed milliseconds for deadlines; never require a browser global in core code. */
  now(): number;
  /** Delay polling without making network requests or refreshing login activity. */
  sleep(milliseconds: number): Promise<void>;
}

/** UUID creation belongs to a runtime adapter, never a browser API in an application use case. */
export interface IdGenerator {
  /** Generate a client message ID; intentional retries use a new ID, network replay reuses it. */
  newId(): string;
}

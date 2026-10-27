/** Application shell; protected feature routing is added by the auth composition task. */
import { APPLICATION_NAME } from '@/composition/title';
import type { ReactNode } from 'react';

/** Render the accessible application landmark and company-information scope. */
export function App({ children }: { children?: ReactNode }) {
  return <main><h1>{APPLICATION_NAME}</h1>{children ?? <p>Company knowledge</p>}</main>;
}

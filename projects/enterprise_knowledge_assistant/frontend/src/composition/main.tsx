/** Browser entry point; mounts the application and imports its visual styles. */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createDependencies } from '@/composition/dependencies';
import { Router } from '@/composition/router';
import '@fontsource/manrope/latin-500.css';
import '@fontsource/manrope/latin-600.css';
import '@fontsource/manrope/latin-700.css';
import '@fontsource/source-sans-3/latin-400.css';
import '@fontsource/source-sans-3/latin-600.css';
import '@/adapters/inbound/react/styles.css';

const root = document.getElementById('root');
if (!root) throw new Error('Application root is missing');
createRoot(root).render(
  <StrictMode>
    <Router dependencies={createDependencies()} />
  </StrictMode>,
);

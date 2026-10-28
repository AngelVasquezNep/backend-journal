/** Small, dependency-free visual primitives shared by the workspace presentation. */
import type { ReactNode } from 'react';
import { useState } from 'react';

type IconName = 'chat' | 'library' | 'settings' | 'user' | 'logout' | 'arrow' | 'file' | 'search' | 'upload' | 'check' | 'lock' | 'chevron' | 'menu' | 'close' | 'spark' | 'download' | 'plus' | 'eye' | 'eye-off';

const paths: Record<IconName, ReactNode> = {
  chat: <><path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5A8.5 8.5 0 0 1 10.5 3h2a8.5 8.5 0 0 1 8.5 8.5Z" /><path d="M7 10h9M7 14h6" /></>,
  library: <><path d="M4 4h4v16H4zM10 4h4v16h-4zM16 5l4-1 3 15-4 1z" /></>,
  settings: <><path d="M4 7h16M4 17h16" /><circle cx="9" cy="7" r="3" /><circle cx="15" cy="17" r="3" /></>,
  user: <><circle cx="10" cy="7" r="4" /><path d="M3 21v-2a7 7 0 0 1 14 0v2M20 8v6M17 11h6" /></>,
  logout: <path d="M9 4H4v16h5M9 12h12m-5-5 5 5-5 5" />,
  arrow: <path d="M12 20V4m-6 6 6-6 6 6" />,
  file: <><path d="M14 2H5v20h14V7zM14 2v5h5M8 12h8M8 16h5" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
  upload: <path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6" />,
  check: <path d="m5 12 4 4L19 6" />,
  lock: <><rect x="5" y="10" width="14" height="11" rx="3" /><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3" /></>,
  chevron: <path d="m9 5 7 7-7 7" />,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  spark: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z" /><path d="m20 2 .5 1.5L22 4l-1.5.5L20 6l-.5-1.5L18 4l1.5-.5z" /></>,
  download: <path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4" />,
  plus: <path d="M12 5v14M5 12h14" />,
  eye: <><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>,
  'eye-off': <path d="m3 3 18 18M10 5a12 12 0 0 1 12 7 18 18 0 0 1-3 4M6 6a18 18 0 0 0-4 6s4 7 10 7a12 12 0 0 0 5-1" />,
};

/** Render a decorative icon; the surrounding control supplies its accessible name. */
export function Icon({ name, className = '' }: { name: IconName; className?: string }) {
  return <svg className={`icon ${className}`} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

/** A folded-page monogram connects the identity to the company document library. */
export function BrandMark({ className = '' }: { className?: string }) {
  return <span className={`brand-mark ${className}`} aria-hidden="true"><svg width="27" height="27" viewBox="0 0 32 32" fill="none"><path d="M6 7h20v6h-7v14h-6V13H6V7Z" fill="currentColor" /><path d="m20 7 6 6V7h-6Z" fill="white" fillOpacity=".45" /></svg></span>;
}

/** Keep feature titles, descriptive copy and optional actions consistently aligned. */
export function PageHeading({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <header className="page-heading"><div><h2>{title}</h2><p>{description}</p></div>{action}</header>;
}

/** Identify an original by its real filename extension without guessing its content. */
export function FileBadge({ filename }: { filename?: string }) {
  const extension = filename?.split('.').pop()?.toLowerCase() ?? 'file';
  return <span className={`file-badge file-badge--${extension}`}><Icon name="file" /><span>{extension.length <= 5 ? extension : 'file'}</span></span>;
}

/** Format safe public file metadata for the document list. */
export function fileSize(bytes: number): string {
  return bytes < 1024 ? `${bytes} B` : bytes < 1048576 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / 1048576).toFixed(1)} MB`;
}

/** Keep password visibility local to a mounted field without copying or retaining its value. */
export function PasswordField({ id, label, value, onChange, autoComplete, disabled = false, hint }: { id: string; label: string; value: string; onChange: (value: string) => void; autoComplete: string; disabled?: boolean; hint?: string }) {
  const [visible, setVisible] = useState(false);
  return <div className="form-field"><label htmlFor={id}>{label}</label><div className="password-input"><input id={id} type={visible ? 'text' : 'password'} autoComplete={autoComplete} required value={value} disabled={disabled} aria-describedby={hint ? `${id}-hint` : undefined} onChange={(event) => { onChange(event.target.value); }} /><button type="button" className="icon-button" disabled={disabled} aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`} aria-pressed={visible} onClick={() => { setVisible(!visible); }}><Icon name={visible ? 'eye-off' : 'eye'} /></button></div>{hint && <small id={`${id}-hint`} className="field-hint">{hint}</small>}</div>;
}

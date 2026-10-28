/** Responsive workspace shell with role-aware navigation and an account-bound mobile drawer. */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { APPLICATION_NAME } from '@/composition/title';
import type { Account } from '@/domain/identity';
import { BrandMark, Icon } from '@/adapters/inbound/react/UI';

/** Render public entry or the protected workspace, preserving a single application landmark. */
export function App({ children, account, onLogout, logoutError, pageTitle = 'Company knowledge' }: { children?: ReactNode; account?: Account; onLogout?: () => void; logoutError?: string; pageTitle?: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!menuOpen) return;
    closeButton.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    /** Close the mobile navigation with Escape and return focus to its trigger. */
    function dismiss(event: KeyboardEvent) { if (event.key === 'Escape') { setMenuOpen(false); menuButton.current?.focus(); } }
    window.addEventListener('keydown', dismiss);
    return () => { window.removeEventListener('keydown', dismiss); document.body.style.overflow = previousOverflow; menuButton.current?.focus(); };
  }, [menuOpen]);
  const brand = <div className="brand"><BrandMark /><h1>{APPLICATION_NAME}<span className="brand-tagline" aria-hidden="true">Company knowledge, connected.</span></h1></div>;
  if (!account || account.mustChangePassword) return <main className="public-shell"><header className="public-header">{brand}<span className="workspace-label"><Icon name="lock" /> Your company workspace</span>{account && <button className="button-quiet" onClick={onLogout}><Icon name="logout" /> Log out</button>}</header>{logoutError && <p role="alert">{logoutError}</p>}{children ?? <p>Company knowledge</p>}<footer className="public-footer">A little less searching. A lot more knowing.<span>Private by design.</span></footer></main>;
  const initials = account.displayName.trim().split(/\s+/u).slice(0, 2).map((part) => part[0]).join('');
  return <main className={`workspace ${menuOpen ? 'is-menu-open' : ''}`}>
    <a className="skip-link" href="#workspace-content">Skip to content</a>
    {menuOpen && <button className="sidebar-scrim" aria-hidden="true" tabIndex={-1} onClick={() => { setMenuOpen(false); menuButton.current?.focus(); }} />}
    <aside className="sidebar" id="workspace-navigation" role={menuOpen ? 'dialog' : undefined} aria-modal={menuOpen ? true : undefined} aria-label="Workspace sidebar" onKeyDown={(event) => {
      if (!menuOpen || event.key !== 'Tab') return;
      const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('a[href], button'));
      const first = controls[0]; const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }}>
      <div className="sidebar-brand">{brand}<button ref={closeButton} className="icon-button mobile-close" aria-label="Close navigation" onClick={() => { setMenuOpen(false); menuButton.current?.focus(); }}><Icon name="close" /></button></div>
      <div className="workspace-switch"><span className="workspace-symbol"><Icon name="library" /></span><div>Company workspace<small>Your shared knowledge</small></div><Icon name="lock" /></div>
      <nav aria-label="Main navigation" onClick={() => { setMenuOpen(false); }}>
        <span className="nav-caption">Workspace</span>
        <NavLink to="/chat"><Icon name="chat" />Chat<Icon name="chevron" className="nav-chevron" /></NavLink>
        <NavLink to="/knowledge"><Icon name="library" />Knowledge<Icon name="chevron" className="nav-chevron" /></NavLink>
        {account.role === 'admin' && <><span className="nav-caption admin-caption">Administration</span><NavLink to="/admin/knowledge"><Icon name="settings" />Manage knowledge<Icon name="chevron" className="nav-chevron" /></NavLink><NavLink to="/admin/users"><Icon name="user" />Create user<Icon name="chevron" className="nav-chevron" /></NavLink></>}
      </nav>
      <div className="sidebar-bottom"><div className="sidebar-note"><span className="note-symbol"><Icon name="file" /></span><h3>Good answers start here.</h3><p>Your company's documents, brought into the conversation.</p><NavLink to="/knowledge" onClick={() => { setMenuOpen(false); }}>Explore your knowledge<Icon name="chevron" /></NavLink></div>
      <div className="account-bar"><span className="avatar">{initials}</span><div className="account-details"><strong>{account.displayName}</strong><span>{account.role === 'admin' ? 'Workspace admin' : 'Workspace member'}</span></div><button className="icon-button" onClick={onLogout} aria-label="Log out" title="Log out"><Icon name="logout" /></button></div></div>
    </aside>
    <div className="workspace-main" inert={menuOpen}><header className="workspace-header"><div><button ref={menuButton} className="icon-button menu-toggle" aria-label="Open navigation" aria-controls="workspace-navigation" aria-expanded={menuOpen} onClick={() => { setMenuOpen(true); }}><Icon name="menu" /></button><span className="header-workspace">Workspace<span className="header-divider">/</span><span>{pageTitle}</span></span></div><span className="privacy-badge"><Icon name="lock" />Private workspace</span></header>
      <div id="workspace-content" className="workspace-content" tabIndex={-1}>{logoutError && <p role="alert">{logoutError}</p>}{children}</div>
    </div>
  </main>;
}

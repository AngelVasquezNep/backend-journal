/** Same-origin route composition wires first-party identity guards without persistent browser state. */
import { useEffect, useState, useSyncExternalStore } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { KnowledgePage } from '@/adapters/inbound/react/KnowledgePage';
import { AdminKnowledgePage } from '@/adapters/inbound/react/AdminKnowledgePage';
import { CreateUserPage } from '@/adapters/inbound/react/CreateUserPage';
import { ChatPage } from '@/adapters/inbound/react/ChatPage';
import type { createDependencies } from '@/composition/dependencies';
import { App } from '@/adapters/inbound/react/App';
import { ChangePasswordPage } from '@/adapters/inbound/react/ChangePasswordPage';
import { LoginPage } from '@/adapters/inbound/react/LoginPage';
import { ProtectedRoute } from '@/adapters/inbound/react/ProtectedRoute';
import { APPLICATION_NAME } from '@/composition/title';

type Dependencies = ReturnType<typeof createDependencies>;

/** Render only after session recovery; a changed identity clears protected views synchronously. */
function SessionRoutes({ dependencies }: { dependencies: Dependencies }) {
  const { auth } = dependencies;
  const session = useSyncExternalStore((listener) => auth.subscribe(listener), () => auth.current);
  const [loading, setLoading] = useState(true);
  const [logoutError, setLogoutError] = useState('');
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const pageTitle = ({ '/chat': 'Company chat', '/knowledge': 'Company knowledge', '/admin/knowledge': 'Manage knowledge', '/admin/users': 'Create user', '/login': 'Log in', '/change-password': 'Change password' } as Record<string, string>)[pathname] ?? 'Company knowledge';
  useEffect(() => { document.title = `${pageTitle} | ${APPLICATION_NAME}`; window.scrollTo({ top: 0, behavior: 'instant' }); }, [pageTitle]);
  useEffect(() => {
    let active = true;
    void auth.restore().catch(() => { if (active) auth.clear(); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [auth]);
  /** Revoke login and clear private UI state; surface a retryable server-revocation failure. */
  async function endSession() {
    try { await auth.logout(); setLogoutError(''); }
    catch { setLogoutError('Logout could not be confirmed. Please retry when connected.'); }
  }
  if (loading) return <App><div className="loading-state" role="status"><span className="loading-ring" />Checking your session…</div></App>;
  return <App key={session?.account.id ?? 'anonymous'} account={session?.account} onLogout={() => { void endSession(); }} logoutError={logoutError} pageTitle={pageTitle}>
    <Routes>
      <Route path="/login" element={session ? <Navigate to={session.account.mustChangePassword ? '/change-password' : '/chat'} replace /> : <LoginPage auth={auth} onAuthenticated={(value) => { navigate(value.account.mustChangePassword ? '/change-password' : '/chat', { replace: true }); }} />} />
      <Route path="/change-password" element={!session ? <Navigate to="/login" replace /> : !session.account.mustChangePassword ? <Navigate to="/chat" replace /> : <ChangePasswordPage auth={auth} onChanged={() => { navigate('/chat', { replace: true }); }} />} />
      <Route path="/chat" element={<ProtectedRoute session={session}><ChatPage chat={dependencies.chat} /></ProtectedRoute>} />
      <Route path="/knowledge" element={<ProtectedRoute session={session}><KnowledgePage knowledge={dependencies.knowledge} /></ProtectedRoute>} />
      <Route path="/admin/knowledge" element={<ProtectedRoute session={session} adminOnly><AdminKnowledgePage knowledge={dependencies.knowledge} wrapFile={dependencies.wrapFile} /></ProtectedRoute>} />
      <Route path="/admin/users" element={<ProtectedRoute session={session} adminOnly><CreateUserPage createUser={dependencies.createUser} /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  </App>;
}

/** Bind browser routing at the composition boundary; application use cases know no route framework. */
export function Router({ dependencies }: { dependencies: Dependencies }) {
  return <BrowserRouter><SessionRoutes dependencies={dependencies} /></BrowserRouter>;
}

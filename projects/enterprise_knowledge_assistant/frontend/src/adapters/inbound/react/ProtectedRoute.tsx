/** Route guard checks in-memory authenticated state; the server validates every protected action. */
import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import type { AuthSession } from '@/domain/identity';

/** Redirect missing/restricted/incorrect-role state before rendering any private view. */
export function ProtectedRoute({ session, adminOnly = false, children }: { session: AuthSession | null; adminOnly?: boolean; children: ReactNode }) {
  if (!session) return <Navigate to="/login" replace />;
  if (session.account.mustChangePassword) return <Navigate to="/change-password" replace />;
  if (adminOnly && session.account.role !== 'admin') return <Navigate to="/chat" replace />;
  return <>{children}</>;
}

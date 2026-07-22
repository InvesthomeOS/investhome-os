'use client';

import { Suspense, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { AdoptionTourProvider } from '@/components/adoption/tour-provider';
import '@/components/adoption/adoption-g13.css';
import { canManageTraining, canViewAdoptionSurfaces } from '@/lib/adoption/permissions';
import { useAuth } from '@/lib/auth/auth-context';

export function AdoptionPageShell({
  children,
  adminOnly = false,
}: {
  children: ReactNode;
  adminOnly?: boolean;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (!canViewAdoptionSurfaces(user)) {
      router.replace('/forbidden');
      return;
    }
    if (adminOnly && !canManageTraining(user)) {
      router.replace('/forbidden');
    }
  }, [adminOnly, loading, router, user]);

  if (loading || !user) {
    return (
      <main className="adop-g13" data-testid="adop-loading">
        <div className="adop-g13__body">
          <p className="adop-g13__muted">Loading…</p>
        </div>
      </main>
    );
  }

  if (adminOnly && !canManageTraining(user)) return null;

  return (
    <AdoptionTourProvider userId={user.id}>
      <Suspense
        fallback={
          <main className="adop-g13">
            <div className="adop-g13__body">
              <p className="adop-g13__muted">Loading…</p>
            </div>
          </main>
        }
      >
        {children}
      </Suspense>
    </AdoptionTourProvider>
  );
}

'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import type { PortalInvestor } from '../_data/types';

interface PortalSessionValue {
  loading: boolean;
  investorId: string | null;
  profile: Pick<
    PortalInvestor,
    'id' | 'fullName' | 'email' | 'avatarInitials' | 'tier' | 'twoFactorEnabled'
  > | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const PortalSessionContext = createContext<PortalSessionValue | null>(null);

export function PortalSessionProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [investorId, setInvestorId] = useState<string | null>(null);
  const [profile, setProfile] = useState<PortalSessionValue['profile']>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/portal/session', { credentials: 'include' });
      if (!res.ok) {
        setInvestorId(null);
        setProfile(null);
        return;
      }
      const data = (await res.json()) as {
        investorId: string;
        profile: PortalSessionValue['profile'];
      };
      setInvestorId(data.investorId);
      setProfile(data.profile);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await fetch('/api/portal/session', { method: 'DELETE', credentials: 'include' });
    setInvestorId(null);
    setProfile(null);
    window.location.href = '/portal/login';
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({ loading, investorId, profile, refresh, logout }),
    [loading, investorId, profile, refresh, logout],
  );

  return (
    <PortalSessionContext.Provider value={value}>{children}</PortalSessionContext.Provider>
  );
}

export function usePortalSession(): PortalSessionValue {
  const ctx = useContext(PortalSessionContext);
  if (!ctx) {
    throw new Error('usePortalSession must be used within PortalSessionProvider');
  }
  return ctx;
}

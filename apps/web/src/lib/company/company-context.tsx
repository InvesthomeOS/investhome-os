'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import {
  fetchCompanyContext,
  fetchPublicBrand,
  type CompanyContext,
  type PublicBrand,
} from '@/lib/api/company-foundation';
import { useAuth } from '@/lib/auth/auth-context';

type CompanyBrandingContextValue = {
  context: CompanyContext | null;
  publicBrand: PublicBrand | null;
  loading: boolean;
  refresh: () => Promise<void>;
  displayName: string;
  slogan: string | null;
  primaryColor: string;
  accentColor: string;
};

const FALLBACK_NAME = 'Investhome OS';
const FALLBACK_PRIMARY = '#1e3a5f';
const FALLBACK_ACCENT = '#0ea5e9';

const CompanyBrandingContext = createContext<CompanyBrandingContextValue | null>(null);

export function CompanyBrandingProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [context, setContext] = useState<CompanyContext | null>(null);
  const [publicBrand, setPublicBrand] = useState<PublicBrand | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      if (user) {
        const next = await fetchCompanyContext();
        setContext(next);
        setPublicBrand(null);
      } else {
        const next = await fetchPublicBrand();
        setPublicBrand(next);
        setContext(null);
      }
    } catch {
      setContext(null);
      setPublicBrand(null);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo<CompanyBrandingContextValue>(() => {
    const source = context ?? publicBrand;
    const brand = context?.brand;
    return {
      context,
      publicBrand,
      loading,
      refresh,
      displayName: source?.company_name ?? source?.short_name ?? FALLBACK_NAME,
      slogan: source?.slogan ?? null,
      primaryColor: brand?.primary_color ?? publicBrand?.primary_color ?? FALLBACK_PRIMARY,
      accentColor: brand?.accent_color ?? publicBrand?.accent_color ?? FALLBACK_ACCENT,
    };
  }, [context, publicBrand, loading, refresh]);

  return <CompanyBrandingContext.Provider value={value}>{children}</CompanyBrandingContext.Provider>;
}

export function useCompanyBranding(): CompanyBrandingContextValue {
  const ctx = useContext(CompanyBrandingContext);
  if (!ctx) {
    return {
      context: null,
      publicBrand: null,
      loading: false,
      refresh: async () => {},
      displayName: FALLBACK_NAME,
      slogan: null,
      primaryColor: FALLBACK_PRIMARY,
      accentColor: FALLBACK_ACCENT,
    };
  }
  return ctx;
}

export function PublicBrandingProvider({ children }: { children: React.ReactNode }) {
  const [publicBrand, setPublicBrand] = useState<PublicBrand | null>(null);

  useEffect(() => {
    void fetchPublicBrand()
      .then(setPublicBrand)
      .catch(() => setPublicBrand(null));
  }, []);

  const value = useMemo<CompanyBrandingContextValue>(
    () => ({
      context: null,
      publicBrand,
      loading: publicBrand === null,
      refresh: async () => {
        const next = await fetchPublicBrand();
        setPublicBrand(next);
      },
      displayName: publicBrand?.company_name ?? publicBrand?.short_name ?? FALLBACK_NAME,
      slogan: publicBrand?.slogan ?? null,
      primaryColor: publicBrand?.primary_color ?? FALLBACK_PRIMARY,
      accentColor: publicBrand?.accent_color ?? FALLBACK_ACCENT,
    }),
    [publicBrand],
  );

  return <CompanyBrandingContext.Provider value={value}>{children}</CompanyBrandingContext.Provider>;
}

export function useOptionalCompanyBranding(): CompanyBrandingContextValue {
  return useCompanyBranding();
}

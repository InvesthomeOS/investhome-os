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

import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

type GlobalSearchContextValue = {
  open: boolean;
  openPalette: () => void;
  closePalette: () => void;
  togglePalette: () => void;
  canSearch: boolean;
};

const GlobalSearchContext = createContext<GlobalSearchContextValue | null>(null);

export function GlobalSearchProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const canSearch = user ? hasPermission(user, 'search', 'view') : false;
  const [open, setOpen] = useState(false);

  const openPalette = useCallback(() => {
    if (canSearch) setOpen(true);
  }, [canSearch]);

  const closePalette = useCallback(() => setOpen(false), []);

  const togglePalette = useCallback(() => {
    if (!canSearch) return;
    setOpen((value) => !value);
  }, [canSearch]);

  useEffect(() => {
    if (!canSearch) return;
    const onKeyDown = (event: KeyboardEvent) => {
      const isMac = navigator.platform.toLowerCase().includes('mac');
      const modifier = isMac ? event.metaKey : event.ctrlKey;
      if (modifier && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen((value) => !value);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [canSearch]);

  const value = useMemo(
    () => ({
      open,
      openPalette,
      closePalette,
      togglePalette,
      canSearch,
    }),
    [open, openPalette, closePalette, togglePalette, canSearch],
  );

  return <GlobalSearchContext.Provider value={value}>{children}</GlobalSearchContext.Provider>;
}

export function useGlobalSearch() {
  const context = useContext(GlobalSearchContext);
  if (!context) {
    throw new Error('useGlobalSearch must be used within GlobalSearchProvider');
  }
  return context;
}

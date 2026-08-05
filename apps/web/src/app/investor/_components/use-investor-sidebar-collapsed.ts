'use client';

import { useCallback, useSyncExternalStore } from 'react';

const STORAGE_KEY = 'investhome-investor-sidebar-collapsed';

const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

function subscribe(onStoreChange: () => void): () => void {
  listeners.add(onStoreChange);
  if (typeof window === 'undefined') {
    return () => {
      listeners.delete(onStoreChange);
    };
  }
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY || event.key === null) onStoreChange();
  };
  window.addEventListener('storage', onStorage);
  return () => {
    listeners.delete(onStoreChange);
    window.removeEventListener('storage', onStorage);
  };
}

function getSnapshot(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

/** Must match SSR — expanded. Client may update after hydration without #418. */
function getServerSnapshot(): boolean {
  return false;
}

export function useInvestorSidebarCollapsed(): [boolean, () => void] {
  const collapsed = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const toggle = useCallback(() => {
    try {
      const next = localStorage.getItem(STORAGE_KEY) !== 'true';
      localStorage.setItem(STORAGE_KEY, String(next));
    } catch {
      /* ignore */
    }
    emit();
  }, []);

  return [collapsed, toggle];
}

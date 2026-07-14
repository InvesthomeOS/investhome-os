'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

export function useRecordDeepLink<T>(
  fetchById: (id: string) => Promise<T>,
  onOpen: (record: T) => void,
  paramName = 'id',
) {
  const pathname = usePathname();

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const recordId = params.get(paramName);
    if (!recordId) return;

    let cancelled = false;
    void fetchById(recordId)
      .then((record) => {
        if (!cancelled) onOpen(record);
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, [pathname, paramName, fetchById, onOpen]);
}

'use client';

import { useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';

export function useRecordDeepLink<T>(
  fetchById: (id: string) => Promise<T>,
  onOpen: (record: T) => void,
  paramName = 'id',
  reactToSearchChanges = false,
) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const recordId = searchParams.get(paramName);
  const recordDependency = reactToSearchChanges ? recordId : null;

  useEffect(() => {
    const targetId = reactToSearchChanges
      ? recordDependency
      : new URLSearchParams(window.location.search).get(paramName);
    if (!targetId) return;

    let cancelled = false;
    void fetchById(targetId)
      .then((record) => {
        if (!cancelled) onOpen(record);
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, [pathname, recordDependency, paramName, reactToSearchChanges, fetchById, onOpen]);
}

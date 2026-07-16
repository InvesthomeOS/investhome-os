'use client';

import { useEffect, useState } from 'react';

const STORAGE_KEY = 'investhome-sidebar-collapsed';

export function useSidebarCollapsed(): [boolean, () => void] {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(STORAGE_KEY) === 'true');
    } catch {
      setCollapsed(false);
    }
  }, []);

  const toggle = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, String(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  return [collapsed, toggle];
}

export { STORAGE_KEY as SIDEBAR_STORAGE_KEY };

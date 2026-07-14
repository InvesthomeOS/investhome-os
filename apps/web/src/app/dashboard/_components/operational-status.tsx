'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchHealth } from '@/lib/api/health';

type OperationalState = 'loading' | 'operational' | 'degraded' | 'unavailable';

export function OperationalStatus() {
  const t = useTranslations('dashboard.operational');
  const [state, setState] = useState<OperationalState>('loading');

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((health) => {
        if (cancelled) {
          return;
        }

        if (health.status === 'ok' && health.database === 'connected') {
          setState('operational');
          return;
        }

        setState('degraded');
      })
      .catch(() => {
        if (!cancelled) {
          setState('unavailable');
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <span className={`dashboard__status dashboard__status--${state}`}>
      {t(state)}
    </span>
  );
}

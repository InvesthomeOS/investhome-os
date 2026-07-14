'use client';

import { useEffect, useState } from 'react';

import { fetchHealth } from '@/lib/api/health';

type OperationalState = 'loading' | 'operational' | 'degraded' | 'unavailable';

const STATUS_LABELS: Record<OperationalState, string> = {
  loading: 'Checking…',
  operational: 'Operational',
  degraded: 'Degraded',
  unavailable: 'Unavailable',
};

export function OperationalStatus() {
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
      {STATUS_LABELS[state]}
    </span>
  );
}

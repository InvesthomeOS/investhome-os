'use client';

/**
 * Shared Creative Studio builder hydration lifecycle.
 * Ensures bootstrap always resolves to ready or error (never stranded hydrated=false),
 * and Strict Mode remounts cannot strand UI on a cancelled first run.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export type CsBuilderHydrationPhase = 'loading' | 'ready' | 'error';

export type CsBuilderBootstrapResult<TDraft> =
  | { ok: true; draft: TDraft | null }
  | { ok: false; error: string };

export type UseCsBuilderHydrationResult = {
  phase: CsBuilderHydrationPhase;
  /** True only after a successful bootstrap. */
  hydrated: boolean;
  error: string | null;
  retry: () => void;
};

export function useCsBuilderHydration<TDraft>(options: {
  bootstrap: () => Promise<CsBuilderBootstrapResult<TDraft>>;
  /** Called only for successful bootstrap results (including empty/new draft=null). */
  onSuccess: (draft: TDraft | null) => void;
}): UseCsBuilderHydrationResult {
  const { bootstrap, onSuccess } = options;
  const [phase, setPhase] = useState<CsBuilderHydrationPhase>('loading');
  const [error, setError] = useState<string | null>(null);

  const bootstrapRef = useRef(bootstrap);
  bootstrapRef.current = bootstrap;
  const onSuccessRef = useRef(onSuccess);
  onSuccessRef.current = onSuccess;
  const genRef = useRef(0);

  const run = useCallback(async () => {
    const gen = ++genRef.current;
    setPhase('loading');
    setError(null);
    try {
      const result = await bootstrapRef.current();
      if (gen !== genRef.current) return;
      if (result.ok) {
        onSuccessRef.current(result.draft);
        setError(null);
        setPhase('ready');
        return;
      }
      setError(result.error || 'Load failed');
      setPhase('error');
    } catch (err) {
      if (gen !== genRef.current) return;
      const message = err instanceof Error ? err.message : 'Load failed';
      setError(message);
      setPhase('error');
    }
  }, []);

  useEffect(() => {
    void run();
    return () => {
      // Invalidate in-flight run so Strict Mode cleanup cannot apply stale results,
      // while the remount starts a fresh generation via run().
      genRef.current += 1;
    };
  }, [run]);

  return {
    phase,
    hydrated: phase === 'ready',
    error,
    retry: () => {
      void run();
    },
  };
}

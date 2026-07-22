'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** Legacy route → G7 Settings view */
export default function AiSettingsRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/dashboard/ai?view=settings');
  }, [router]);
  return null;
}

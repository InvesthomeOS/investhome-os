'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** Legacy route → G7 Activity Log view */
export default function AiHistoryRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/dashboard/ai?view=activity_log');
  }, [router]);
  return null;
}

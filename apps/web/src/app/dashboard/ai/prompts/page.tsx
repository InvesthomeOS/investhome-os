'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** Legacy route → G7 Prompt Library view */
export default function AiPromptsRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/dashboard/ai?view=prompt_library');
  }, [router]);
  return null;
}

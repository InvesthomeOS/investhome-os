import { redirect } from 'next/navigation';
import type { Route } from 'next';

/** G1: /dashboard/documents list → canonical OS Documents (/dashboard/knowledge). */
export default function DocumentsPage() {
  redirect('/dashboard/knowledge' as Route);
}

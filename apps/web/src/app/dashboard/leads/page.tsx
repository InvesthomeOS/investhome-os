import { redirect } from 'next/navigation';
import type { Route } from 'next';

export default function LeadsPage() {
  redirect('/dashboard/sales' as Route);
}

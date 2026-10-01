import { redirect } from 'next/navigation';
import type { Route } from 'next';

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CrmPersonDetailPage({ params }: PageProps) {
  const { id } = await params;
  redirect(`/workspaces/crm/contacts?contact=${encodeURIComponent(id)}` as Route);
}

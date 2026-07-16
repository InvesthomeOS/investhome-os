import type { Route } from 'next';
import { notFound, redirect } from 'next/navigation';

import { isModuleName } from '@/lib/modules';

interface ModulePageProps {
  params: Promise<{ module: string }>;
}

export default async function ModulePage({ params }: ModulePageProps) {
  const { module } = await params;

  if (!isModuleName(module)) {
    notFound();
  }

  if (module === 'leads') {
    redirect('/dashboard/sales' as Route);
  }

  if (module === 'investors') {
    redirect('/dashboard/investors' as Route);
  }

  if (module === 'projects') {
    redirect('/dashboard/projects' as Route);
  }

  if (module === 'inventory') {
    redirect('/dashboard/inventory' as Route);
  }

  if (module === 'finance') {
    redirect('/dashboard/finance' as Route);
  }

  if (module === 'executive') {
    redirect('/dashboard/executive' as Route);
  }

  notFound();
}

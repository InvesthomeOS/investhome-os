'use client';

import dynamic from 'next/dynamic';
import { LoadingState } from '@investhome/ui';

const RolesAdminWorkspace = dynamic(
  () => import('./_components/roles-admin-workspace').then((module) => module.RolesAdminWorkspace),
  { loading: () => <LoadingState /> },
);

export default function AdminRolesPage() {
  return <RolesAdminWorkspace />;
}

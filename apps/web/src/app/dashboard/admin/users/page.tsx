'use client';

import dynamic from 'next/dynamic';
import { LoadingState } from '@investhome/ui';

const UsersAdminWorkspace = dynamic(
  () => import('./_components/users-admin-workspace').then((module) => module.UsersAdminWorkspace),
  { loading: () => <LoadingState /> },
);

export default function AdminUsersPage() {
  return <UsersAdminWorkspace />;
}

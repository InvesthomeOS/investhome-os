'use client';

import dynamic from 'next/dynamic';
import { LoadingState } from '@investhome/ui';

const PermissionsMatrixWorkspace = dynamic(
  () =>
    import('./_components/permissions-matrix-workspace').then((module) => module.PermissionsMatrixWorkspace),
  { loading: () => <LoadingState /> },
);

export default function AdminPermissionsPage() {
  return <PermissionsMatrixWorkspace />;
}

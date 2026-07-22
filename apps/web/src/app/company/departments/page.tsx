import dynamic from 'next/dynamic';

import { LoadingState } from '@investhome/ui';

const DepartmentsWorkspace = dynamic(
  () => import('./_components/departments-workspace').then((mod) => mod.DepartmentsWorkspace),
  { loading: () => <LoadingState /> },
);

export default function DepartmentsPage() {
  return <DepartmentsWorkspace />;
}

import dynamic from 'next/dynamic';

import { LoadingState } from '@investhome/ui';

const EmployeesWorkspace = dynamic(
  () => import('./_components/employees-workspace').then((mod) => mod.EmployeesWorkspace),
  { loading: () => <LoadingState variant="skeleton" lines={5} /> },
);

export default function EmployeesPage() {
  return <EmployeesWorkspace />;
}

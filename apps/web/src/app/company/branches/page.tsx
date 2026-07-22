import dynamic from 'next/dynamic';

import { LoadingState } from '@investhome/ui';

const BranchesWorkspace = dynamic(
  () => import('./_components/branches-workspace').then((mod) => mod.BranchesWorkspace),
  { loading: () => <LoadingState /> },
);

export default function BranchesPage() {
  return <BranchesWorkspace />;
}

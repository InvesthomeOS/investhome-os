import dynamic from 'next/dynamic';

import { LoadingState } from '@investhome/ui';

const CompanyDocumentsWorkspace = dynamic(
  () => import('./_components/documents-workspace').then((mod) => mod.CompanyDocumentsWorkspace),
  { loading: () => <LoadingState /> },
);

export default function CompanyDocumentsPage() {
  return <CompanyDocumentsWorkspace />;
}

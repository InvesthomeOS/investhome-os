import dynamic from 'next/dynamic';

import { LoadingState } from '@investhome/ui';

const CompaniesWorkspace = dynamic(
  () => import('../_components/companies-workspace').then((mod) => mod.CompaniesWorkspace),
  { loading: () => <LoadingState /> },
);

export default function CompaniesPage() {
  return <CompaniesWorkspace />;
}

import { redirect } from 'next/navigation';

export default function CompanySettingsPage() {
  redirect('/dashboard/settings?tab=company');
}

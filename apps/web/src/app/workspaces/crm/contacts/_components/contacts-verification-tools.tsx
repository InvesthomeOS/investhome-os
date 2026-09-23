'use client';

import Link from 'next/link';
import { useLocale } from 'next-intl';

import { Button } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { exportBitrixVerificationCsv } from '@/workspaces/crm/api/contacts';

import './ds/contacts-ds.css';
import './people-workspace.css';

export function ContactsVerificationTools() {
  const locale = useLocale();
  const { has } = useCrmAccess();
  const tr = locale.startsWith('tr');

  const downloadExport = async () => {
    const blob = await exportBitrixVerificationCsv();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'bitrix-contact-verification.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="ctc-ds crm-people-tools-page" data-testid="crm-contacts-tools">
      <Link href="/workspaces/crm/contacts">{tr ? 'Kişilere dön' : 'Back to people'}</Link>
      <h1>{tr ? 'Kişi doğrulama araçları' : 'People verification tools'}</h1>
      <p>
        {tr
          ? 'Birincil Kişiler ekranından ayrılmış yönetim aracı. Müşteri verisini değiştirmez.'
          : 'Admin tool moved off the primary People screen. Does not change customer data.'}
      </p>
      {has('export') ? (
        <Button variant="secondary" size="sm" onClick={() => void downloadExport()} data-testid="crm-bitrix-csv-export">
          {tr ? 'Bitrix doğrulama CSV' : 'Bitrix verification CSV'}
        </Button>
      ) : (
        <p>{tr ? 'Dışa aktarma izniniz yok.' : 'Export permission required.'}</p>
      )}
    </div>
  );
}

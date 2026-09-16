'use client';

import { useLocale } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { LoadingState } from '@investhome/ui';

import { fetchCrmReportsSummary, type CrmReportCount } from '@/workspaces/crm/api/reports';

const COPY = {
  tr: {
    title: 'Raporlar',
    subtitle: 'Canlı CRM özetleri. Tahmin veya uydurma metrik yok.',
    contacts: 'Kişiler',
    total: 'Toplam',
    active: 'Aktif',
    junk: 'Junk',
    agents: 'Acentalar',
    agreement: 'Anlaşma kişileri',
    pipeline: 'Pipeline',
    activities: 'Aktiviteler',
    pending: 'Bekleyen görev',
    completed: 'Tamamlanan görev',
    overdue: 'Geciken görev',
    agreements: 'Anlaşmalar',
    reit: 'REIT yatırım toplamı',
    reitHint: 'Yalnızca dolu investment_amount değerleri',
    unavailable: 'Yok',
    companies: 'Şirketler',
    companyLinks: 'Şirket-kişi bağlantısı',
    relationships: 'İlişkiler',
    contactCompany: 'Kişi-şirket',
    investorProject: 'Yatırımcı-proje',
    stage: 'Aşama',
    type: 'Tür',
    group: 'Proje grubu',
    count: 'Adet',
  },
  en: {
    title: 'Reports',
    subtitle: 'Live CRM totals. No forecasts or invented metrics.',
    contacts: 'Contacts',
    total: 'Total',
    active: 'Active',
    junk: 'Junk',
    agents: 'Agents',
    agreement: 'Agreement contacts',
    pipeline: 'Pipeline',
    activities: 'Activities',
    pending: 'Pending tasks',
    completed: 'Completed tasks',
    overdue: 'Overdue tasks',
    agreements: 'Agreements',
    reit: 'REIT investment total',
    reitHint: 'Populated investment_amount values only',
    unavailable: 'n/a',
    companies: 'Companies',
    companyLinks: 'Company-contact links',
    relationships: 'Relationships',
    contactCompany: 'Contact-company',
    investorProject: 'Investor-project',
    stage: 'Stage',
    type: 'Type',
    group: 'Project group',
    count: 'Count',
  },
} as const;

function CountTable({
  title,
  keyLabel,
  rows,
}: {
  title: string;
  keyLabel: string;
  rows: CrmReportCount[];
}) {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  return (
    <article className="crm-reports__card">
      <header className="crm-reports__card-head">
        <h2>{title}</h2>
      </header>
      {rows.length === 0 ? (
        <p className="crm-reports__empty">{copy.unavailable}</p>
      ) : (
        <table className="crm-reports__table">
          <thead>
            <tr>
              <th>{keyLabel}</th>
              <th>{copy.count}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <td>{row.key}</td>
                <td>{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </article>
  );
}

function Kpi({ label, value }: { label: string; value: string | number }) {
  return (
    <article className="crm-reports__kpi">
      <div className="crm-reports__kpi-top">
        <span className="crm-reports__kpi-label">{label}</span>
      </div>
      <span className="crm-reports__kpi-value">{value}</span>
    </article>
  );
}

export function CrmReportsLiveWorkspace() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const query = useQuery({
    queryKey: ['crm', 'reports', 'summary'],
    queryFn: fetchCrmReportsSummary,
  });

  if (query.isLoading) {
    return <LoadingState label={copy.title} />;
  }

  const data = query.data;
  if (!data) {
    return <div className="crm-reports__empty">{copy.unavailable}</div>;
  }

  const reitValue =
    data.reit_investment.total == null
      ? copy.unavailable
      : new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(data.reit_investment.total);

  return (
    <div className="crm-reports" data-testid="crm-reports-live">
      <header className="crm-reports__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
      </header>

      <section className="crm-reports__kpi-row" aria-label={copy.contacts}>
        <Kpi label={`${copy.contacts} · ${copy.total}`} value={data.contacts_total} />
        <Kpi label={copy.active} value={data.contacts_active} />
        <Kpi label={copy.junk} value={data.contacts_junk} />
        <Kpi label={copy.agents} value={data.contacts_agents} />
        <Kpi label={copy.agreement} value={data.contacts_agreement} />
      </section>

      <section className="crm-reports__kpi-row" aria-label={copy.pipeline}>
        <Kpi label={copy.pipeline} value={data.pipeline_total} />
        <Kpi label={copy.activities} value={data.activities_total} />
        <Kpi label={copy.pending} value={data.tasks_pending} />
        <Kpi label={copy.completed} value={data.tasks_completed} />
        <Kpi label={copy.overdue} value={data.tasks_overdue} />
      </section>

      <section className="crm-reports__kpi-row" aria-label={copy.agreements}>
        <Kpi label={copy.agreements} value={data.agreements_total} />
        <Kpi label={copy.reit} value={reitValue} />
        <Kpi label={copy.companies} value={data.companies_total} />
        <Kpi label={copy.companyLinks} value={data.company_contact_links} />
        <Kpi label={copy.relationships} value={data.relationships_total} />
      </section>

      <section className="crm-reports__kpi-row" aria-label={copy.relationships}>
        <Kpi label={copy.contactCompany} value={data.relationships_contact_company} />
        <Kpi label={copy.investorProject} value={data.relationships_investor_project} />
        <Kpi
          label={copy.reitHint}
          value={`${data.reit_investment.populated_count}`}
        />
      </section>

      <section className="crm-reports__grid crm-reports__grid--secondary">
        <CountTable title={copy.pipeline} keyLabel={copy.stage} rows={data.pipeline_by_stage} />
        <CountTable title={copy.activities} keyLabel={copy.type} rows={data.activities_by_type} />
        <CountTable title={copy.agreements} keyLabel={copy.group} rows={data.agreements_by_project_group} />
      </section>
    </div>
  );
}

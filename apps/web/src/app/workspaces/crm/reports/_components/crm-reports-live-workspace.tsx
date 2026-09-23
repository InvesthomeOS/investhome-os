'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState, LoadingState, Select } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { downloadCsvFile } from '@/lib/api/documents';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  fetchCrmReportsWorkspace,
  type CrmReportCount,
  type CrmReportMoney,
  type CrmReportsInvestorRow,
  type CrmReportsSalesRow,
} from '@/workspaces/crm/api/reports';

import { CountBarChart, PetrolDonut, SplitBarChart } from './reports-charts';

const COPY = {
  tr: {
    title: 'Raporlar',
    subtitle: 'Canlı CRM yönetim raporları. Tahmin veya birleştirilmiş sahte toplam yok.',
    filters: 'Rapor filtreleri',
    dateRange: 'Tarih Aralığı',
    project: 'Proje',
    owner: 'Sorumlu',
    source: 'Kaynak',
    currency: 'Para Birimi',
    clear: 'Filtreleri Temizle',
    all: 'Tümü',
    today: 'Bugün',
    d7: 'Son 7 gün',
    d30: 'Son 30 gün',
    d90: 'Son 90 gün',
    year: 'Bu yıl',
    kpiPurchases: 'Güncel Satın Alma',
    kpiInvestors: 'Toplam Yatırımcı',
    kpiSales: 'Toplam Satış Tutarı',
    kpiTasks: 'Aktif Görev',
    kpiLeads: 'Açık Lead',
    kpiDocs: 'Belge İnceleme Gereken',
    none: '—',
    sales: 'Satın Alma / Satış',
    byProjectCount: 'Projeye Göre Satın Alma Sayısı',
    byProjectAmount: 'Projeye Göre Satış Tutarı',
    byMonth: 'Aylara Göre Satın Alma',
    currentVsHist: 'Güncel / Geçmiş satın alma',
    current: 'Güncel',
    historical: 'Geçmiş birim değişimi',
    investors: 'Yatırımcılar',
    perInvestor: 'Yatırımcı başına satın alma',
    investorProjects: 'Proje dağılımı',
    leads: 'Leadler',
    leadSource: 'Kaynak',
    leadStage: 'Aşama',
    leadOwner: 'Sorumlu',
    leadProject: 'Proje',
    conversion: 'Dönüşüm',
    won: 'Kazanılan',
    lost: 'Kaybedilen',
    rate: 'Oran',
    communication: 'İletişim',
    byChannel: 'Kanala göre aktivite',
    byTime: 'Zamana göre aktivite',
    byOwner: 'Sorumluya göre aktivite',
    email: 'E-posta',
    whatsapp: 'WhatsApp',
    calls: 'Aramalar',
    meetings: 'Toplantılar',
    tasks: 'Görevler',
    notes: 'Notlar',
    taskReport: 'Görevler',
    taskActive: 'Aktif',
    taskProgress: 'Devam Ediyor',
    taskDone: 'Tamamlandı',
    taskOverdue: 'Geciken',
    documents: 'Belgeler',
    docTotal: 'Toplam belge',
    docPerson: 'Kişi belgeleri',
    docPurchase: 'Satın alma belgeleri',
    docHidden: 'Gizli',
    docReview: 'İnceleme gereken',
    categories: 'Kategoriler',
    exportCsv: 'CSV',
    projectCol: 'Proje',
    count: 'Adet',
    amount: 'Tutar',
    name: 'Kişi',
    purchases: 'Satın alma',
    channel: 'Kanal',
    status: 'Durum',
    empty: 'Bu filtrelerde canlı kayıt yok.',
    unavailable: 'Raporlar yüklenemedi.',
  },
  en: {
    title: 'Reports',
    subtitle: 'Live CRM management reports. No forecasts or mixed-currency totals.',
    filters: 'Report filters',
    dateRange: 'Date range',
    project: 'Project',
    owner: 'Owner',
    source: 'Source',
    currency: 'Currency',
    clear: 'Clear filters',
    all: 'All',
    today: 'Today',
    d7: 'Last 7 days',
    d30: 'Last 30 days',
    d90: 'Last 90 days',
    year: 'This year',
    kpiPurchases: 'Current purchases',
    kpiInvestors: 'Investors',
    kpiSales: 'Sales amount',
    kpiTasks: 'Active tasks',
    kpiLeads: 'Open leads',
    kpiDocs: 'Documents needing review',
    none: '—',
    sales: 'Purchases / Sales',
    byProjectCount: 'Purchases by project',
    byProjectAmount: 'Sales amount by project',
    byMonth: 'Purchases by month',
    currentVsHist: 'Current / historical purchases',
    current: 'Current',
    historical: 'Historical unit change',
    investors: 'Investors',
    perInvestor: 'Purchases per investor',
    investorProjects: 'Project distribution',
    leads: 'Leads',
    leadSource: 'Source',
    leadStage: 'Stage',
    leadOwner: 'Owner',
    leadProject: 'Project',
    conversion: 'Conversion',
    won: 'Won',
    lost: 'Lost',
    rate: 'Rate',
    communication: 'Communication',
    byChannel: 'Activity by channel',
    byTime: 'Activity over time',
    byOwner: 'Activity by owner',
    email: 'Email',
    whatsapp: 'WhatsApp',
    calls: 'Calls',
    meetings: 'Meetings',
    tasks: 'Tasks',
    notes: 'Notes',
    taskReport: 'Tasks',
    taskActive: 'Active',
    taskProgress: 'In progress',
    taskDone: 'Completed',
    taskOverdue: 'Overdue',
    documents: 'Documents',
    docTotal: 'Total documents',
    docPerson: 'Person documents',
    docPurchase: 'Purchase documents',
    docHidden: 'Hidden',
    docReview: 'Review required',
    categories: 'Categories',
    exportCsv: 'CSV',
    projectCol: 'Project',
    count: 'Count',
    amount: 'Amount',
    name: 'Person',
    purchases: 'Purchases',
    channel: 'Channel',
    status: 'Status',
    empty: 'No live records for these filters.',
    unavailable: 'Reports could not be loaded.',
  },
} as const;

function dateRange(value: string): { date_from?: string; date_to?: string } {
  if (!value) return {};
  const now = new Date();
  const end = now.toISOString();
  if (value === 'today') {
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return { date_from: start.toISOString(), date_to: end };
  }
  if (value === 'year') {
    const start = new Date(now.getFullYear(), 0, 1);
    return { date_from: start.toISOString(), date_to: end };
  }
  const days = value === '7d' ? 7 : value === '30d' ? 30 : value === '90d' ? 90 : 0;
  if (!days) return {};
  return { date_from: new Date(now.getTime() - days * 86_400_000).toISOString(), date_to: end };
}

function formatMoney(amount: number, currency: string, locale: string): string {
  if (currency === 'unspecified') {
    return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(amount);
  }
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency, maximumFractionDigits: 0 }).format(amount);
  } catch {
    return `${currency} ${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(amount)}`;
  }
}

function formatTotals(totals: CrmReportMoney[], locale: string, empty: string): string {
  if (!totals.length) return empty;
  return totals.map((item) => formatMoney(item.total, item.currency, locale)).join(' · ');
}

function toCsv(headers: string[], rows: Array<Array<string | number>>): string {
  return [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n');
}

function exportCsv(filename: string, headers: string[], rows: Array<Array<string | number>>) {
  downloadCsvFile(filename, toCsv(headers, rows));
}

function chartPoints(rows: CrmReportCount[]): Array<{ key: string; label: string; count: number; href?: string | null }> {
  return rows.map((row) => ({
    key: row.key,
    label: row.label || row.key,
    count: row.count,
    href: row.href,
  }));
}

function KpiLink({
  href,
  label,
  value,
}: {
  href: string;
  label: string;
  value: string | number;
}) {
  return (
    <Link href={href as Route} className="crm-reports__kpi crm-reports__kpi--link">
      <span className="crm-reports__kpi-label">{label}</span>
      <strong className="crm-reports__kpi-value">{value}</strong>
    </Link>
  );
}

function CountTable({
  title,
  keyLabel,
  countLabel,
  rows,
  onExport,
  exportLabel,
}: {
  title: string;
  keyLabel: string;
  countLabel: string;
  rows: CrmReportCount[];
  onExport?: () => void;
  exportLabel: string;
}) {
  return (
    <article className="crm-reports__card">
      <header className="crm-reports__card-head">
        <h2>{title}</h2>
        {onExport ? (
          <Button variant="secondary" size="sm" type="button" onClick={onExport}>
            {exportLabel}
          </Button>
        ) : null}
      </header>
      {rows.length === 0 ? (
        <p className="crm-reports__empty">—</p>
      ) : (
        <table className="crm-reports__table">
          <thead>
            <tr>
              <th>{keyLabel}</th>
              <th>{countLabel}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <td>
                  {row.href ? <Link href={row.href as Route}>{row.label || row.key}</Link> : row.label || row.key}
                </td>
                <td>{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </article>
  );
}

export function CrmReportsLiveWorkspace() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const { authLoading, canRead } = useCrmAccess();
  const [date, setDate] = useState('');
  const [projectGroup, setProjectGroup] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [source, setSource] = useState('');
  const [currency, setCurrency] = useState('');

  const params = useMemo(
    () => ({
      project_group: projectGroup || undefined,
      owner_id: ownerId || undefined,
      source: source || undefined,
      currency: currency || undefined,
      ...dateRange(date),
    }),
    [currency, date, ownerId, projectGroup, source],
  );

  const query = useQuery({
    queryKey: ['crm', 'reports', 'workspace', params],
    queryFn: () => fetchCrmReportsWorkspace(params),
    enabled: !authLoading && canRead,
  });
  const ownersQuery = useQuery({
    queryKey: ['users', 'reports-owners'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canRead,
  });

  const clearFilters = () => {
    setDate('');
    setProjectGroup('');
    setOwnerId('');
    setSource('');
    setCurrency('');
  };

  if (authLoading || query.isLoading) {
    return <LoadingState label={copy.title} />;
  }
  if (query.isError || !query.data) {
    return <ErrorState title={copy.unavailable} message={copy.empty} />;
  }

  const data = query.data;
  const salesValue = formatTotals(data.kpis.sales_totals, locale, copy.none);
  const channelLabels: Record<string, string> = {
    email: copy.email,
    whatsapp: copy.whatsapp,
    call: copy.calls,
    meeting: copy.meetings,
    task: copy.tasks,
    note: copy.notes,
  };
  const taskLabels: Record<string, string> = {
    active: copy.taskActive,
    in_progress: copy.taskProgress,
    completed: copy.taskDone,
    overdue: copy.taskOverdue,
  };
  const docLabels: Record<string, string> = {
    total: copy.docTotal,
    person: copy.docPerson,
    purchase: copy.docPurchase,
    hidden: copy.docHidden,
    review: copy.docReview,
  };

  const amountByProject = data.sales.by_project.map((row) => ({
    key: row.key,
    label: row.label,
    count: row.amounts[0]?.total ? Math.round(row.amounts[0].total) : 0,
  }));

  return (
    <div className="crm-reports crm-reports--live" data-testid="crm-reports-live">
      <header className="crm-reports__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
      </header>

      <section className="crm-reports__filters" aria-label={copy.filters}>
        <Select label={copy.dateRange} value={date} onChange={(event) => setDate(event.target.value)}>
          <option value="">{copy.all}</option>
          <option value="today">{copy.today}</option>
          <option value="7d">{copy.d7}</option>
          <option value="30d">{copy.d30}</option>
          <option value="90d">{copy.d90}</option>
          <option value="year">{copy.year}</option>
        </Select>
        <Select label={copy.project} value={projectGroup} onChange={(event) => setProjectGroup(event.target.value)}>
          <option value="">{copy.all}</option>
          {data.filter_options.projects.map((item) => (
            <option key={item.key} value={item.key}>
              {item.label}
            </option>
          ))}
        </Select>
        <Select label={copy.owner} value={ownerId} onChange={(event) => setOwnerId(event.target.value)}>
          <option value="">{copy.all}</option>
          {(ownersQuery.data?.items ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name || user.email}
            </option>
          ))}
        </Select>
        <Select label={copy.source} value={source} onChange={(event) => setSource(event.target.value)}>
          <option value="">{copy.all}</option>
          {data.filter_options.sources.map((item) => (
            <option key={item.key} value={item.key}>
              {item.label}
            </option>
          ))}
        </Select>
        <Select label={copy.currency} value={currency} onChange={(event) => setCurrency(event.target.value)}>
          <option value="">{copy.all}</option>
          {data.filter_options.currencies.map((item) => (
            <option key={item.key} value={item.key}>
              {item.label}
            </option>
          ))}
        </Select>
        <button type="button" className="crm-reports__clear" onClick={clearFilters}>
          {copy.clear}
        </button>
      </section>

      <section className="crm-reports__kpi-row crm-reports__kpi-row--6" aria-label={copy.title}>
        <KpiLink href="/workspaces/crm/agreements" label={copy.kpiPurchases} value={data.kpis.current_purchases} />
        <KpiLink href="/workspaces/crm/investors" label={copy.kpiInvestors} value={data.kpis.investors} />
        <KpiLink href="/workspaces/crm/agreements" label={copy.kpiSales} value={salesValue} />
        <KpiLink href="/workspaces/crm/tasks" label={copy.kpiTasks} value={data.kpis.active_tasks} />
        <KpiLink href="/workspaces/crm/leads" label={copy.kpiLeads} value={data.kpis.open_leads} />
        <KpiLink href="/workspaces/crm/documents?scope=unresolved" label={copy.kpiDocs} value={data.kpis.documents_review} />
      </section>

      <section className="crm-reports__section" aria-label={copy.sales}>
        <header className="crm-reports__section-head">
          <h2>{copy.sales}</h2>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() =>
              exportCsv(
                'crm-satinalma.csv',
                [copy.projectCol, copy.current, copy.historical, copy.amount],
                data.sales.table.map((row) => [
                  row.label,
                  row.current_count,
                  row.historical_count,
                  formatTotals(row.amounts, locale, copy.none),
                ]),
              )
            }
          >
            {copy.exportCsv}
          </Button>
        </header>
        <div className="crm-reports__grid crm-reports__grid--secondary">
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.byProjectCount}</h2>
            </header>
            {data.sales.by_project.length ? (
              <CountBarChart
                data={data.sales.by_project.map((row) => ({ key: row.key, label: row.label, count: row.current_count }))}
                ariaLabel={copy.byProjectCount}
              />
            ) : (
              <p className="crm-reports__empty">{copy.empty}</p>
            )}
          </article>
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.byProjectAmount}</h2>
            </header>
            {amountByProject.some((row) => row.count > 0) ? (
              <CountBarChart data={amountByProject} ariaLabel={copy.byProjectAmount} />
            ) : (
              <p className="crm-reports__empty">{copy.empty}</p>
            )}
          </article>
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.byMonth}</h2>
            </header>
            {data.sales.by_month.length ? (
              <CountBarChart data={chartPoints(data.sales.by_month)} ariaLabel={copy.byMonth} />
            ) : (
              <p className="crm-reports__empty">{copy.empty}</p>
            )}
          </article>
        </div>
        <article className="crm-reports__card">
          <header className="crm-reports__card-head">
            <h2>{copy.currentVsHist}</h2>
          </header>
          <SplitBarChart
            data={data.sales.by_project.map((row) => ({
              key: row.key,
              label: row.label,
              current: row.current_count,
              previous: row.historical_count,
            }))}
            ariaLabel={copy.currentVsHist}
            currentLabel={copy.current}
            previousLabel={copy.historical}
          />
          <SalesTable rows={data.sales.table} copy={copy} locale={locale} />
        </article>
      </section>

      <section className="crm-reports__section" aria-label={copy.investors}>
        <header className="crm-reports__section-head">
          <h2>{copy.investors}</h2>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() =>
              exportCsv(
                'crm-yatirimci.csv',
                [copy.name, copy.purchases, copy.projectCol, copy.amount],
                data.investors.table.map((row) => [
                  row.name,
                  row.purchases,
                  row.projects.join(' · '),
                  formatTotals(row.amounts, locale, copy.none),
                ]),
              )
            }
          >
            {copy.exportCsv}
          </Button>
        </header>
        <div className="crm-reports__grid crm-reports__grid--secondary">
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.perInvestor}</h2>
            </header>
            {data.investors.purchases_per_investor.length ? (
              <CountBarChart data={chartPoints(data.investors.purchases_per_investor)} ariaLabel={copy.perInvestor} />
            ) : (
              <p className="crm-reports__empty">{copy.empty}</p>
            )}
          </article>
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.investorProjects}</h2>
            </header>
            {data.investors.by_project.length ? (
              <PetrolDonut data={chartPoints(data.investors.by_project)} ariaLabel={copy.investorProjects} />
            ) : (
              <p className="crm-reports__empty">{copy.empty}</p>
            )}
          </article>
          <CountTable
            title={copy.investorProjects}
            keyLabel={copy.projectCol}
            rows={data.investors.by_project}
            countLabel={copy.count}
            exportLabel={copy.exportCsv}
          />
        </div>
        <InvestorTable rows={data.investors.table} copy={copy} locale={locale} />
      </section>

      <section className="crm-reports__section" aria-label={copy.leads}>
        <header className="crm-reports__section-head">
          <h2>{copy.leads}</h2>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() =>
              exportCsv(
                'crm-lead.csv',
                [copy.name, copy.leadSource, copy.leadStage, copy.leadOwner, copy.leadProject],
                data.leads.table.map((row) => [
                  row.name,
                  row.source || copy.none,
                  row.stage,
                  row.owner || copy.none,
                  row.project || copy.none,
                ]),
              )
            }
          >
            {copy.exportCsv}
          </Button>
        </header>
        <div className="crm-reports__grid crm-reports__grid--secondary">
          <CountTable title={copy.leadSource} keyLabel={copy.leadSource} countLabel={copy.count} rows={data.leads.by_source} exportLabel={copy.exportCsv} />
          <CountTable title={copy.leadStage} keyLabel={copy.leadStage} countLabel={copy.count} rows={data.leads.by_stage} exportLabel={copy.exportCsv} />
          <CountTable title={copy.leadOwner} keyLabel={copy.leadOwner} countLabel={copy.count} rows={data.leads.by_owner} exportLabel={copy.exportCsv} />
        </div>
        <div className="crm-reports__grid crm-reports__grid--secondary">
          <CountTable title={copy.leadProject} keyLabel={copy.leadProject} countLabel={copy.count} rows={data.leads.by_project} exportLabel={copy.exportCsv} />
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.conversion}</h2>
            </header>
            {data.leads.conversion.length === 0 ? (
              <p className="crm-reports__empty">{copy.empty}</p>
            ) : (
              <table className="crm-reports__table">
                <thead>
                  <tr>
                    <th>{copy.leadSource}</th>
                    <th>{copy.won}</th>
                    <th>{copy.lost}</th>
                    <th>{copy.rate}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.leads.conversion.map((row) => (
                    <tr key={row.key}>
                      <td>{row.label}</td>
                      <td>{row.won}</td>
                      <td>{row.lost}</td>
                      <td>{row.rate == null ? copy.none : `${Math.round(row.rate * 100)}%`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </article>
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.leads}</h2>
            </header>
            {data.leads.table.length === 0 ? (
              <p className="crm-reports__empty">{copy.empty}</p>
            ) : (
              <table className="crm-reports__table">
                <thead>
                  <tr>
                    <th>{copy.name}</th>
                    <th>{copy.leadSource}</th>
                    <th>{copy.leadStage}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.leads.table.slice(0, 12).map((row) => (
                    <tr key={row.id}>
                      <td>
                        <Link href={(row.href || '/workspaces/crm/leads') as Route}>{row.name}</Link>
                      </td>
                      <td>{row.source || copy.none}</td>
                      <td>{row.stage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </article>
        </div>
      </section>

      <section className="crm-reports__section" aria-label={copy.communication}>
        <header className="crm-reports__section-head">
          <h2>{copy.communication}</h2>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() =>
              exportCsv(
                'crm-iletisim.csv',
                [copy.channel, copy.count],
                data.communication.table.map((row) => [channelLabels[row.key] || row.label || row.key, row.count]),
              )
            }
          >
            {copy.exportCsv}
          </Button>
        </header>
        <div className="crm-reports__grid crm-reports__grid--secondary">
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.byChannel}</h2>
            </header>
            <PetrolDonut
              data={data.communication.by_channel.map((row) => ({
                key: row.key,
                label: channelLabels[row.key] || row.label || row.key,
                count: row.count,
              }))}
              ariaLabel={copy.byChannel}
            />
          </article>
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.byTime}</h2>
            </header>
            {data.communication.by_month.length ? (
              <CountBarChart data={chartPoints(data.communication.by_month)} ariaLabel={copy.byTime} />
            ) : (
              <p className="crm-reports__empty">{copy.empty}</p>
            )}
          </article>
          <CountTable
            title={copy.byOwner}
            keyLabel={copy.owner}
            rows={data.communication.by_owner}
            countLabel={copy.count}
            exportLabel={copy.exportCsv}
          />
        </div>
        <CountTable
          title={copy.byChannel}
          keyLabel={copy.channel}
          rows={data.communication.table.map((row) => ({ ...row, label: channelLabels[row.key] || row.label }))}
          countLabel={copy.count}
          onExport={() =>
            exportCsv(
              'crm-iletisim-kanal.csv',
              [copy.channel, copy.count],
              data.communication.table.map((row) => [channelLabels[row.key] || row.key, row.count]),
            )
          }
          exportLabel={copy.exportCsv}
        />
      </section>

      <section className="crm-reports__section" aria-label={copy.taskReport}>
        <header className="crm-reports__section-head">
          <h2>{copy.taskReport}</h2>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() =>
              exportCsv(
                'crm-gorev.csv',
                [copy.status, copy.count],
                data.tasks.table.map((row) => [taskLabels[row.key] || row.key, row.count]),
              )
            }
          >
            {copy.exportCsv}
          </Button>
        </header>
        <div className="crm-reports__grid crm-reports__grid--secondary">
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.taskReport}</h2>
            </header>
            <CountBarChart
              data={data.tasks.table.map((row) => ({
                key: row.key,
                label: taskLabels[row.key] || row.label || row.key,
                count: row.count,
              }))}
              ariaLabel={copy.taskReport}
            />
          </article>
          <CountTable
            title={copy.byOwner}
            keyLabel={copy.owner}
            rows={data.tasks.by_owner}
            countLabel={copy.count}
            exportLabel={copy.exportCsv}
          />
          <CountTable
            title={copy.status}
            keyLabel={copy.status}
            rows={data.tasks.table.map((row) => ({ ...row, label: taskLabels[row.key] || row.label }))}
            countLabel={copy.count}
            exportLabel={copy.exportCsv}
          />
        </div>
      </section>

      <section className="crm-reports__section" aria-label={copy.documents}>
        <header className="crm-reports__section-head">
          <h2>{copy.documents}</h2>
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() =>
              exportCsv(
                'crm-belge.csv',
                [copy.status, copy.count],
                data.documents.table.map((row) => [docLabels[row.key] || row.key, row.count]),
              )
            }
          >
            {copy.exportCsv}
          </Button>
        </header>
        <div className="crm-reports__grid crm-reports__grid--secondary">
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.categories}</h2>
            </header>
            {data.documents.by_category.length ? (
              <PetrolDonut data={chartPoints(data.documents.by_category)} ariaLabel={copy.categories} />
            ) : (
              <p className="crm-reports__empty">{copy.empty}</p>
            )}
          </article>
          <article className="crm-reports__card">
            <header className="crm-reports__card-head">
              <h2>{copy.projectCol}</h2>
            </header>
            {data.documents.by_project.length ? (
              <CountBarChart data={chartPoints(data.documents.by_project)} ariaLabel={copy.projectCol} />
            ) : (
              <p className="crm-reports__empty">{copy.empty}</p>
            )}
          </article>
          <CountTable
            title={copy.documents}
            keyLabel={copy.status}
            rows={data.documents.table.map((row) => ({ ...row, label: docLabels[row.key] || row.label }))}
            countLabel={copy.count}
            exportLabel={copy.exportCsv}
          />
        </div>
      </section>
    </div>
  );
}

function SalesTable({
  rows,
  copy,
  locale,
}: {
  rows: CrmReportsSalesRow[];
  copy: (typeof COPY)['tr'];
  locale: string;
}) {
  return (
    <table className="crm-reports__table">
      <thead>
        <tr>
          <th>{copy.projectCol}</th>
          <th>{copy.current}</th>
          <th>{copy.historical}</th>
          <th>{copy.amount}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.key}>
            <td>
              <Link href={(row.href || '/workspaces/crm/agreements') as Route}>{row.label}</Link>
            </td>
            <td>{row.current_count}</td>
            <td>{row.historical_count}</td>
            <td>{formatTotals(row.amounts, locale, copy.none)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function InvestorTable({
  rows,
  copy,
  locale,
}: {
  rows: CrmReportsInvestorRow[];
  copy: (typeof COPY)['tr'];
  locale: string;
}) {
  return (
    <article className="crm-reports__card">
      <table className="crm-reports__table">
        <thead>
          <tr>
            <th>{copy.name}</th>
            <th>{copy.purchases}</th>
            <th>{copy.projectCol}</th>
            <th>{copy.amount}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.contact_id}>
              <td>
                <Link href={(row.href || '/workspaces/crm/investors') as Route}>{row.name}</Link>
              </td>
              <td>{row.purchases}</td>
              <td>{row.projects.join(' · ') || copy.none}</td>
              <td>{formatTotals(row.amounts, locale, copy.none)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </article>
  );
}

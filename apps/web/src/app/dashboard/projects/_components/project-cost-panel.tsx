'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import {
  createCommitment,
  createVendor,
  fetchCostSummary,
  fetchProjectCommitments,
  fetchProjectPayments,
  fetchProjectVendorBills,
  fetchRetainageSummary,
  formatMetricCurrency,
  formatShortDate,
  transitionCommitment,
  transitionVendorBill,
  type CostSummary,
  type ProjectCommitment,
  type ProjectPayment,
  type ProjectVendorBill,
  type RetainageSummary,
} from '@/lib/api/projects';

export type CostSubTab = 'commitments' | 'bills' | 'payments' | 'retainage';

interface ProjectCostPanelProps {
  projectId: string;
  locale: string;
  subTab: CostSubTab;
}

export function ProjectCostPanel({ projectId, locale, subTab }: ProjectCostPanelProps) {
  const t = useTranslations('projects');
  const tCommon = useTranslations('common');
  const na = t('notAvailable');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null);
  const [commitments, setCommitments] = useState<ProjectCommitment[]>([]);
  const [bills, setBills] = useState<ProjectVendorBill[]>([]);
  const [payments, setPayments] = useState<ProjectPayment[]>([]);
  const [retainage, setRetainage] = useState<RetainageSummary | null>(null);
  const [quickVendorName, setQuickVendorName] = useState('');
  const [quickCommitmentTitle, setQuickCommitmentTitle] = useState('GC Contract');
  const [lastVendorId, setLastVendorId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, commitmentData, billData, paymentData, retainageData] =
        await Promise.all([
          fetchCostSummary(projectId),
          fetchProjectCommitments(projectId),
          fetchProjectVendorBills(projectId),
          fetchProjectPayments(projectId),
          fetchRetainageSummary(projectId),
        ]);
      setCostSummary(summaryData);
      setCommitments(commitmentData.items);
      setBills(billData.items);
      setPayments(paymentData.items);
      setRetainage(retainageData);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('detailWorkspace.tabLoadError'));
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('detailWorkspace.actionError'));
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <LoadingState label={t('detailWorkspace.loadingTab')} />;
  }

  if (error && !costSummary) {
    return (
      <ErrorState
        title={t('detailWorkspace.tabLoadError')}
        message={error}
        action={
          <Button type="button" onClick={() => void load()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  return (
    <div className="project-cost-panel project-detail__stack">
      {error ? <p className="project-detail__error">{error}</p> : null}

      {subTab === 'commitments' ? (
        <>
          <section className="project-detail__card">
            <h3>{t('costTracking.quickVendor')}</h3>
            <div className="project-detail__toolbar">
              <input
                value={quickVendorName}
                onChange={(event) => setQuickVendorName(event.target.value)}
                placeholder={t('costTracking.vendorName')}
                aria-label={t('costTracking.vendorName')}
              />
              <Button
                type="button"
                disabled={busy || !quickVendorName.trim()}
                onClick={() =>
                  void run(async () => {
                    const vendor = await createVendor({
                      name: quickVendorName.trim(),
                      vendor_code: `V-${Date.now().toString().slice(-6)}`,
                    });
                    setLastVendorId(vendor.id);
                    setQuickVendorName('');
                  })
                }
              >
                {t('costTracking.createVendor')}
              </Button>
            </div>
            {lastVendorId ? (
              <p className="project-detail__note">
                {t('costTracking.lastVendor')}: {lastVendorId}
              </p>
            ) : null}
          </section>

          <section className="project-detail__card">
            <h3>{t('costTracking.commitments')}</h3>
            {commitments.length === 0 ? (
              <EmptyState
                title={t('costTracking.empty.commitments')}
                description={t('costTracking.empty.commitmentsHint')}
              />
            ) : (
              <div className="project-detail__table-wrap">
                <table className="project-detail__table">
                  <thead>
                    <tr>
                      <th>{t('costTracking.columns.number')}</th>
                      <th>{t('costTracking.columns.type')}</th>
                      <th>{t('costTracking.columns.title')}</th>
                      <th>{t('costTracking.columns.status')}</th>
                      <th>{t('costTracking.columns.current')}</th>
                      <th>{t('costTracking.columns.invoiced')}</th>
                      <th>{t('costTracking.columns.paid')}</th>
                      <th>{t('costTracking.columns.actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commitments.map((item) => (
                      <tr key={item.id}>
                        <td>{item.commitment_number}</td>
                        <td>{item.commitment_type}</td>
                        <td>{item.title}</td>
                        <td>
                          <StatusChip
                            tone={
                              item.status === 'active' || item.status === 'approved'
                                ? 'success'
                                : item.status === 'rejected' || item.status === 'cancelled'
                                  ? 'danger'
                                  : 'default'
                            }
                          >
                            {item.status}
                          </StatusChip>
                        </td>
                        <td>
                          {formatMetricCurrency(
                            {
                              value: item.current_committed_amount,
                              available: true,
                              reason: null,
                            },
                            locale,
                            na,
                          )}
                        </td>
                        <td>
                          {formatMetricCurrency(
                            { value: item.invoiced_amount, available: true, reason: null },
                            locale,
                            na,
                          )}
                        </td>
                        <td>
                          {formatMetricCurrency(
                            { value: item.paid_amount, available: true, reason: null },
                            locale,
                            na,
                          )}
                        </td>
                        <td>
                          <div className="project-detail__row-actions">
                            {item.status === 'draft' ? (
                              <Button
                                type="button"
                                variant="secondary"
                                disabled={busy}
                                onClick={() =>
                                  void run(() =>
                                    transitionCommitment(projectId, item.id, 'submit'),
                                  )
                                }
                              >
                                {t('costTracking.actions.submit')}
                              </Button>
                            ) : null}
                            {item.status === 'in_review' ? (
                              <Button
                                type="button"
                                disabled={busy}
                                onClick={() =>
                                  void run(() =>
                                    transitionCommitment(projectId, item.id, 'approve'),
                                  )
                                }
                              >
                                {t('costTracking.actions.approve')}
                              </Button>
                            ) : null}
                            {item.status === 'approved' ? (
                              <Button
                                type="button"
                                variant="secondary"
                                disabled={busy}
                                onClick={() =>
                                  void run(() =>
                                    transitionCommitment(projectId, item.id, 'execute'),
                                  )
                                }
                              >
                                {t('costTracking.actions.execute')}
                              </Button>
                            ) : null}
                            {item.status === 'executed' ? (
                              <Button
                                type="button"
                                variant="secondary"
                                disabled={busy}
                                onClick={() =>
                                  void run(() =>
                                    transitionCommitment(projectId, item.id, 'activate'),
                                  )
                                }
                              >
                                {t('costTracking.actions.activate')}
                              </Button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="project-detail__note">{t('costTracking.commitmentHint')}</p>
            {lastVendorId ? (
              <div className="project-detail__toolbar">
                <input
                  value={quickCommitmentTitle}
                  onChange={(event) => setQuickCommitmentTitle(event.target.value)}
                  aria-label={t('costTracking.commitmentTitle')}
                />
                <Button
                  type="button"
                  disabled={busy || !quickCommitmentTitle.trim()}
                  onClick={() =>
                    void run(async () => {
                      // Lines require a budget line — create draft shell via API with empty lines fails
                      // validation on submit; create without lines for draft scaffolding only when
                      // budget lines exist from Financials Budget tab.
                      const summary = await fetchCostSummary(projectId);
                      void summary;
                      await createCommitment(projectId, {
                        vendor_id: lastVendorId,
                        commitment_type: 'contract',
                        title: quickCommitmentTitle.trim(),
                        lines: [],
                      });
                    })
                  }
                >
                  {t('costTracking.createDraftCommitment')}
                </Button>
              </div>
            ) : null}
          </section>
        </>
      ) : null}

      {subTab === 'bills' ? (
        <section className="project-detail__card">
          <h3>{t('costTracking.bills')}</h3>
          {bills.length === 0 ? (
            <EmptyState title={t('costTracking.empty.bills')} />
          ) : (
            <div className="project-detail__table-wrap">
              <table className="project-detail__table">
                <thead>
                  <tr>
                    <th>{t('costTracking.columns.number')}</th>
                    <th>{t('costTracking.columns.invoice')}</th>
                    <th>{t('costTracking.columns.status')}</th>
                    <th>{t('costTracking.columns.invoiceDate')}</th>
                    <th>{t('costTracking.columns.dueDate')}</th>
                    <th>{t('costTracking.columns.approved')}</th>
                    <th>{t('costTracking.columns.balance')}</th>
                    <th>{t('costTracking.columns.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {bills.map((bill) => {
                    const overdue =
                      bill.due_date &&
                      bill.balance_due &&
                      Number(bill.balance_due) > 0 &&
                      !['paid', 'void', 'archived'].includes(bill.status) &&
                      new Date(bill.due_date) < new Date();
                    return (
                      <tr key={bill.id}>
                        <td>{bill.bill_number}</td>
                        <td>{bill.vendor_invoice_number}</td>
                        <td>
                          <StatusChip tone={overdue ? 'danger' : 'default'}>
                            {overdue ? t('costTracking.overdue') : bill.status}
                          </StatusChip>
                        </td>
                        <td>{formatShortDate(bill.invoice_date, locale)}</td>
                        <td>{formatShortDate(bill.due_date, locale)}</td>
                        <td>
                          {formatMetricCurrency(
                            { value: bill.approved_amount, available: true, reason: null },
                            locale,
                            na,
                          )}
                        </td>
                        <td>
                          {formatMetricCurrency(
                            { value: bill.balance_due, available: true, reason: null },
                            locale,
                            na,
                          )}
                        </td>
                        <td>
                          <div className="project-detail__row-actions">
                            {bill.status === 'draft' ? (
                              <Button
                                type="button"
                                variant="secondary"
                                disabled={busy}
                                onClick={() =>
                                  void run(() => transitionVendorBill(projectId, bill.id, 'submit'))
                                }
                              >
                                {t('costTracking.actions.submit')}
                              </Button>
                            ) : null}
                            {bill.status === 'in_review' ? (
                              <Button
                                type="button"
                                disabled={busy}
                                onClick={() =>
                                  void run(() =>
                                    transitionVendorBill(projectId, bill.id, 'approve'),
                                  )
                                }
                              >
                                {t('costTracking.actions.approve')}
                              </Button>
                            ) : null}
                            {bill.status === 'approved' ? (
                              <Button
                                type="button"
                                disabled={busy}
                                onClick={() =>
                                  void run(() => transitionVendorBill(projectId, bill.id, 'post'))
                                }
                              >
                                {t('costTracking.actions.post')}
                              </Button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}

      {subTab === 'payments' ? (
        <section className="project-detail__card">
          <h3>{t('costTracking.payments')}</h3>
          {payments.length === 0 ? (
            <EmptyState title={t('costTracking.empty.payments')} />
          ) : (
            <div className="project-detail__table-wrap">
              <table className="project-detail__table">
                <thead>
                  <tr>
                    <th>{t('costTracking.columns.number')}</th>
                    <th>{t('costTracking.columns.date')}</th>
                    <th>{t('costTracking.columns.method')}</th>
                    <th>{t('costTracking.columns.status')}</th>
                    <th>{t('costTracking.columns.amount')}</th>
                    <th>{t('costTracking.columns.reference')}</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.map((payment) => (
                    <tr key={payment.id}>
                      <td>{payment.payment_number}</td>
                      <td>{formatShortDate(payment.payment_date, locale)}</td>
                      <td>{payment.payment_method}</td>
                      <td>{payment.status}</td>
                      <td>
                        {formatMetricCurrency(
                          { value: payment.gross_amount, available: true, reason: null },
                          locale,
                          na,
                        )}
                      </td>
                      <td>{payment.reference_number ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}

      {subTab === 'retainage' ? (
        <section className="project-detail__card">
          <h3>{t('costTracking.retainage')}</h3>
          {retainage ? (
            <div className="project-detail__metrics">
              {(
                [
                  ['total_retained', retainage.total_retained],
                  ['total_released', retainage.total_released],
                  ['outstanding_retainage', retainage.outstanding_retainage],
                ] as const
              ).map(([key, metric]) => (
                <article key={key} className="project-detail__metric">
                  <p className="project-detail__metric-label">
                    {t(`costTracking.retainageTotals.${key}`)}
                  </p>
                  <p className="project-detail__metric-value">
                    {formatMetricCurrency(metric, locale, na)}
                  </p>
                  {!metric.available && metric.reason ? (
                    <p className="project-detail__metric-note">{metric.reason}</p>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title={t('costTracking.empty.retainage')} />
          )}
          <p className="project-detail__note">{t('costTracking.retainageHint')}</p>
        </section>
      ) : null}
    </div>
  );
}

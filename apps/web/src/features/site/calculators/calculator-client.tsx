'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  calc1031,
  calcAppreciation,
  calcCashFlow,
  calcMortgage,
  calcRefinance,
  calcRentalYield,
  calcRoi,
  fmtMoney,
  fmtPct,
  type CalculatorSlug,
} from '@/features/site/calculators/math';
import { buildShareUrl } from '@/features/site/lib/lead-submit';

type NumMap = Record<string, number>;

const DEFAULTS: Record<CalculatorSlug, NumMap> = {
  roi: { totalInvested: 250000, totalReturned: 320000, years: 5 },
  'cash-flow': { monthlyRent: 2200, vacancyPct: 5, monthlyOpex: 350, monthlyDebt: 1100 },
  'rental-yield': { purchasePrice: 280000, annualRent: 18000, annualCosts: 3500 },
  mortgage: { principal: 200000, annualRatePct: 4.5, years: 20 },
  refinance: {
    currentPayment: 1400,
    newPrincipal: 190000,
    newRatePct: 3.9,
    newYears: 20,
    closingCosts: 4500,
  },
  appreciation: { currentValue: 300000, annualPct: 4, years: 7 },
  '1031': {
    salePrice: 500000,
    adjustedBasis: 320000,
    sellingCosts: 25000,
    replacementPrice: 520000,
  },
};

const FIELD_KEYS: Record<CalculatorSlug, string[]> = {
  roi: ['totalInvested', 'totalReturned', 'years'],
  'cash-flow': ['monthlyRent', 'vacancyPct', 'monthlyOpex', 'monthlyDebt'],
  'rental-yield': ['purchasePrice', 'annualRent', 'annualCosts'],
  mortgage: ['principal', 'annualRatePct', 'years'],
  refinance: ['currentPayment', 'newPrincipal', 'newRatePct', 'newYears', 'closingCosts'],
  appreciation: ['currentValue', 'annualPct', 'years'],
  '1031': ['salePrice', 'adjustedBasis', 'sellingCosts', 'replacementPrice'],
};

export function CalculatorClient({ slug }: { slug: CalculatorSlug }) {
  const t = useTranslations('site.calculators');
  const [values, setValues] = useState<NumMap>(() => ({ ...DEFAULTS[slug] }));
  const [shared, setShared] = useState(false);

  const results = useMemo(() => {
    switch (slug) {
      case 'roi': {
        const r = calcRoi(values as never);
        return [
          { key: 'profit', value: fmtMoney(r.profit) },
          { key: 'simpleRoi', value: fmtPct(r.simple) },
          { key: 'annualizedRoi', value: fmtPct(r.annualized) },
        ];
      }
      case 'rental-yield': {
        const r = calcRentalYield(values as never);
        return [
          { key: 'grossYield', value: fmtPct(r.gross) },
          { key: 'netYield', value: fmtPct(r.net) },
          { key: 'netIncome', value: fmtMoney(r.netIncome) },
        ];
      }
      case 'mortgage': {
        const r = calcMortgage(values as never);
        return [
          { key: 'payment', value: fmtMoney(r.payment) },
          { key: 'totalInterest', value: fmtMoney(r.totalInterest) },
          { key: 'totalPaid', value: fmtMoney(r.totalPaid) },
        ];
      }
      case 'cash-flow': {
        const r = calcCashFlow(values as never);
        return [
          { key: 'effectiveRent', value: fmtMoney(r.effectiveRent) },
          { key: 'monthlyCashFlow', value: fmtMoney(r.monthly) },
          { key: 'annualCashFlow', value: fmtMoney(r.annual) },
        ];
      }
      case 'refinance': {
        const r = calcRefinance(values as never);
        return [
          { key: 'newPayment', value: fmtMoney(r.newPayment) },
          { key: 'monthlySavings', value: fmtMoney(r.monthlySavings) },
          {
            key: 'breakEven',
            value: Number.isFinite(r.breakEvenMonths) ? r.breakEvenMonths.toFixed(1) : '—',
          },
        ];
      }
      case 'appreciation': {
        const r = calcAppreciation(values as never);
        return [
          { key: 'futureValue', value: fmtMoney(r.future) },
          { key: 'gain', value: fmtMoney(r.gain) },
        ];
      }
      case '1031': {
        const r = calc1031(values as never);
        return [
          { key: 'realizedGain', value: fmtMoney(r.realizedGain) },
          { key: 'boot', value: fmtMoney(r.boot) },
          { key: 'deferred', value: fmtMoney(r.deferredEstimate) },
        ];
      }
      default:
        return [];
    }
  }, [slug, values]);

  const summary = results.map((r) => `${t(`metrics.${r.key}`)}: ${r.value}`).join(' | ');

  const onShare = async () => {
    const params: Record<string, string> = {};
    for (const [k, v] of Object.entries(values)) params[k] = String(v);
    const url = buildShareUrl(`/calculators/${slug}`, params);
    try {
      await navigator.clipboard.writeText(url);
      setShared(true);
      setTimeout(() => setShared(false), 2000);
    } catch {
      window.prompt('Share URL', url);
    }
  };

  return (
    <div className="site-calc">
      <div className="site-calc__panel">
        <h2>{t('inputs')}</h2>
        <div className="site-calc__fields">
          {FIELD_KEYS[slug].map((key) => (
            <label key={key} className="site-calc__field">
              <span>{t(`fields.${key}`)}</span>
              <input
                type="number"
                value={Number.isFinite(values[key]) ? values[key] : ''}
                onChange={(e) =>
                  setValues((prev) => ({ ...prev, [key]: Number(e.target.value) }))
                }
              />
            </label>
          ))}
        </div>
      </div>

      <div className="site-calc__panel">
        <h2>{t('results')}</h2>
        <div className="site-calc__results">
          {results.map((r) => (
            <div key={r.key} className="site-calc__result">
              <span>{t(`metrics.${r.key}`)}</span>
              <strong>{r.value}</strong>
            </div>
          ))}
        </div>
        <div className="site-calc__actions">
          <button type="button" className="site-btn site-btn--ghost" onClick={onShare}>
            {shared ? t('shared') : t('share')}
          </button>
          <Link
            href={
              `/lead/calculator?calculator=${slug}&results_summary=${encodeURIComponent(summary)}` as Route
            }
            className="site-btn site-btn--primary"
          >
            {t('saveLead')}
          </Link>
        </div>
        <p className="site-note" style={{ marginTop: '1.25rem' }}>
          {t('disclaimer')}
        </p>
      </div>
    </div>
  );
}

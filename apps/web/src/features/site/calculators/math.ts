export type CalculatorSlug =
  | 'roi'
  | 'cash-flow'
  | 'rental-yield'
  | 'mortgage'
  | 'refinance'
  | 'appreciation'
  | '1031';

export type CalculatorMeta = {
  slug: CalculatorSlug;
  title: { en: string; tr: string };
  description: { en: string; tr: string };
  icon: string;
};

export const SITE_CALCULATORS: CalculatorMeta[] = [
  {
    slug: 'roi',
    title: { en: 'ROI', tr: 'ROI' },
    description: {
      en: 'Estimate simple and annualized return on invested capital.',
      tr: 'Yatırılan sermaye için basit ve yıllıklandırılmış getiriyi tahmin edin.',
    },
    icon: 'roi',
  },
  {
    slug: 'cash-flow',
    title: { en: 'Cash flow', tr: 'Nakit akışı' },
    description: {
      en: 'Monthly income after mortgage, vacancy, and operating costs.',
      tr: 'Mortgage, boşluk ve işletme giderlerinden sonra aylık gelir.',
    },
    icon: 'cash',
  },
  {
    slug: 'rental-yield',
    title: { en: 'Rental yield', tr: 'Kira getirisi' },
    description: {
      en: 'Gross and net yield from purchase price and annual rent.',
      tr: 'Alış fiyatı ve yıllık kiradan brüt ve net getiri.',
    },
    icon: 'yield',
  },
  {
    slug: 'mortgage',
    title: { en: 'Mortgage', tr: 'Mortgage' },
    description: {
      en: 'Payment estimate from principal, rate, and term.',
      tr: 'Anapara, faiz ve vade ile ödeme tahmini.',
    },
    icon: 'mortgage',
  },
  {
    slug: 'refinance',
    title: { en: 'Refinance', tr: 'Refinansman' },
    description: {
      en: 'Compare current vs new loan payments and break-even months.',
      tr: 'Mevcut ve yeni kredi ödemelerini ve başabaş ayını karşılaştırın.',
    },
    icon: 'refi',
  },
  {
    slug: 'appreciation',
    title: { en: 'Appreciation', tr: 'Değer artışı' },
    description: {
      en: 'Project future value from annual appreciation assumptions.',
      tr: 'Yıllık değer artışı varsayımlarıyla gelecekteki değeri projekte edin.',
    },
    icon: 'growth',
  },
  {
    slug: '1031',
    title: { en: '1031 exchange', tr: '1031 değişimi' },
    description: {
      en: 'Scenario framing for deferred gain — educational, not tax advice.',
      tr: 'Ertelenmiş kazanç senaryosu — eğitici, vergi tavsiyesi değil.',
    },
    icon: '1031',
  },
];

export function getCalculator(slug: string): CalculatorMeta | undefined {
  return SITE_CALCULATORS.find((c) => c.slug === slug);
}

export function fmtMoney(n: number, currency = 'EUR'): string {
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(n);
}

export function fmtPct(n: number, digits = 2): string {
  if (!Number.isFinite(n)) return '—';
  return `${n.toFixed(digits)}%`;
}

export function calcRoi(params: {
  totalInvested: number;
  totalReturned: number;
  years: number;
}) {
  const { totalInvested, totalReturned, years } = params;
  const profit = totalReturned - totalInvested;
  const simple = totalInvested > 0 ? (profit / totalInvested) * 100 : NaN;
  const annualized =
    totalInvested > 0 && years > 0
      ? (Math.pow(totalReturned / totalInvested, 1 / years) - 1) * 100
      : NaN;
  return { profit, simple, annualized };
}

export function calcRentalYield(params: {
  purchasePrice: number;
  annualRent: number;
  annualCosts: number;
}) {
  const { purchasePrice, annualRent, annualCosts } = params;
  const gross = purchasePrice > 0 ? (annualRent / purchasePrice) * 100 : NaN;
  const net = purchasePrice > 0 ? ((annualRent - annualCosts) / purchasePrice) * 100 : NaN;
  return { gross, net, netIncome: annualRent - annualCosts };
}

export function calcMortgage(params: {
  principal: number;
  annualRatePct: number;
  years: number;
}) {
  const { principal, annualRatePct, years } = params;
  const n = years * 12;
  const r = annualRatePct / 100 / 12;
  if (principal <= 0 || n <= 0) return { payment: NaN, totalPaid: NaN, totalInterest: NaN };
  if (r === 0) {
    const payment = principal / n;
    return { payment, totalPaid: payment * n, totalInterest: 0 };
  }
  const payment = (principal * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
  const totalPaid = payment * n;
  return { payment, totalPaid, totalInterest: totalPaid - principal };
}

export function calcCashFlow(params: {
  monthlyRent: number;
  vacancyPct: number;
  monthlyOpex: number;
  monthlyDebt: number;
}) {
  const effectiveRent = params.monthlyRent * (1 - params.vacancyPct / 100);
  const monthly = effectiveRent - params.monthlyOpex - params.monthlyDebt;
  return { effectiveRent, monthly, annual: monthly * 12 };
}

export function calcRefinance(params: {
  currentPayment: number;
  newPrincipal: number;
  newRatePct: number;
  newYears: number;
  closingCosts: number;
}) {
  const next = calcMortgage({
    principal: params.newPrincipal,
    annualRatePct: params.newRatePct,
    years: params.newYears,
  });
  const monthlySavings = params.currentPayment - next.payment;
  const breakEvenMonths =
    monthlySavings > 0 ? params.closingCosts / monthlySavings : Number.POSITIVE_INFINITY;
  return { newPayment: next.payment, monthlySavings, breakEvenMonths };
}

export function calcAppreciation(params: {
  currentValue: number;
  annualPct: number;
  years: number;
}) {
  const future = params.currentValue * Math.pow(1 + params.annualPct / 100, params.years);
  const gain = future - params.currentValue;
  return { future, gain };
}

export function calc1031(params: {
  salePrice: number;
  adjustedBasis: number;
  sellingCosts: number;
  replacementPrice: number;
}) {
  const realizedGain = params.salePrice - params.adjustedBasis - params.sellingCosts;
  const reinvested = params.replacementPrice;
  const boot = Math.max(0, params.salePrice - params.sellingCosts - reinvested);
  const deferredEstimate = Math.max(0, realizedGain - boot);
  return { realizedGain, boot, deferredEstimate };
}

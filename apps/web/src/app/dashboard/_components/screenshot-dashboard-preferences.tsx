'use client';

import { useLocale } from 'next-intl';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import { useCompanyBranding } from '@/lib/company/company-context';

export const DASHBOARD_DENSITIES = ['compact', 'comfortable', 'large'] as const;
export type DashboardDensity = (typeof DASHBOARD_DENSITIES)[number];

export const DASHBOARD_CURRENCIES = ['USD', 'EUR', 'TRY', 'GBP', 'AED'] as const;
export type DashboardCurrency = (typeof DASHBOARD_CURRENCIES)[number];

const DENSITY_STORAGE_KEY = 'investhome-dashboard-density';
const CURRENCY_STORAGE_KEY = 'investhome-dashboard-currency';

const DEMO_USD_EXCHANGE_RATES: Readonly<Record<DashboardCurrency, number>> = {
  USD: 1,
  EUR: 0.92,
  TRY: 32.6,
  GBP: 0.79,
  AED: 3.67,
};

type CurrencyFormat = 'standard' | 'compact';

type DashboardPreferencesContextValue = {
  density: DashboardDensity;
  setDensity: (density: DashboardDensity) => void;
  currency: DashboardCurrency;
  setCurrency: (currency: DashboardCurrency) => void;
  formatCurrency: (baseUsdValue: number, format?: CurrencyFormat) => string;
  formatUsdCurrency: (value: number, format?: CurrencyFormat) => string;
};

const DashboardPreferencesContext = createContext<DashboardPreferencesContextValue | null>(null);

function isDashboardDensity(value: string | null): value is DashboardDensity {
  return DASHBOARD_DENSITIES.includes(value as DashboardDensity);
}

function isDashboardCurrency(value: string | null | undefined): value is DashboardCurrency {
  return DASHBOARD_CURRENCIES.includes(value as DashboardCurrency);
}

export function ScreenshotDashboardPreferencesProvider({
  children,
  applyDocumentAttributes = true,
}: {
  children: ReactNode;
  applyDocumentAttributes?: boolean;
}) {
  const locale = useLocale();
  const { context } = useCompanyBranding();
  const [density, setDensityState] = useState<DashboardDensity>('comfortable');
  const [currency, setCurrencyState] = useState<DashboardCurrency>('USD');
  const hasStoredCurrency = useRef(false);

  useEffect(() => {
    try {
      const storedDensity = localStorage.getItem(DENSITY_STORAGE_KEY);
      const storedCurrency = localStorage.getItem(CURRENCY_STORAGE_KEY);
      if (isDashboardDensity(storedDensity)) {
        setDensityState(storedDensity);
      }
      if (isDashboardCurrency(storedCurrency)) {
        hasStoredCurrency.current = true;
        setCurrencyState(storedCurrency);
      }
    } catch {
      hasStoredCurrency.current = false;
    }
  }, []);

  useEffect(() => {
    if (!hasStoredCurrency.current && isDashboardCurrency(context?.default_currency)) {
      setCurrencyState(context.default_currency);
    }
  }, [context?.default_currency]);

  useEffect(() => {
    if (!applyDocumentAttributes) {
      return;
    }
    document.documentElement.dataset.dashboardDensity = density;
    document.documentElement.dataset.dashboardCurrency = currency;
    return () => {
      delete document.documentElement.dataset.dashboardDensity;
      delete document.documentElement.dataset.dashboardCurrency;
    };
  }, [applyDocumentAttributes, currency, density]);

  const setDensity = useCallback((nextDensity: DashboardDensity) => {
    setDensityState(nextDensity);
    try {
      localStorage.setItem(DENSITY_STORAGE_KEY, nextDensity);
    } catch {
      /* Local persistence is best-effort. */
    }
  }, []);

  const setCurrency = useCallback((nextCurrency: DashboardCurrency) => {
    hasStoredCurrency.current = true;
    setCurrencyState(nextCurrency);
    try {
      localStorage.setItem(CURRENCY_STORAGE_KEY, nextCurrency);
    } catch {
      /* Local persistence is best-effort. */
    }
  }, []);

  const localeName = locale === 'tr' ? 'tr-TR' : 'en-US';
  const standardFormatter = useMemo(
    () =>
      new Intl.NumberFormat(localeName, {
        style: 'currency',
        currency,
        maximumFractionDigits: 0,
      }),
    [currency, localeName],
  );
  const compactFormatter = useMemo(
    () =>
      new Intl.NumberFormat(localeName, {
        style: 'currency',
        currency,
        notation: 'compact',
        maximumFractionDigits: 1,
      }),
    [currency, localeName],
  );
  const usdStandardFormatter = useMemo(
    () =>
      new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0,
      }),
    [],
  );
  const usdCompactFormatter = useMemo(
    () =>
      new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        notation: 'compact',
        maximumFractionDigits: 1,
      }),
    [],
  );

  const formatCurrency = useCallback(
    (baseUsdValue: number, format: CurrencyFormat = 'standard') => {
      const converted = baseUsdValue * DEMO_USD_EXCHANGE_RATES[currency];
      return (format === 'compact' ? compactFormatter : standardFormatter).format(converted);
    },
    [compactFormatter, currency, standardFormatter],
  );
  const formatUsdCurrency = useCallback(
    (value: number, format: CurrencyFormat = 'standard') =>
      (format === 'compact' ? usdCompactFormatter : usdStandardFormatter).format(value),
    [usdCompactFormatter, usdStandardFormatter],
  );

  const value = useMemo(
    () => ({ density, setDensity, currency, setCurrency, formatCurrency, formatUsdCurrency }),
    [currency, density, formatCurrency, formatUsdCurrency, setCurrency, setDensity],
  );

  return (
    <DashboardPreferencesContext.Provider value={value}>
      {children}
    </DashboardPreferencesContext.Provider>
  );
}

export function useScreenshotDashboardPreferences() {
  const context = useContext(DashboardPreferencesContext);
  if (!context) {
    throw new Error(
      'useScreenshotDashboardPreferences must be used within ScreenshotDashboardPreferencesProvider',
    );
  }
  return context;
}

export const DASHBOARD_DENSITY_STORAGE_KEY = DENSITY_STORAGE_KEY;
export const DASHBOARD_CURRENCY_STORAGE_KEY = CURRENCY_STORAGE_KEY;

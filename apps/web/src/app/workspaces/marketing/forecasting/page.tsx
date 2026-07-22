import { redirect } from 'next/navigation';
import type { Route } from 'next';

/**
 * Legacy / documented Forecasting entry.
 * Canonical forecast UI lives under AI Prediction Frameworks
 * (revenue, lead, pipeline, conversion forecast slots).
 */
export default function MarketingForecastingPage() {
  redirect('/workspaces/marketing/ai/predictions' as Route);
}

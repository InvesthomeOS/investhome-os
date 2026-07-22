/**
 * D1D executive UI analytics — privacy-safe, no PII / financial amounts / message bodies.
 * Uses CustomEvent so existing observability can subscribe without a second analytics library.
 */

export type ExecutiveUiEventName =
  | 'executive_dashboard_view'
  | 'executive_dashboard_refresh'
  | 'executive_dashboard_period_change'
  | 'executive_widget_retry'
  | 'executive_widget_drilldown'
  | 'executive_layout_mode';

export interface ExecutiveUiEventPayload {
  event: ExecutiveUiEventName;
  widgetId?: string;
  layout?: 'production' | 'legacy' | 'g8';
  periodPreset?: string;
  /** ISO timestamp only — never attach entity ids, names, or amounts */
  at: string;
}

const SENSITIVE_KEYS = /amount|balance|email|phone|body|message|name|title|token|password/i;

export function trackExecutiveUiEvent(
  event: ExecutiveUiEventName,
  detail: Omit<ExecutiveUiEventPayload, 'event' | 'at'> = {},
): void {
  const safe: ExecutiveUiEventPayload = {
    event,
    at: new Date().toISOString(),
  };
  if (detail.widgetId && !SENSITIVE_KEYS.test(detail.widgetId)) {
    safe.widgetId = detail.widgetId;
  }
  if (detail.layout === 'production' || detail.layout === 'legacy' || detail.layout === 'g8') {
    safe.layout = detail.layout;
  }
  if (detail.periodPreset && /^[a-zA-Z0-9_]+$/.test(detail.periodPreset)) {
    safe.periodPreset = detail.periodPreset;
  }

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('investhome:executive-ui', { detail: safe }));
  }
}

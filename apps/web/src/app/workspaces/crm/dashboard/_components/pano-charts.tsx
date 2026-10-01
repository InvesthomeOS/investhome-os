'use client';

import type { Route } from 'next';
import Link from 'next/link';

import type { CrmDashboardCount } from '@/workspaces/crm/types';

const PETROL = '#075b75';
const TURQUOISE = '#58aebb';
const PETROL_DEEP = '#0a6f8a';
const PETROL_SOFT = '#9ec9d2';

const DOC_SLICE_COLOR: Record<string, string> = {
  person: PETROL,
  purchase: TURQUOISE,
  unresolved: PETROL_DEEP,
  hidden: PETROL_SOFT,
};

const SLICE_FALLBACK = [PETROL, TURQUOISE, PETROL_DEEP, PETROL_SOFT];

function sliceColor(key: string, index: number) {
  return DOC_SLICE_COLOR[key] ?? SLICE_FALLBACK[index % SLICE_FALLBACK.length];
}

export function CompactVerticalBars({
  data,
  ariaLabel,
}: {
  data: CrmDashboardCount[];
  ariaLabel: string;
}) {
  const max = Math.max(...data.map((row) => row.count), 1);
  const dense = data.length > 12;
  const labelStep = dense ? Math.ceil(data.length / 8) : 1;
  const summary = data.map((row) => `${row.label}: ${row.count}`).join('; ');

  return (
    <div className="crm-pano-vbars" role="img" aria-label={`${ariaLabel}. ${summary}`}>
      {data.map((row, index) => {
        const height = Math.max((row.count / max) * 100, row.count > 0 ? 6 : 0);
        const showValue = !dense || row.count === max || index === data.length - 1;
        const showLabel = index % labelStep === 0 || index === data.length - 1;
        const inner = (
          <>
            <span className="crm-pano-vbars__value">{showValue && row.count > 0 ? row.count : ''}</span>
            <span className="crm-pano-vbars__track">
              <span className="crm-pano-vbars__fill" style={{ height: `${height}%` }} />
            </span>
            <span className="crm-pano-vbars__label" title={row.label}>
              {showLabel ? row.label : ''}
            </span>
          </>
        );
        return row.href ? (
          <Link key={row.key} href={row.href as Route} className="crm-pano-vbars__col" title={`${row.label}: ${row.count}`}>
            {inner}
          </Link>
        ) : (
          <div key={row.key} className="crm-pano-vbars__col" title={`${row.label}: ${row.count}`}>
            {inner}
          </div>
        );
      })}
    </div>
  );
}

export function CompactHorizontalBars({
  data,
  ariaLabel,
}: {
  data: CrmDashboardCount[];
  ariaLabel: string;
}) {
  const max = Math.max(...data.map((row) => row.count), 1);
  const summary = data.map((row) => `${row.label}: ${row.count}`).join('; ');

  return (
    <ul className="crm-pano-hbars" aria-label={`${ariaLabel}. ${summary}`}>
      {data.map((row) => {
        const width = Math.max((row.count / max) * 100, row.count > 0 ? 4 : 0);
        const inner = (
          <>
            <span className="crm-pano-hbars__label" title={row.label}>
              {row.label}
            </span>
            <span className="crm-pano-hbars__track">
              <span className="crm-pano-hbars__fill" style={{ width: `${width}%` }} />
            </span>
            <strong className="crm-pano-hbars__value">{row.count}</strong>
          </>
        );
        return (
          <li key={row.key}>
            {row.href ? (
              <Link href={row.href as Route} className="crm-pano-hbars__row" title={`${row.label}: ${row.count}`}>
                {inner}
              </Link>
            ) : (
              <div className="crm-pano-hbars__row" title={`${row.label}: ${row.count}`}>
                {inner}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function PanoDonut({
  data,
  ariaLabel,
  totalLabel,
}: {
  data: CrmDashboardCount[];
  ariaLabel: string;
  totalLabel: string;
}) {
  const visible = data.filter((row) => row.count > 0);
  const total = data.reduce((sum, row) => sum + row.count, 0);
  const denom = total || 1;
  let cursor = 0;
  const slices = data.map((row, index) => {
    const pct = (row.count / denom) * 100;
    const start = cursor;
    cursor += pct;
    return {
      ...row,
      pct,
      color: sliceColor(row.key, index),
      start,
      end: cursor,
    };
  });
  const stops = visible.length
    ? slices.map((item) => `${item.color} ${item.start}% ${item.end}%`).join(', ')
    : '#e6eef1 0% 100%';
  const summary = slices.map((item) => `${item.label} ${item.count}`).join('; ');

  return (
    <div className="crm-pano-donut">
      <div
        className="crm-pano-donut__ring"
        style={{ background: `conic-gradient(${stops})` }}
        role="img"
        aria-label={`${ariaLabel}. ${summary}`}
      >
        <span className="crm-pano-donut__hole">
          <strong>{total}</strong>
          <em>{totalLabel}</em>
        </span>
      </div>
      <ul className="crm-pano-donut__legend">
        {slices.map((item) => {
          const inner = (
            <>
              <span className="crm-pano-donut__dot" style={{ background: item.color }} aria-hidden="true" />
              <span className="crm-pano-donut__name">{item.label}</span>
              <strong>
                {item.count}
                {total > 0 ? ` (${Math.round(item.pct)}%)` : ''}
              </strong>
            </>
          );
          return (
            <li key={item.key}>
              {item.href ? (
                <Link href={item.href as Route} className="crm-pano-donut__item">
                  {inner}
                </Link>
              ) : (
                <div className="crm-pano-donut__item">{inner}</div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

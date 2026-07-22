'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, useState } from 'react';

import { MosaicAvatar } from './MosaicAvatar';
import { LEADS, LEAD_SOURCES, LEAD_STATUSES, type LeadSource, type LeadStatus } from './demo-data';
import { statusClass } from './status';

export function LeadsView() {
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<'all' | LeadStatus>('all');
  const [source, setSource] = useState<'all' | LeadSource>('all');

  const rows = useMemo(() => {
    const query = q.trim().toLowerCase();
    return LEADS.filter((lead) => {
      if (status !== 'all' && lead.status !== status) return false;
      if (source !== 'all' && lead.source !== source) return false;
      if (!query) return true;
      return (
        lead.name.toLowerCase().includes(query) ||
        lead.project.toLowerCase().includes(query) ||
        lead.salesperson.toLowerCase().includes(query) ||
        lead.email.toLowerCase().includes(query)
      );
    });
  }, [q, source, status]);

  return (
    <div className="mosaic-leads" data-testid="mosaic-leads">
      <section className="mosaic-card mosaic-filters">
        <label className="mosaic-search">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
            <path d="M7 14c-3.86 0-7-3.14-7-7s3.14-7 7-7 7 3.14 7 7-3.14 7-7 7ZM7 2C4.243 2 2 4.243 2 7s2.243 5 5 5 5-2.243 5-5-2.243-5-5-5Z" />
            <path d="m13.314 11.9 2.393 2.393a.999.999 0 1 1-1.414 1.414L11.9 13.314a8.019 8.019 0 0 0 1.414-1.414Z" />
          </svg>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name, project, salesperson…"
            aria-label="Search leads"
          />
        </label>
        <label className="mosaic-select">
          <span>Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value as 'all' | LeadStatus)}>
            <option value="all">All statuses</option>
            {LEAD_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="mosaic-select">
          <span>Source</span>
          <select value={source} onChange={(e) => setSource(e.target.value as 'all' | LeadSource)}>
            <option value="all">All sources</option>
            {LEAD_SOURCES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <p className="mosaic-filters__count">
          Showing <strong>{rows.length}</strong> of {LEADS.length}
        </p>
      </section>

      <section className="mosaic-card">
        <div className="mosaic-table-wrap">
          <table className="mosaic-table mosaic-table--dense">
            <thead>
              <tr>
                <th>Lead</th>
                <th>Source</th>
                <th>Salesperson</th>
                <th>Project interest</th>
                <th>Status</th>
                <th>Last contact</th>
                <th>Next action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((lead) => (
                <tr key={lead.id}>
                  <td>
                    <div className="mosaic-person">
                      <MosaicAvatar name={lead.name} size="md" />
                      <div>
                        <Link
                          href={'/ui-preview/mosaic/customer' as Route}
                          className="mosaic-link-strong"
                          data-testid={`mosaic-lead-${lead.id}`}
                        >
                          {lead.name}
                        </Link>
                        <span>{lead.email}</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="mosaic-chip">{lead.source}</span>
                  </td>
                  <td>
                    <div className="mosaic-person mosaic-person--compact">
                      <MosaicAvatar name={lead.salesperson} size="sm" />
                      <span>{lead.salesperson}</span>
                    </div>
                  </td>
                  <td>
                    <strong>{lead.project}</strong>
                    <div className="mosaic-muted">{lead.budget}</div>
                  </td>
                  <td>
                    <span className={`mosaic-badge ${statusClass(lead.status)}`}>{lead.status}</span>
                  </td>
                  <td className="mosaic-muted">{lead.lastContact}</td>
                  <td>{lead.nextAction}</td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="mosaic-empty">
                    No leads match these filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale } from 'next-intl';
import { useState } from 'react';
import { useSearchParams } from 'next/navigation';

import { PLAYBOOKS, SLAS } from '@/lib/adoption/content';
import { lt } from '@/lib/adoption/locale';

export function OperationsWorkspace() {
  const locale = useLocale();
  const search = useSearchParams();
  const [tab, setTab] = useState<'playbooks' | 'sla'>(
    search.get('view') === 'sla' ? 'sla' : 'playbooks',
  );

  return (
    <main className="adop-g13" data-testid="adop-operations" data-tour="operations-root">
      <header className="adop-g13__top">
        <div>
          <p className="adop-g13__eyebrow">G13 · Admin</p>
          <h1 className="adop-g13__title">
            {locale === 'en' ? 'Operations playbooks & SLA' : 'Operasyon playbook ve SLA'}
          </h1>
          <p className="adop-g13__subtitle">
            {locale === 'en'
              ? 'Playbooks link to existing Automation Center SLAs — no duplicate engine.'
              : 'Playbooklar mevcut Otomasyon Merkezi SLA’larına bağlanır — çift motor yok.'}
          </p>
        </div>
        <div className="adop-g13__top-actions">
          <Link href={'/dashboard/automation' as Route} className="adop-g13__btn adop-g13__btn--primary">
            {locale === 'en' ? 'Open Automation Center' : 'Otomasyon Merkezini aç'}
          </Link>
        </div>
      </header>

      <div className="adop-g13__tabs" role="tablist">
        <button type="button" role="tab" className="adop-g13__tab" aria-selected={tab === 'playbooks'} onClick={() => setTab('playbooks')}>
          {locale === 'en' ? 'Playbooks' : 'Playbooklar'}
        </button>
        <button
          type="button"
          role="tab"
          className="adop-g13__tab"
          aria-selected={tab === 'sla'}
          data-testid="adop-sla-tab"
          onClick={() => setTab('sla')}
        >
          SLA
        </button>
      </div>

      <div className="adop-g13__body">
        {tab === 'playbooks' ? (
          <section className="adop-g13__panel" data-testid="adop-playbooks">
            <table className="adop-g13__table">
              <thead>
                <tr>
                  <th>{locale === 'en' ? 'Playbook' : 'Playbook'}</th>
                  <th>{locale === 'en' ? 'Role' : 'Rol'}</th>
                  <th>SLA</th>
                  <th>{locale === 'en' ? 'Escalation' : 'Yükseltme'}</th>
                </tr>
              </thead>
              <tbody>
                {PLAYBOOKS.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <strong>{lt(locale, p.title)}</strong>
                      <div className="adop-g13__muted">{lt(locale, p.trigger)}</div>
                    </td>
                    <td>{p.responsibleRole}</td>
                    <td>{p.slaId}</td>
                    <td>{lt(locale, p.escalationPath)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : (
          <section className="adop-g13__panel" data-testid="adop-sla-settings">
            <table className="adop-g13__table">
              <thead>
                <tr>
                  <th>SLA</th>
                  <th>{locale === 'en' ? 'Response' : 'Yanıt'}</th>
                  <th>{locale === 'en' ? 'Resolution' : 'Çözüm'}</th>
                  <th>{locale === 'en' ? 'Severity' : 'Ciddiyet'}</th>
                  <th>{locale === 'en' ? 'Automation' : 'Otomasyon'}</th>
                </tr>
              </thead>
              <tbody>
                {SLAS.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <strong>{lt(locale, s.title)}</strong>
                      <div className="adop-g13__muted">{lt(locale, s.event)}</div>
                    </td>
                    <td>{s.responseTargetMinutes}m</td>
                    <td>{s.resolutionTargetHours}h</td>
                    <td>
                      <span className="adop-g13__pill">{s.severity}</span>
                    </td>
                    <td>{s.linkedAutomation ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </div>
    </main>
  );
}

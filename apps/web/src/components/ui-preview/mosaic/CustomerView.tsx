'use client';

import { MosaicAvatar } from './MosaicAvatar';
import { DEMO_CUSTOMER } from './demo-data';
import { statusClass } from './status';

export function CustomerView() {
  const c = DEMO_CUSTOMER;

  return (
    <div className="mosaic-customer" data-testid="mosaic-customer">
      <section className="mosaic-card mosaic-customer__hero">
        <MosaicAvatar name={c.name} size="xl" tone="violet" />
        <div className="mosaic-customer__identity">
          <div className="mosaic-customer__title-row">
            <h2>{c.name}</h2>
            <span className={`mosaic-badge ${statusClass(c.status)}`}>{c.status}</span>
          </div>
          <p className="mosaic-muted">
            {c.company} · {c.city} · {c.source}
          </p>
          <dl className="mosaic-dl">
            <div>
              <dt>Email</dt>
              <dd>{c.email}</dd>
            </div>
            <div>
              <dt>Phone</dt>
              <dd>{c.phone}</dd>
            </div>
            <div>
              <dt>Salesperson</dt>
              <dd>
                <span className="mosaic-person mosaic-person--compact">
                  <MosaicAvatar name={c.salesperson} size="sm" />
                  {c.salesperson}
                </span>
              </dd>
            </div>
            <div>
              <dt>Budget</dt>
              <dd>{c.budget}</dd>
            </div>
            <div>
              <dt>Last communication</dt>
              <dd>{c.lastComm}</dd>
            </div>
            <div>
              <dt>Next action</dt>
              <dd>
                <strong>{c.nextAction}</strong>
              </dd>
            </div>
          </dl>
        </div>
        <div className="mosaic-comm-actions">
          <button type="button" className="mosaic-btn mosaic-btn--primary">
            Call
          </button>
          <button type="button" className="mosaic-btn">
            WhatsApp
          </button>
          <button type="button" className="mosaic-btn">
            Email
          </button>
          <button type="button" className="mosaic-btn">
            Meeting
          </button>
          <button type="button" className="mosaic-btn mosaic-btn--dark">
            Add note
          </button>
        </div>
      </section>

      <section className="mosaic-grid mosaic-grid--2">
        <article className="mosaic-card">
          <header className="mosaic-card__head">
            <h2>Projects</h2>
          </header>
          <ul className="mosaic-project-cards">
            {c.projects.map((p) => (
              <li key={`${p.name}-${p.unit}`}>
                <div>
                  <strong>{p.name}</strong>
                  <span>{p.unit}</span>
                </div>
                <div className="mosaic-project-cards__meta">
                  <span className="mosaic-chip">{p.interest}</span>
                  <span className={`mosaic-badge ${statusClass(p.stage)}`}>{p.stage}</span>
                </div>
              </li>
            ))}
          </ul>
        </article>

        <article className="mosaic-card">
          <header className="mosaic-card__head">
            <h2>Tasks</h2>
          </header>
          <ul className="mosaic-tasks">
            {c.customerTasks.map((t) => (
              <li key={t.id}>
                <span className="mosaic-check" aria-hidden />
                <div>
                  <strong>{t.title}</strong>
                  <span>Due {t.due}</span>
                </div>
                <span className={`mosaic-prio mosaic-prio--${t.priority}`}>{t.priority}</span>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="mosaic-grid mosaic-grid--2">
        <article className="mosaic-card">
          <header className="mosaic-card__head">
            <h2>Timeline</h2>
          </header>
          <ol className="mosaic-timeline">
            {c.timeline.map((ev) => (
              <li key={ev.id} data-type={ev.type}>
                <span className="mosaic-timeline__dot" aria-hidden />
                <div>
                  <strong>{ev.title}</strong>
                  <p>{ev.detail}</p>
                  <small>{ev.at}</small>
                </div>
              </li>
            ))}
          </ol>
        </article>

        <div className="mosaic-stack">
          <article className="mosaic-card">
            <header className="mosaic-card__head">
              <h2>Notes</h2>
            </header>
            <ul className="mosaic-notes">
              {c.notes.map((n) => (
                <li key={n.id}>
                  <div className="mosaic-notes__head">
                    <MosaicAvatar name={n.author} size="sm" />
                    <strong>{n.author}</strong>
                    <span>{n.at}</span>
                  </div>
                  <p>{n.text}</p>
                </li>
              ))}
            </ul>
          </article>

          <article className="mosaic-card">
            <header className="mosaic-card__head">
              <h2>Documents</h2>
            </header>
            <ul className="mosaic-docs">
              {c.docs.map((d) => (
                <li key={d.id}>
                  <span className="mosaic-doc-icon" aria-hidden>
                    PDF
                  </span>
                  <div>
                    <strong>{d.name}</strong>
                    <span>
                      {d.kind} · {d.size}
                    </span>
                  </div>
                  <button type="button" className="mosaic-btn mosaic-btn--ghost">
                    Open
                  </button>
                </li>
              ))}
            </ul>
          </article>
        </div>
      </section>
    </div>
  );
}

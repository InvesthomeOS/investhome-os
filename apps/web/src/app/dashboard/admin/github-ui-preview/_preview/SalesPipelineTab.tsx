'use client';

import { useMemo, useState } from 'react';

import { OpportunityDrawer } from './OpportunityDrawer';
import {
  OPPORTUNITIES,
  STAGE_META,
  formatShortDate,
  formatTry,
  type Opportunity,
  type PipelineStageId,
} from './demo-data';

type Filter = 'all' | 'sales' | 'investor';
type ViewMode = 'board' | 'list';

export function SalesPipelineTab() {
  const [items, setItems] = useState<Opportunity[]>(OPPORTUNITIES);
  const [filter, setFilter] = useState<Filter>('all');
  const [view, setView] = useState<ViewMode>('board');
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [overStage, setOverStage] = useState<PipelineStageId | null>(null);
  const [selected, setSelected] = useState<Opportunity | null>(null);

  const filtered = useMemo(() => {
    if (filter === 'all') return items;
    return items.filter((o) => o.type === filter);
  }, [filter, items]);

  const byStage = useMemo(() => {
    const map = {} as Record<PipelineStageId, Opportunity[]>;
    for (const s of STAGE_META) map[s.id] = [];
    for (const o of filtered) map[o.stage].push(o);
    return map;
  }, [filtered]);

  const moveTo = (id: string, stage: PipelineStageId) => {
    setItems((prev) => prev.map((o) => (o.id === id ? { ...o, stage } : o)));
  };

  return (
    <div data-testid="g1-sales-pipeline">
      <div className="g1-preview__toolbar">
        <div className="g1-preview__toolbar-left">
          <div>
            <h2 className="g1-preview__title">Satış & Yatırımcı Pipeline</h2>
            <p className="g1-preview__subtitle">
              {filtered.length} fırsat · demo veri · sürükle-bırak aşama değiştirir (yerel)
            </p>
          </div>
        </div>
        <div className="g1-preview__toolbar-right">
          <button
            type="button"
            className={`g1-chip${filter === 'all' ? ' g1-chip--active' : ''}`}
            onClick={() => setFilter('all')}
          >
            Tümü
          </button>
          <button
            type="button"
            className={`g1-chip${filter === 'sales' ? ' g1-chip--active' : ''}`}
            onClick={() => setFilter('sales')}
          >
            Satış
          </button>
          <button
            type="button"
            className={`g1-chip${filter === 'investor' ? ' g1-chip--active' : ''}`}
            onClick={() => setFilter('investor')}
          >
            Yatırımcı
          </button>
          <div className="g1-seg" role="group" aria-label="Görünüm">
            <button
              type="button"
              className={view === 'board' ? 'is-active' : undefined}
              onClick={() => setView('board')}
            >
              Pano
            </button>
            <button
              type="button"
              className={view === 'list' ? 'is-active' : undefined}
              onClick={() => setView('list')}
            >
              Liste
            </button>
          </div>
        </div>
      </div>

      {view === 'board' ? (
        <div className="g1-board" role="list">
          {STAGE_META.map((stage) => {
            const cards = byStage[stage.id];
            const total = cards.reduce((sum, c) => sum + c.valueTry, 0);
            return (
              <section
                key={stage.id}
                className={`g1-col g1-col--tone-${stage.tone}${overStage === stage.id ? ' g1-col--over' : ''}`}
                role="listitem"
                onDragOver={(e) => {
                  e.preventDefault();
                  setOverStage(stage.id);
                }}
                onDragLeave={() => setOverStage((cur) => (cur === stage.id ? null : cur))}
                onDrop={(e) => {
                  e.preventDefault();
                  if (draggingId) moveTo(draggingId, stage.id);
                  setDraggingId(null);
                  setOverStage(null);
                }}
              >
                <header className="g1-col__head">
                  <div className="g1-col__head-row">
                    <span className="g1-col__name">{stage.labelTr}</span>
                    <span className="g1-col__count">{cards.length}</span>
                  </div>
                  <span className="g1-col__total">{formatTry(total)}</span>
                </header>
                <div className="g1-col__cards">
                  {cards.map((opp) => (
                    <article
                      key={opp.id}
                      className={`g1-card${draggingId === opp.id ? ' g1-card--dragging' : ''}`}
                      draggable
                      onDragStart={() => setDraggingId(opp.id)}
                      onDragEnd={() => {
                        setDraggingId(null);
                        setOverStage(null);
                      }}
                      onClick={() => setSelected(opp)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSelected(opp);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      data-testid={`g1-opp-${opp.id}`}
                    >
                      <div className="g1-card__top">
                        <h3 className="g1-card__title">{opp.title}</h3>
                        <span className="g1-card__type">
                          {opp.type === 'investor' ? 'Yatırım' : 'Satış'}
                        </span>
                      </div>
                      <p className="g1-card__company">{opp.company}</p>
                      <div className="g1-card__value">
                        <strong>{formatTry(opp.valueTry)}</strong>
                        <span>%{opp.probability}</span>
                      </div>
                      <div className="g1-prob" aria-hidden>
                        <i style={{ width: `${opp.probability}%` }} />
                      </div>
                      <div className="g1-card__meta">
                        <div className="g1-card__who">
                          <span className="g1-avatar">{opp.initials}</span>
                          <span>{opp.investor}</span>
                        </div>
                        <span className="g1-card__date">{formatShortDate(opp.closeDate)}</span>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      ) : (
        <div className="g1-list">
          <table>
            <thead>
              <tr>
                <th>Fırsat</th>
                <th>Şirket</th>
                <th>Aşama</th>
                <th>Değer</th>
                <th>Olasılık</th>
                <th>Kapanış</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((opp) => {
                const stage = STAGE_META.find((s) => s.id === opp.stage);
                return (
                  <tr key={opp.id} onClick={() => setSelected(opp)}>
                    <td>
                      <strong>{opp.title}</strong>
                    </td>
                    <td>{opp.company}</td>
                    <td>{stage?.labelTr}</td>
                    <td>{formatTry(opp.valueTry)}</td>
                    <td>%{opp.probability}</td>
                    <td>{formatShortDate(opp.closeDate)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {selected ? (
        <OpportunityDrawer opportunity={selected} onClose={() => setSelected(null)} />
      ) : null}
    </div>
  );
}

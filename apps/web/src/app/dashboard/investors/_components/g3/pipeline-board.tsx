'use client';

import type { Investor } from '@/lib/api/investors';
import { formatCurrency, formatShortDate } from '@/lib/api/investors';

import {
  getBoardMeta,
  type InvestorBoardMeta,
  type InvestorPriority,
} from './board-meta';
import {
  LIFECYCLE_META,
  initials,
  investorCapacity,
  stageProbability,
  toLifecycleStage,
  type InvestorLifecycleStage,
} from './lifecycle';

interface PipelineBoardProps {
  investors: Investor[];
  locale: string;
  stageLabel: (stage: InvestorLifecycleStage) => string;
  typeLabel: (type: string) => string;
  priorityLabel: (p: InvestorPriority) => string;
  canMove: boolean;
  draggingId: string | null;
  overStage: InvestorLifecycleStage | null;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
  onDragOver: (stage: InvestorLifecycleStage) => void;
  onDrop: (stage: InvestorLifecycleStage) => void;
  onOpen: (investor: Investor) => void;
  onQuickAssign?: (investor: Investor) => void;
  metaVersion: number;
}

function resolveMeta(investor: Investor, metaVersion: number): InvestorBoardMeta & { probability: number } {
  void metaVersion;
  const meta = getBoardMeta(investor.id);
  const stage = toLifecycleStage(investor.status);
  return {
    ...meta,
    probability: meta.probability ?? stageProbability(stage),
    priority: meta.priority ?? 'medium',
  };
}

export function PipelineBoard({
  investors,
  locale,
  stageLabel,
  typeLabel,
  priorityLabel,
  canMove,
  draggingId,
  overStage,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  onOpen,
  onQuickAssign,
  metaVersion,
}: PipelineBoardProps) {
  const byStage = LIFECYCLE_META.reduce(
    (acc, stage) => {
      acc[stage.id] = [];
      return acc;
    },
    {} as Record<InvestorLifecycleStage, Investor[]>,
  );

  for (const inv of investors) {
    byStage[toLifecycleStage(inv.status)].push(inv);
  }

  return (
    <div className="inv-g3__board" role="list" data-testid="inv-g3-board">
      {LIFECYCLE_META.map((stage) => {
        const cards = byStage[stage.id];
        const total = cards.reduce((sum, c) => sum + investorCapacity(c), 0);
        const weighted = cards.reduce((sum, c) => {
          const meta = resolveMeta(c, metaVersion);
          return sum + (investorCapacity(c) * meta.probability) / 100;
        }, 0);

        return (
          <section
            key={stage.id}
            className={`inv-g3__col inv-g3__col--tone-${stage.tone}${overStage === stage.id ? ' inv-g3__col--over' : ''}`}
            role="listitem"
            aria-label={stageLabel(stage.id)}
            onDragOver={(e) => {
              if (!canMove) return;
              e.preventDefault();
              onDragOver(stage.id);
            }}
            onDragLeave={() => {
              /* column highlight cleared on drag end / drop */
            }}
            onDrop={(e) => {
              e.preventDefault();
              if (canMove) onDrop(stage.id);
            }}
            data-testid={`inv-g3-col-${stage.id}`}
          >
            <header className="inv-g3__col-head">
              <div className="inv-g3__col-head-row">
                <span className="inv-g3__col-name">{stageLabel(stage.id)}</span>
                <span className="inv-g3__col-count">{cards.length}</span>
              </div>
              <span className="inv-g3__col-total">{formatCurrency(String(total), locale)}</span>
              <span className="inv-g3__col-total">
                W {formatCurrency(String(Math.round(weighted)), locale)}
              </span>
            </header>
            <div className="inv-g3__col-cards">
              {cards.map((investor) => {
                const meta = resolveMeta(investor, metaVersion);
                const stageId = toLifecycleStage(investor.status);
                return (
                  <article
                    key={investor.id}
                    className={`inv-g3__card${draggingId === investor.id ? ' inv-g3__card--dragging' : ''}`}
                    draggable={canMove}
                    onDragStart={() => onDragStart(investor.id)}
                    onDragEnd={onDragEnd}
                    onClick={() => onOpen(investor)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onOpen(investor);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    data-testid={`inv-g3-card-${investor.id}`}
                    aria-grabbed={draggingId === investor.id}
                  >
                    <div className="inv-g3__card-top">
                      <h3 className="inv-g3__card-title">{investor.full_name}</h3>
                      {meta.warning ? (
                        <span className="inv-g3__card-badge inv-g3__card-badge--warn">!</span>
                      ) : (
                        <span className="inv-g3__card-badge">{typeLabel(investor.investor_type)}</span>
                      )}
                    </div>
                    <p className="inv-g3__card-company">
                      {[investor.country, investor.city].filter(Boolean).join(' · ') || '—'}
                    </p>
                    <div className="inv-g3__card-value">
                      <strong>{formatCurrency(investor.investment_capacity, locale)}</strong>
                      <span>%{meta.probability}</span>
                    </div>
                    <div className="inv-g3__prob" aria-hidden>
                      <i style={{ width: `${Math.min(100, meta.probability)}%` }} />
                    </div>
                    <div className="inv-g3__card-meta">
                      <div className="inv-g3__who">
                        <span className="inv-g3__avatar">
                          {initials(investor.assigned_to || investor.full_name)}
                        </span>
                        <span>{investor.assigned_to || '—'}</span>
                      </div>
                      <span>
                        {investor.next_follow_up_date
                          ? formatShortDate(investor.next_follow_up_date, locale)
                          : '—'}
                      </span>
                    </div>
                    <div className="inv-g3__card-foot">
                      <span>{stageLabel(stageId)}</span>
                      <span>· {priorityLabel(meta.priority ?? 'medium')}</span>
                      {investor.preferred_projects ? (
                        <span>· {investor.preferred_projects.split(',')[0]}</span>
                      ) : null}
                      {meta.nextAction ? <span>· {meta.nextAction}</span> : null}
                    </div>
                    {onQuickAssign ? (
                      <div className="inv-g3__card-actions" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          className="inv-g3__link"
                          onClick={() => onQuickAssign(investor)}
                        >
                          →
                        </button>
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

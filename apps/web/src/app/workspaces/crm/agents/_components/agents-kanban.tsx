'use client';

import type { CrmContactSummary } from '@/workspaces/crm/types';

import {
  agentFlags,
  displayDate,
  kanbanColumns,
  normalizeAgentStage,
  responsibleOf,
  type AgentActivityIndex,
} from './agents-stage';

export function AgentsKanban({
  items,
  activity,
  onOpen,
}: {
  items: CrmContactSummary[];
  activity: AgentActivityIndex;
  onOpen: (agent: CrmContactSummary) => void;
}) {
  const columns = kanbanColumns(items);

  return (
    <div className="crm-agreements-kanban" data-testid="agents-kanban">
      {columns.map((column) => {
        const cards = items.filter((item) => normalizeAgentStage(item) === column);
        return (
          <section key={column} className="crm-agreements-column" data-testid={`agents-column-${column}`}>
            <h2>
              {column}
              <span>{cards.length}</span>
            </h2>
            {cards.map((agent) => {
              const last = activity.last[agent.id];
              const next = activity.next[agent.id];
              return (
                <button
                  key={agent.id}
                  type="button"
                  className="crm-agreements-card"
                  data-testid={`agents-card-${agent.id}`}
                  onClick={() => onOpen(agent)}
                >
                  <strong>{agent.display_name}</strong>
                  <small>{agent.organization_name || agent.company_name || '—'}</small>
                  <small>{[agent.primary_phone, agent.primary_email].filter(Boolean).join(' · ') || '—'}</small>
                  {responsibleOf(agent) ? (
                    <span className="crm-agreements-meta">{responsibleOf(agent)}</span>
                  ) : null}
                  {last ? (
                    <span className="crm-agreements-meta">
                      Son: {last.title}
                      {last.created_at ? ` · ${displayDate(last.created_at)}` : ''}
                    </span>
                  ) : null}
                  {next ? (
                    <span className="crm-agreements-meta">
                      Sonraki: {next.title}
                      {displayDate(next.due_date || next.start_date)
                        ? ` · ${displayDate(next.due_date || next.start_date)}`
                        : ''}
                    </span>
                  ) : null}
                  <div className="crm-agreements-tags">
                    {agentFlags(agent).map((flag) => (
                      <span key={flag} className="crm-agreements-tag">
                        {flag}
                      </span>
                    ))}
                  </div>
                </button>
              );
            })}
          </section>
        );
      })}
    </div>
  );
}

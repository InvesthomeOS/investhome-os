'use client';

import type { ConstructionStage, ConstructionTask } from './construction-domain';
import { STAGE_META } from './construction-domain';

interface ConstructionBoardProps {
  tasks: ConstructionTask[];
  stageLabel: (s: ConstructionStage) => string;
  priorityLabel: (p: string) => string;
  canMove: boolean;
  draggingId: string | null;
  overStage: ConstructionStage | null;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
  onDragOver: (stage: ConstructionStage) => void;
  onDrop: (stage: ConstructionStage) => void;
  onOpen: (task: ConstructionTask) => void;
}

export function ConstructionBoard({
  tasks,
  stageLabel,
  priorityLabel,
  canMove,
  draggingId,
  overStage,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  onOpen,
}: ConstructionBoardProps) {
  const byStage = STAGE_META.reduce(
    (acc, stage) => {
      acc[stage.id] = [];
      return acc;
    },
    {} as Record<ConstructionStage, ConstructionTask[]>,
  );

  for (const task of tasks) {
    byStage[task.stage]?.push(task);
  }

  return (
    <div className="proj-g4__board" role="list" data-testid="proj-g4-board">
      {STAGE_META.map((stage) => {
        const cards = byStage[stage.id] ?? [];
        return (
          <section
            key={stage.id}
            className={`proj-g4__col proj-g4__col--tone-${stage.tone}${overStage === stage.id ? ' proj-g4__col--over' : ''}`}
            role="listitem"
            aria-label={stageLabel(stage.id)}
            onDragOver={(e) => {
              if (!canMove) return;
              e.preventDefault();
              onDragOver(stage.id);
            }}
            onDrop={(e) => {
              e.preventDefault();
              if (canMove) onDrop(stage.id);
            }}
            data-testid={`proj-g4-col-${stage.id}`}
          >
            <header className="proj-g4__col-head">
              <div className="proj-g4__col-head-row">
                <span className="proj-g4__col-name">{stageLabel(stage.id)}</span>
                <span className="proj-g4__col-count">{cards.length}</span>
              </div>
            </header>
            <div className="proj-g4__col-cards">
              {cards.map((task) => (
                <article
                  key={task.id}
                  className={`proj-g4__card${draggingId === task.id ? ' proj-g4__card--dragging' : ''}`}
                  draggable={canMove}
                  onDragStart={() => onDragStart(task.id)}
                  onDragEnd={onDragEnd}
                  onClick={() => onOpen(task)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onOpen(task);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  data-testid={`proj-g4-task-${task.id}`}
                  aria-grabbed={draggingId === task.id}
                >
                  <div className="proj-g4__card-top">
                    <h3 className="proj-g4__card-title">{task.title}</h3>
                    {task.blockers > 0 ? (
                      <span className="proj-g4__card-badge proj-g4__card-badge--warn">!</span>
                    ) : (
                      <span className="proj-g4__card-badge">{task.key}</span>
                    )}
                  </div>
                  <p className="proj-g4__card-company">{task.projectName}</p>
                  <div className="proj-g4__card-meta">
                    <span className={`proj-g4__card-badge`}>{priorityLabel(task.priority)}</span>
                    <span>{task.dueDate ?? '—'}</span>
                  </div>
                  <div className="proj-g4__card-foot">
                    <div className="proj-g4__who">
                      <span className="proj-g4__avatar">
                        {task.assignee.slice(0, 2).toUpperCase()}
                      </span>
                      <span>{task.assignee}</span>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

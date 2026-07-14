import type { ModuleName } from '@investhome/shared';

export interface DomainEvent<TPayload = Record<string, unknown>> {
  id: string;
  type: string;
  module: ModuleName;
  aggregateId: string;
  occurredAt: string;
  payload: TPayload;
  metadata?: Record<string, string>;
}

export type EventHandler<TPayload = Record<string, unknown>> = (
  event: DomainEvent<TPayload>,
) => void | Promise<void>;

export const EVENT_BUS_CHANNEL = 'investhome.events' as const;

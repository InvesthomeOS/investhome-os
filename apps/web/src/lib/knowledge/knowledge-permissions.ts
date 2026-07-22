import type { CurrentUser } from '@/lib/api/auth';
import { hasPermission } from '@/lib/api/auth';

export function canViewKnowledge(user: CurrentUser | null): boolean {
  if (!user) return false;
  return hasPermission(user, 'knowledge', 'view') || hasPermission(user, 'documents', 'view');
}

export function canManageKnowledge(user: CurrentUser | null): boolean {
  if (!user) return false;
  return hasPermission(user, 'knowledge', 'manage');
}

export function canReviewKnowledge(user: CurrentUser | null): boolean {
  if (!user) return false;
  return hasPermission(user, 'knowledge', 'review') || hasPermission(user, 'documents', 'approve');
}

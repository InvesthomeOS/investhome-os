import { hasPermission, type CurrentUser } from '@/lib/api/auth';
import { canQueryCopilot, canViewMarketingAI } from '@/lib/marketing/marketing-permissions';

/** Platform AI Workspace access — dedicated resource with executive / marketing fallbacks. */
export function canViewAiWorkspace(user: CurrentUser | null): boolean {
  if (!user) return false;
  return (
    hasPermission(user, 'ai_workspace', 'view') ||
    hasPermission(user, 'executive', 'view') ||
    canViewMarketingAI(user) ||
    hasPermission(user, 'ai_providers', 'view')
  );
}

export function canUseAiWorkspace(user: CurrentUser | null): boolean {
  if (!user) return false;
  return (
    hasPermission(user, 'ai_workspace', 'use_ai') ||
    hasPermission(user, 'marketing', 'use_ai') ||
    canQueryCopilot(user) ||
    canViewAiWorkspace(user)
  );
}

export function canManageAiWorkspaceSettings(user: CurrentUser | null): boolean {
  if (!user) return false;
  return (
    hasPermission(user, 'ai_workspace', 'manage_ai_settings') ||
    hasPermission(user, 'marketing', 'manage_ai_settings') ||
    hasPermission(user, 'documents', 'manage_ai')
  );
}

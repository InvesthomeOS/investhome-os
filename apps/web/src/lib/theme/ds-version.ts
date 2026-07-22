/**
 * UXR1 V2 opt-in activation helpers.
 * Production Phase 2A: Dashboard home + Executive command center only.
 * Keep scoped — do not activate globally (avoids CSS leakage to CRM/Sales/etc.).
 */

const V2_EXACT = new Set(['/dashboard', '/dashboard/']);

/** True when pathname should activate [data-ds-version="v2"] on the OS shell. */
export function isDsV2ShellRoute(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  // Strip query/hash if callers ever pass a full URL path fragment
  const path = pathname.split('?')[0]?.split('#')[0] ?? pathname;
  if (V2_EXACT.has(path)) return true;
  if (path === '/dashboard/executive' || path.startsWith('/dashboard/executive/')) {
    return true;
  }
  return false;
}

export const DS_VERSION_V2 = 'v2' as const;

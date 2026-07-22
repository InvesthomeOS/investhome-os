export type WidgetLoadState = 'idle' | 'loading' | 'error' | 'success';

export type ShellState = 'ready' | 'loading' | 'empty' | 'error';

/** Map loader state + data presence → WidgetShell state. Never treat error as empty zeros. */
export function toShellState(
  state: WidgetLoadState,
  opts: { empty?: boolean; permissionDenied?: boolean; unsupported?: boolean } = {},
): ShellState {
  if (opts.permissionDenied || opts.unsupported) return 'empty';
  if (state === 'loading' || state === 'idle') return 'loading';
  if (state === 'error') return 'error';
  if (opts.empty) return 'empty';
  return 'ready';
}

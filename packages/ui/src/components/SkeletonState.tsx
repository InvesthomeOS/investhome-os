import { LoadingState, type LoadingStateProps } from './LoadingState.js';

export type SkeletonStateProps = Omit<LoadingStateProps, 'variant'> & {
  /** Alias for LoadingState skeleton — keep callers of LoadingState intact */
  lines?: number;
};

/** Design System v1.0 skeleton alias — extends LoadingState without breaking existing callers. */
export function SkeletonState({ label = 'Loading…', lines = 4 }: SkeletonStateProps) {
  return <LoadingState label={label} variant="skeleton" lines={lines} />;
}

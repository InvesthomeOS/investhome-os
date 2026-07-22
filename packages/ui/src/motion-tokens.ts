/**
 * Motion tokens for TS consumers. CSS source of truth: apps/web/src/app/motion-system.css
 */
export const motionTokens = {
  duration: {
    instant: '0ms',
    fast: '120ms',
    base: '200ms',
    standard: '200ms',
    moderate: '280ms',
    slow: '360ms',
    toast: '320ms',
    page: '240ms',
    drawer: '280ms',
    modal: '200ms',
    hover: '120ms',
    collapse: '240ms',
  },
  ease: {
    out: 'cubic-bezier(0.22, 1, 0.36, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    emphasized: 'cubic-bezier(0.2, 0, 0, 1)',
    spring: 'cubic-bezier(0.34, 1.2, 0.64, 1)',
  },
} as const;

export type MotionDurationName = keyof typeof motionTokens.duration;
export type MotionEaseName = keyof typeof motionTokens.ease;

'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';
import { useLocale } from 'next-intl';

import { getTour } from '@/lib/adoption/content';
import { lt } from '@/lib/adoption/locale';
import {
  loadAdoptionState,
  updateAdoptionState,
  type AdoptionLocalState,
} from '@/lib/adoption/progress-store';
import type { ProductTour, TourStep } from '@/lib/adoption/types';

type TourContextValue = {
  activeTour: ProductTour | null;
  stepIndex: number;
  step: TourStep | null;
  startTour: (tourId: string) => void;
  next: () => void;
  prev: () => void;
  skip: () => void;
  close: () => void;
  state: AdoptionLocalState;
  refreshState: () => void;
  userId: string;
};

const TourContext = createContext<TourContextValue | null>(null);

export function useAdoptionTour() {
  const ctx = useContext(TourContext);
  if (!ctx) throw new Error('useAdoptionTour requires AdoptionTourProvider');
  return ctx;
}

export function AdoptionTourProvider({
  userId,
  children,
}: {
  userId: string;
  children: ReactNode;
}) {
  const [state, setState] = useState(() => loadAdoptionState(userId));
  const [activeTourId, setActiveTourId] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);

  const refreshState = useCallback(() => {
    setState(loadAdoptionState(userId));
  }, [userId]);

  const activeTour = activeTourId ? getTour(activeTourId) ?? null : null;
  const step = activeTour?.steps[stepIndex] ?? null;

  const persistTour = useCallback(
    (tourId: string, index: number, completed: boolean) => {
      updateAdoptionState(userId, (prev) => ({
        ...prev,
        tours: {
          ...prev.tours,
          [tourId]: {
            tourId,
            stepIndex: index,
            completed,
            updatedAt: new Date().toISOString(),
          },
        },
      }));
      refreshState();
    },
    [refreshState, userId],
  );

  const startTour = useCallback(
    (tourId: string) => {
      const existing = loadAdoptionState(userId).tours[tourId];
      setActiveTourId(tourId);
      setStepIndex(existing && !existing.completed ? existing.stepIndex : 0);
      persistTour(tourId, existing && !existing.completed ? existing.stepIndex : 0, false);
    },
    [persistTour, userId],
  );

  const close = useCallback(() => {
    setActiveTourId(null);
  }, []);

  const next = useCallback(() => {
    if (!activeTour) return;
    if (stepIndex >= activeTour.steps.length - 1) {
      persistTour(activeTour.id, stepIndex, true);
      setActiveTourId(null);
      return;
    }
    const nextIndex = stepIndex + 1;
    setStepIndex(nextIndex);
    persistTour(activeTour.id, nextIndex, false);
  }, [activeTour, persistTour, stepIndex]);

  const prev = useCallback(() => {
    if (!activeTour || stepIndex <= 0) return;
    const prevIndex = stepIndex - 1;
    setStepIndex(prevIndex);
    persistTour(activeTour.id, prevIndex, false);
  }, [activeTour, persistTour, stepIndex]);

  const skip = useCallback(() => {
    if (!activeTour?.skipAllowed) return;
    persistTour(activeTour.id, stepIndex, false);
    setActiveTourId(null);
  }, [activeTour, persistTour, stepIndex]);

  const value = useMemo(
    () => ({
      activeTour,
      stepIndex,
      step,
      startTour,
      next,
      prev,
      skip,
      close,
      state,
      refreshState,
      userId,
    }),
    [activeTour, close, next, prev, refreshState, skip, startTour, state, step, stepIndex, userId],
  );

  return (
    <TourContext.Provider value={value}>
      {children}
      <TourOverlay />
    </TourContext.Provider>
  );
}

function TourOverlay() {
  const locale = useLocale();
  const { activeTour, step, stepIndex, next, prev, skip, close } = useAdoptionTour();
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (!step) {
      setRect(null);
      return;
    }
    const measure = () => {
      const el = document.querySelector(step.selector);
      if (el) {
        setRect(el.getBoundingClientRect());
        el.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
      } else {
        setRect(null);
      }
    };
    measure();
    window.addEventListener('resize', measure);
    window.addEventListener('scroll', measure, true);
    return () => {
      window.removeEventListener('resize', measure);
      window.removeEventListener('scroll', measure, true);
    };
  }, [step]);

  useEffect(() => {
    if (!activeTour) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (activeTour.skipAllowed) skip();
        else close();
      } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        e.preventDefault();
        next();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prev();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [activeTour, close, next, prev, skip]);

  if (!activeTour || !step) return null;

  const pad = 6;
  const highlight = rect
    ? {
        top: Math.max(8, rect.top - pad),
        left: Math.max(8, rect.left - pad),
        width: rect.width + pad * 2,
        height: rect.height + pad * 2,
      }
    : { top: 80, left: 24, width: 280, height: 48 };

  const placement = step.placement ?? 'bottom';
  const cardStyle: CSSProperties = {
    top:
      placement === 'top'
        ? highlight.top - 12
        : placement === 'bottom'
          ? highlight.top + highlight.height + 16
          : highlight.top,
    left:
      placement === 'right'
        ? highlight.left + highlight.width + 16
        : placement === 'left'
          ? Math.max(12, highlight.left - 360)
          : highlight.left,
  };
  if (placement === 'top') {
    cardStyle.transform = 'translateY(-100%)';
  }

  return (
    <div
      className="adop-tour-root adop-tour-root--active"
      role="dialog"
      aria-modal="true"
      aria-label={lt(locale, activeTour.title)}
      data-testid="adop-tour-overlay"
      data-tour-active={activeTour.id}
    >
      {!rect && <div className="adop-tour-dim" aria-hidden />}
      <div
        className="adop-tour-highlight"
        style={highlight}
        data-tour-highlight={step.selector}
        aria-hidden
      />
      <div className="adop-tour-card" style={cardStyle} data-testid="adop-tour-card">
        <p className="adop-g13__eyebrow" style={{ marginBottom: 4 }}>
          {stepIndex + 1} / {activeTour.steps.length}
        </p>
        <h3>{lt(locale, step.title)}</h3>
        <p>{lt(locale, step.description)}</p>
        <div className="adop-tour-card__meta">
          <div>
            <strong>{locale === 'en' ? 'Action' : 'Aksiyon'}:</strong> {lt(locale, step.action)}
          </div>
          <div>
            <strong>{locale === 'en' ? 'Expected' : 'Beklenen'}:</strong>{' '}
            {lt(locale, step.expectedResult)}
          </div>
          {step.warning ? (
            <div style={{ color: '#b45309' }}>
              <strong>{locale === 'en' ? 'Warning' : 'Uyarı'}:</strong> {lt(locale, step.warning)}
            </div>
          ) : null}
        </div>
        <div className="adop-tour-card__actions">
          <div className="adop-tour-card__nav">
            <button type="button" className="adop-g13__btn" onClick={prev} disabled={stepIndex === 0}>
              {locale === 'en' ? 'Previous' : 'Önceki'}
            </button>
            <button type="button" className="adop-g13__btn adop-g13__btn--primary" onClick={next}>
              {stepIndex >= activeTour.steps.length - 1
                ? locale === 'en'
                  ? 'Finish'
                  : 'Bitir'
                : locale === 'en'
                  ? 'Next'
                  : 'Sonraki'}
            </button>
          </div>
          {activeTour.skipAllowed ? (
            <button type="button" className="adop-g13__btn adop-g13__btn--ghost" onClick={skip}>
              {locale === 'en' ? 'Skip' : 'Atla'}
            </button>
          ) : (
            <button type="button" className="adop-g13__btn adop-g13__btn--ghost" onClick={close}>
              {locale === 'en' ? 'Pause' : 'Duraklat'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

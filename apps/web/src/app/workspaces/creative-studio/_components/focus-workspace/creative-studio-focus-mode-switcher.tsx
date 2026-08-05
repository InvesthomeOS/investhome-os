'use client';

import { useTranslations } from 'next-intl';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  CS_FOCUS_MODE_ICONS,
  CS_FOCUS_MODE_ORDER,
  type CreativeStudioWorkspaceMode,
} from './creative-studio-focus-types';

export type CreativeStudioFocusModeSwitcherProps = {
  mode: CreativeStudioWorkspaceMode;
  setMode: (mode: CreativeStudioWorkspaceMode) => void;
  className?: string;
};

export function CreativeStudioFocusModeSwitcher({
  mode,
  setMode,
  className,
}: CreativeStudioFocusModeSwitcherProps) {
  const t = useTranslations('creativeStudio.focusWorkspace');

  return (
    <div
      className={['cs-fw-switcher', className].filter(Boolean).join(' ')}
      data-testid="cs-fw-mode-switcher"
      role="group"
      aria-label={t('modeSwitcherLabel')}
    >
      {CS_FOCUS_MODE_ORDER.map((item) => {
        const active = mode === item;
        return (
          <button
            key={item}
            type="button"
            className={['cs-fw-switcher__btn', active ? 'is-active' : '']
              .filter(Boolean)
              .join(' ')}
            data-testid={`cs-fw-mode-${item}`}
            title={t(`modes.${item}`)}
            aria-pressed={active}
            onClick={() => setMode(item)}
          >
            <IhIcon name={CS_FOCUS_MODE_ICONS[item]} size={16} />
            <span className="cs-fw-switcher__label">{t(`modesShort.${item}`)}</span>
          </button>
        );
      })}
    </div>
  );
}

'use client';

import { IconButton } from '@investhome/ui';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState, useTransition } from 'react';

import { IhIcon } from '@/components/icons/ih-icons';
import { locales, type AppLocale } from '@/i18n/config';
import { useAuth } from '@/lib/auth/auth-context';
import { writeLocaleCookie } from '@/lib/i18n/locale-cookie';
import { useGlobalSearch } from '@/lib/search/global-search-context';

import {
  QUICK_ACTIONS,
  useScreenshotDashboardInteractions,
} from './screenshot-dashboard-interactions';
import {
  DASHBOARD_CURRENCIES,
  DASHBOARD_DENSITIES,
  useScreenshotDashboardPreferences,
} from './screenshot-dashboard-preferences';

type ScreenshotDashboardHeaderCoreProps = {
  canSearch: boolean;
  openPalette: () => void;
  locale: AppLocale;
  isPending: boolean;
  changeLocale: (locale: AppLocale) => void;
};

function ScreenshotDashboardHeaderCore({
  canSearch,
  openPalette,
  locale,
  isPending,
  changeLocale,
}: ScreenshotDashboardHeaderCoreProps) {
  const { openAi, openQuickAction, openNotifications, unreadCount } =
    useScreenshotDashboardInteractions();
  const t = useTranslations('screenshotDashboard');
  const { density, setDensity, currency, setCurrency } = useScreenshotDashboardPreferences();
  const [quickMenuOpen, setQuickMenuOpen] = useState(false);
  const [displaySettingsOpen, setDisplaySettingsOpen] = useState(false);
  const displaySettingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!quickMenuOpen && !displaySettingsOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setQuickMenuOpen(false);
        setDisplaySettingsOpen(false);
        if (displaySettingsOpen) {
          window.requestAnimationFrame(() => {
            displaySettingsRef.current?.querySelector<HTMLButtonElement>(':scope > button')?.focus();
          });
        }
      }
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [displaySettingsOpen, quickMenuOpen]);

  return (
    <div className="screenshot-header">
      <button
        type="button"
        className="screenshot-header__search"
        onClick={openPalette}
        disabled={!canSearch}
      >
        <IhIcon name="search" size={14} />
        <span>{t('header.search')}</span>
      </button>

      <div className="screenshot-header__actions">
        <button type="button" className="screenshot-header__ai" onClick={() => openAi()}>
          <IhIcon name="sparkles" size={14} />
          <span>{t('header.aiAssistant')}</span>
        </button>

        <div className="screenshot-header__quick-icons" aria-label={t('header.quickActions')}>
          {QUICK_ACTIONS.map((action) => {
            const label = t(`quick.actions.${action.id}.title`);
            return (
              <IconButton
                key={action.id}
                label={label}
                variant="ghost"
                className="screenshot-header__quick-icon"
                onClick={() => openQuickAction(action.id)}
              >
                <IhIcon name={action.icon} size={14} />
              </IconButton>
            );
          })}
        </div>

        <div className="screenshot-header__quick-compact">
          <IconButton
            label={t('header.quickActions')}
            variant="ghost"
            className="screenshot-header__quick-icon"
            aria-expanded={quickMenuOpen}
            onClick={() => setQuickMenuOpen((current) => !current)}
          >
            <IhIcon name="plus" size={15} />
          </IconButton>
          {quickMenuOpen ? (
            <div className="screenshot-header__quick-menu" role="menu">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.id}
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setQuickMenuOpen(false);
                    openQuickAction(action.id);
                  }}
                >
                  <IhIcon name={action.icon} size={14} />
                  {t(`quick.actions.${action.id}.title`)}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="screenshot-header__language" aria-label={t('header.language')}>
          {(['tr', 'en'] as const).map((item) => (
            <button
              key={item}
              type="button"
              className={locale === item ? 'is-active' : ''}
              aria-pressed={locale === item}
              disabled={isPending}
              onClick={() => changeLocale(item)}
            >
              {item.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="screenshot-header__display-settings" ref={displaySettingsRef}>
          <IconButton
            label={t('header.displaySettings')}
            variant="ghost"
            className="screenshot-header__quick-icon"
            aria-expanded={displaySettingsOpen}
            onClick={() => setDisplaySettingsOpen((current) => !current)}
          >
            <IhIcon name="settings" size={15} />
          </IconButton>
          {displaySettingsOpen ? (
            <div
              className="screenshot-header__display-popover"
              role="group"
              aria-label={t('header.displaySettings')}
            >
              <fieldset>
                <legend>{t('preferences.density')}</legend>
                <div className="screenshot-header__density-options">
                  {DASHBOARD_DENSITIES.map((option) => (
                    <button
                      key={option}
                      type="button"
                      className={density === option ? 'is-active' : ''}
                      aria-pressed={density === option}
                      onClick={() => setDensity(option)}
                    >
                      {t(`preferences.densities.${option}`)}
                    </button>
                  ))}
                </div>
              </fieldset>
              <label htmlFor="screenshot-dashboard-currency">
                <span>{t('preferences.currency')}</span>
                <select
                  id="screenshot-dashboard-currency"
                  value={currency}
                  onChange={(event) =>
                    setCurrency(event.target.value as (typeof DASHBOARD_CURRENCIES)[number])
                  }
                >
                  {DASHBOARD_CURRENCIES.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <small>{t('preferences.localOnly')}</small>
            </div>
          ) : null}
        </div>

        <button
          type="button"
          className="screenshot-header__notification"
          aria-label={t('header.notifications')}
          onClick={openNotifications}
        >
          <IhIcon name="bell" size={17} />
          <span className="screenshot-header__badge" aria-label={t('header.unreadCount', { count: unreadCount })}>
            {unreadCount}
          </span>
        </button>
        <span className="screenshot-header__divider" aria-hidden="true" />
        <div className="screenshot-header__profile">
          <span className="screenshot-header__avatar" aria-hidden="true">EB</span>
          <span className="screenshot-header__identity">
            <strong>Emin Bilgin</strong>
            <small>{t('header.profileRole')}</small>
          </span>
          <IhIcon name="chevronDown" size={13} />
        </div>
      </div>
    </div>
  );
}

export function ScreenshotDashboardHeader() {
  const { canSearch, openPalette } = useGlobalSearch();
  const locale = useLocale() as AppLocale;
  const router = useRouter();
  const { setPreferredLocale } = useAuth();
  const [isPending, startTransition] = useTransition();

  const changeLocale = (nextLocale: AppLocale) => {
    if (nextLocale === locale || !(locales as readonly string[]).includes(nextLocale)) {
      return;
    }
    writeLocaleCookie(nextLocale);
    startTransition(() => {
      void (async () => {
        await setPreferredLocale(nextLocale);
        router.refresh();
      })();
    });
  };

  return (
    <ScreenshotDashboardHeaderCore
      canSearch={canSearch}
      openPalette={openPalette}
      locale={locale}
      isPending={isPending}
      changeLocale={changeLocale}
    />
  );
}

/**
 * The exact Dashboard header surface with local-only preview wiring.
 * It intentionally avoids auth, search and route mutations.
 */
export function ScreenshotDashboardPreviewHeader() {
  const configuredLocale = useLocale() as AppLocale;
  const [locale, setLocale] = useState<AppLocale>(configuredLocale);

  return (
    <ScreenshotDashboardHeaderCore
      canSearch
      openPalette={() => undefined}
      locale={locale}
      isPending={false}
      changeLocale={setLocale}
    />
  );
}

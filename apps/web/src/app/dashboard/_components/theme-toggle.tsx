'use client';

import { useTranslations } from 'next-intl';

import { useTheme, type ThemeMode } from '@/lib/theme/theme-context';

export function ThemeToggle() {
  const t = useTranslations('theme');
  const { mode, setMode } = useTheme();

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setMode(event.target.value as ThemeMode);
  };

  return (
    <label className="app-header__theme">
      <span className="app-header__theme-label">{t('label')}</span>
      <select
        className="app-header__theme-select"
        value={mode}
        onChange={handleChange}
        aria-label={t('label')}
      >
        <option value="light">{t('light')}</option>
        <option value="dark">{t('dark')}</option>
        <option value="system">{t('system')}</option>
      </select>
    </label>
  );
}

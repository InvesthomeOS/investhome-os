'use client';

import { useTranslations } from 'next-intl';

interface MessagesSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function MessagesSearchBar({
  value,
  onChange,
  placeholder = 'Search messages, tasks, announcements…',
}: MessagesSearchBarProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <div className="inv-msg-search">
      <span className="inv-msg-search__icon" aria-hidden="true">
        ⌕
      </span>
      <input
        type="search"
        className="inv-msg-search__input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={tChrome('k0a16590e9c')}
      />
      {value ? (
        <button
          type="button"
          className="inv-msg-search__clear"
          onClick={() => onChange('')}
          aria-label={tChrome('k67300d0fed')}
        >
          ×
        </button>
      ) : null}
    </div>
  );
}

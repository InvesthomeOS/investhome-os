'use client';

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
        aria-label="Search messages module"
      />
      {value ? (
        <button
          type="button"
          className="inv-msg-search__clear"
          onClick={() => onChange('')}
          aria-label="Clear search"
        >
          ×
        </button>
      ) : null}
    </div>
  );
}

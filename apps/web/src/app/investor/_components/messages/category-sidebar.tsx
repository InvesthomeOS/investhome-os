'use client';

import type { MessageCategory } from '../../_data/messaging-types';

interface CategorySidebarProps {
  activeCategory: MessageCategory;
  onCategoryChange: (category: MessageCategory) => void;
  counts: Record<MessageCategory, number>;
}

const CATEGORIES: { id: MessageCategory; label: string; icon: string }[] = [
  { id: 'inbox', label: 'Inbox', icon: '📥' },
  { id: 'announcements', label: 'Announcements', icon: '📢' },
  { id: 'project_updates', label: 'Project Updates', icon: '🏗' },
  { id: 'financial', label: 'Financial', icon: '$' },
  { id: 'documents', label: 'Documents', icon: '📄' },
  { id: 'signatures', label: 'Signatures', icon: '✍' },
  { id: 'support', label: 'Support', icon: '💬' },
  { id: 'archived', label: 'Archived', icon: '📦' },
  { id: 'starred', label: 'Starred', icon: '★' },
  { id: 'unread', label: 'Unread', icon: '●' },
  { id: 'all', label: 'All', icon: '☰' },
];

export function CategorySidebar({
  activeCategory,
  onCategoryChange,
  counts,
}: CategorySidebarProps) {
  return (
    <nav className="inv-msg-categories" aria-label="Message categories">
      <ul className="inv-msg-categories__list">
        {CATEGORIES.map((cat) => (
          <li key={cat.id}>
            <button
              type="button"
              className={`inv-msg-categories__btn${activeCategory === cat.id ? ' inv-msg-categories__btn--active' : ''}`}
              onClick={() => onCategoryChange(cat.id)}
              aria-current={activeCategory === cat.id ? 'true' : undefined}
            >
              <span className="inv-msg-categories__icon" aria-hidden="true">
                {cat.icon}
              </span>
              <span className="inv-msg-categories__label">{cat.label}</span>
              {counts[cat.id] > 0 ? (
                <span className="inv-msg-categories__count">{counts[cat.id]}</span>
              ) : null}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

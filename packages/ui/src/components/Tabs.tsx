import type { ReactNode } from 'react';

export interface TabItem {
  id: string;
  label: string;
  disabled?: boolean;
}

export interface TabsProps {
  tabs: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  ariaLabel?: string;
  className?: string;
}

export function Tabs({ tabs, activeId, onChange, ariaLabel, className }: TabsProps) {
  return (
    <div className={`ih-tabs${className ? ` ${className}` : ''}`} role="tablist" aria-label={ariaLabel}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={tab.id === activeId}
          disabled={tab.disabled}
          className={`ih-tabs__tab${tab.id === activeId ? ' ih-tabs__tab--active' : ''}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

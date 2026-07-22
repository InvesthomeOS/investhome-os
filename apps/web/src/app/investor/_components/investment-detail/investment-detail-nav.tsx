'use client';

import { useCallback, useEffect, useRef } from 'react';

import {
  INVESTMENT_DETAIL_TABS,
  type InvestmentDetailTab,
} from '../../_data/investment-detail-types';

export interface InvestmentDetailNavProps {
  activeTab: InvestmentDetailTab;
  onTabChange: (tab: InvestmentDetailTab) => void;
}

export function InvestmentDetailNav({ activeTab, onTabChange }: InvestmentDetailNavProps) {
  const navRef = useRef<HTMLElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, tab: InvestmentDetailTab, index: number) => {
      const tabs = INVESTMENT_DETAIL_TABS;
      let nextIndex = index;

      if (e.key === 'ArrowRight') {
        e.preventDefault();
        nextIndex = (index + 1) % tabs.length;
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        nextIndex = (index - 1 + tabs.length) % tabs.length;
      } else if (e.key === 'Home') {
        e.preventDefault();
        nextIndex = 0;
      } else if (e.key === 'End') {
        e.preventDefault();
        nextIndex = tabs.length - 1;
      } else {
        return;
      }

      onTabChange(tabs[nextIndex]!.id);
      const btn = navRef.current?.querySelector<HTMLButtonElement>(
        `[data-tab="${tabs[nextIndex]!.id}"]`,
      );
      btn?.focus();
    },
    [onTabChange],
  );

  useEffect(() => {
    const btn = navRef.current?.querySelector<HTMLButtonElement>(`[data-tab="${activeTab}"]`);
    btn?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }, [activeTab]);

  return (
    <nav
      ref={navRef}
      className="inv-detail-nav"
      aria-label="Investment detail sections"
    >
      <div className="inv-detail-nav__scroll" role="tablist">
        {INVESTMENT_DETAIL_TABS.map((tab, index) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            data-tab={tab.id}
            id={`tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            className={`inv-detail-nav__tab${activeTab === tab.id ? ' inv-detail-nav__tab--active' : ''}`}
            onClick={() => onTabChange(tab.id)}
            onKeyDown={(e) => handleKeyDown(e, tab.id, index)}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </nav>
  );
}

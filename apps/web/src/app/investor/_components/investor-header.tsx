'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { IhIcon } from '@/components/icons/ih-icons';

import { investorProfile, notifications } from '../_data/mock-data';
import { formatInvestorDateTime } from '../_data/mock-data';

export function InvestorHeader() {
  const t = useTranslations('investorPortal');
  const [searchQuery, setSearchQuery] = useState('');
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const closeDropdown = useCallback(() => setNotificationsOpen(false), []);

  useEffect(() => {
    if (!notificationsOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        closeDropdown();
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [notificationsOpen, closeDropdown]);

  return (
    <header className="app-header investor-header">
      <div className="investor-header__search app-header__left">
        <span className="investor-header__search-icon" aria-hidden="true">
          <IhIcon name="search" size={16} />
        </span>
        <input
          type="search"
          className="investor-header__search-input"
          placeholder={t('header.searchPlaceholder')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label={t('header.searchAria')}
        />
      </div>

      <div className="investor-header__actions app-header__actions">
        <button type="button" className="app-header__quick investor-header__action-btn--primary">
          <IhIcon name="plus" size={15} />
          <span>{t('header.quickActions')}</span>
        </button>

        <div className="investor-header__notification" ref={dropdownRef}>
          <button
            type="button"
            className="app-header__icon-btn"
            onClick={() => setNotificationsOpen((prev) => !prev)}
            aria-expanded={notificationsOpen}
            aria-haspopup="true"
            aria-label={
              unreadCount > 0
                ? t('header.notificationsUnread', { count: unreadCount })
                : t('header.notifications')
            }
          >
            <IhIcon name="bell" size={18} />
            {unreadCount > 0 ? (
              <span className="investor-header__notification-badge">{unreadCount}</span>
            ) : null}
          </button>

          {notificationsOpen ? (
            <div className="investor-header__dropdown" role="menu">
              <div className="investor-header__dropdown-header">{t('header.notifications')}</div>
              {notifications.map((notif) => (
                <div
                  key={notif.id}
                  className={`investor-header__dropdown-item${!notif.read ? ' investor-header__dropdown-item--unread' : ''}`}
                  role="menuitem"
                >
                  <p className="investor-header__dropdown-item-title">{notif.title}</p>
                  <p className="investor-header__dropdown-item-msg">{notif.message}</p>
                  <time
                    className="inv-timeline__time"
                    dateTime={notif.timestamp}
                    style={{ marginTop: '0.25rem', display: 'block' }}
                  >
                    {formatInvestorDateTime(notif.timestamp)}
                  </time>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <Link href={'/investor/profile' as Route} className="app-header__user">
          <span className="app-header__avatar" aria-hidden="true">
            {investorProfile.avatarInitials}
          </span>
          <div className="app-header__user-meta">
            <span className="app-header__user-name">{investorProfile.name}</span>
          </div>
        </Link>
      </div>
    </header>
  );
}

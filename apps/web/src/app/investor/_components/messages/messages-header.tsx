'use client';

interface MessagesHeaderProps {
  onCompose: () => void;
  onAnnouncements: () => void;
  onNotifications: () => void;
  unreadAnnouncements: number;
  unreadNotifications: number;
}

export function MessagesHeader({
  onCompose,
  onAnnouncements,
  onNotifications,
  unreadAnnouncements,
  unreadNotifications,
}: MessagesHeaderProps) {
  return (
    <header className="inv-msg-page-header">
      <div>
        <h1 className="investor-page__title">Messages</h1>
        <p className="investor-page__subtitle">
          Communications with your relationship manager and investment team.
        </p>
      </div>
      <div className="inv-msg-page-header__actions">
        <button type="button" className="inv-msg-page-header__btn inv-msg-page-header__btn--primary" onClick={onCompose}>
          + Compose Message
        </button>
        <button type="button" className="inv-msg-page-header__btn" onClick={onAnnouncements}>
          Announcements
          {unreadAnnouncements > 0 ? (
            <span className="inv-msg-page-header__badge">{unreadAnnouncements}</span>
          ) : null}
        </button>
        <button type="button" className="inv-msg-page-header__btn" onClick={onNotifications}>
          Notifications
          {unreadNotifications > 0 ? (
            <span className="inv-msg-page-header__badge">{unreadNotifications}</span>
          ) : null}
        </button>
      </div>
    </header>
  );
}

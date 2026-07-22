'use client';

import type { ReactNode } from 'react';

interface MessagesLayoutProps {
  sidebar: ReactNode;
  list: ReactNode;
  main: ReactNode;
}

export function MessagesLayout({ sidebar, list, main }: MessagesLayoutProps) {
  return (
    <div className="inv-msg-layout">
      <aside className="inv-msg-layout__sidebar">{sidebar}</aside>
      <div className="inv-msg-layout__list">{list}</div>
      <main className="inv-msg-layout__main">{main}</main>
    </div>
  );
}

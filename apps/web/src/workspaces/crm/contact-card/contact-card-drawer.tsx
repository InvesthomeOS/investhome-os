'use client';

import { useEffect, useState } from 'react';
import { useLocale } from 'next-intl';
import { Drawer } from '@investhome/ui';

import { personCardCopy } from './person-card-copy';
import { UnifiedContactCard } from './unified-contact-card';

import './contact-card.css';

type ContactCardDrawerProps = {
  contactId: string;
  onClose: () => void;
};

export function ContactCardDrawer({ contactId, onClose }: ContactCardDrawerProps) {
  const t = personCardCopy(useLocale());
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 768px)');
    const sync = () => setCompact(media.matches);
    sync();
    media.addEventListener('change', sync);
    return () => media.removeEventListener('change', sync);
  }, []);

  return (
    <div className="crm-contact-card-drawer" data-testid="unified-contact-card-drawer">
      <Drawer
        open
        onClose={onClose}
        title={t.title}
        size={compact ? 'full' : 'lg'}
        ariaLabel="Unified CRM contact card"
      >
        <UnifiedContactCard contactId={contactId} variant="drawer" />
      </Drawer>
    </div>
  );
}

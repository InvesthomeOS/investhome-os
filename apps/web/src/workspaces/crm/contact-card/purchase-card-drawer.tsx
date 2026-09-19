'use client';

import { useEffect, useState } from 'react';
import { Drawer } from '@investhome/ui';

import { PurchaseCard } from './purchase-card';

import './contact-card.css';

type PurchaseCardDrawerProps = {
  agreementId: string;
  onClose: () => void;
};

export function PurchaseCardDrawer({ agreementId, onClose }: PurchaseCardDrawerProps) {
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 768px)');
    const sync = () => setCompact(media.matches);
    sync();
    media.addEventListener('change', sync);
    return () => media.removeEventListener('change', sync);
  }, []);

  return (
    <div className="crm-contact-card-drawer" data-testid="purchase-card-drawer">
      <Drawer
        open
        onClose={onClose}
        title="Satın alma"
        size={compact ? 'full' : 'lg'}
        ariaLabel="Satın alma detayı"
      >
        <PurchaseCard agreementId={agreementId} />
      </Drawer>
    </div>
  );
}

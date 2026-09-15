'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { ContactCardDrawer } from './contact-card-drawer';

export const CRM_CONTACT_UPDATED_EVENT = 'crm-contact-updated';

type ContactCardContextValue = {
  contactId: string | null;
  openContact: (contactId: string) => void;
  closeContact: () => void;
};

const ContactCardContext = createContext<ContactCardContextValue | null>(null);

function isContactFullPage(pathname: string | null): boolean {
  return Boolean(pathname && /^\/workspaces\/crm\/contacts\/[0-9a-fA-F-]{36}$/.test(pathname));
}

function readContactParam(): string | null {
  if (typeof window === 'undefined') return null;
  return new URLSearchParams(window.location.search).get('contact');
}

export function notifyContactUpdated(contactId: string) {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(CRM_CONTACT_UPDATED_EVENT, { detail: { contactId } }));
}

export function ContactCardProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [contactId, setContactId] = useState<string | null>(null);
  const fullPage = isContactFullPage(pathname);

  useEffect(() => {
    setContactId(fullPage ? null : readContactParam());
  }, [fullPage, pathname]);

  useEffect(() => {
    const onPopState = () => setContactId(fullPage ? null : readContactParam());
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [fullPage]);

  const pushContactUrl = useCallback(
    (id: string | null) => {
      const params = new URLSearchParams(typeof window === 'undefined' ? '' : window.location.search);
      params.delete('opportunity');
      if (id) params.set('contact', id);
      else params.delete('contact');
      const qs = params.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  const openContact = useCallback(
    (id: string) => {
      if (fullPage) return;
      setContactId(id);
      pushContactUrl(id);
    },
    [fullPage, pushContactUrl],
  );

  const closeContact = useCallback(() => {
    setContactId(null);
    pushContactUrl(null);
  }, [pushContactUrl]);

  const value = useMemo(
    () => ({ contactId: fullPage ? null : contactId, openContact, closeContact }),
    [closeContact, contactId, fullPage, openContact],
  );

  return (
    <ContactCardContext.Provider value={value}>
      {children}
      {value.contactId ? (
        <ContactCardDrawer contactId={value.contactId} onClose={closeContact} />
      ) : null}
    </ContactCardContext.Provider>
  );
}

export function useContactCard(): ContactCardContextValue {
  const ctx = useContext(ContactCardContext);
  const router = useRouter();
  if (ctx) return ctx;
  return {
    contactId: null,
    openContact: (id: string) => {
      router.push(`/workspaces/crm/contacts/${id}`);
    },
    closeContact: () => undefined,
  };
}

export function opportunityContactId(opportunity: {
  crm_contact_id?: string | null;
  party_type?: string | null;
  party_id?: string | null;
}): string | null {
  if (opportunity.crm_contact_id) return opportunity.crm_contact_id;
  if (opportunity.party_type === 'crm_contact' && opportunity.party_id) return opportunity.party_id;
  return null;
}

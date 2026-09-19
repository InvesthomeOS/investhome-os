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
import { PurchaseCardDrawer } from './purchase-card-drawer';
import { salesDetailUrl } from './pilot-people';

export const CRM_CONTACT_UPDATED_EVENT = 'crm-contact-updated';

type ContactCardOpenOptions = {
  projectGroup?: string;
};

type ContactCardContextValue = {
  contactId: string | null;
  purchaseId: string | null;
  openContact: (contactId: string, options?: ContactCardOpenOptions) => void;
  openPurchase: (agreementId: string) => void;
  closeContact: () => void;
  closePurchase: () => void;
};

const ContactCardContext = createContext<ContactCardContextValue | null>(null);

function isContactFullPage(pathname: string | null): boolean {
  return Boolean(pathname && /^\/workspaces\/crm\/contacts\/[0-9a-fA-F-]{36}$/.test(pathname));
}

function readParam(name: string): string | null {
  if (typeof window === 'undefined') return null;
  return new URLSearchParams(window.location.search).get(name);
}

export function notifyContactUpdated(contactId: string) {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(CRM_CONTACT_UPDATED_EVENT, { detail: { contactId } }));
}

export function purchaseCardUrl(agreementId: string): string {
  return `/workspaces/crm/agreements?purchase=${agreementId}`;
}

function personIdFromPath(pathname: string | null): string | null {
  const match = pathname?.match(/\/contacts\/([0-9a-fA-F-]{36})(?:\/|$)/);
  return match?.[1] || null;
}

export function ContactCardProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [contactId, setContactId] = useState<string | null>(() => (typeof window === 'undefined' ? null : readParam('contact')));
  const [purchaseId, setPurchaseId] = useState<string | null>(() => (typeof window === 'undefined' ? null : readParam('purchase')));
  const fullPage = isContactFullPage(pathname);
  const pathPersonId = personIdFromPath(pathname);
  const personPage = fullPage || Boolean(pathname?.includes('/satin-alma/'));

  useEffect(() => {
    setContactId(fullPage ? null : readParam('contact'));
    setPurchaseId(personPage ? null : readParam('purchase'));
    const purchase = readParam('purchase');
    if (purchase && fullPage && pathPersonId && !pathname?.includes('/satin-alma/')) {
      router.replace(salesDetailUrl(pathPersonId, purchase));
    }
  }, [fullPage, pathPersonId, pathname, personPage, router]);

  useEffect(() => {
    const onPopState = () => {
      setContactId(fullPage ? null : readParam('contact'));
      setPurchaseId(personPage ? null : readParam('purchase'));
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [fullPage, personPage]);

  const pushUrl = useCallback(
    (nextContact: string | null, nextPurchase: string | null) => {
      const params = new URLSearchParams(typeof window === 'undefined' ? '' : window.location.search);
      params.delete('opportunity');
      params.delete('project');
      if (nextPurchase) {
        params.set('purchase', nextPurchase);
        params.delete('contact');
      } else {
        params.delete('purchase');
        if (nextContact) params.set('contact', nextContact);
        else params.delete('contact');
      }
      const qs = params.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  const openContact = useCallback(
    (id: string, _options?: ContactCardOpenOptions) => {
      if (fullPage) {
        router.push(`/workspaces/crm/contacts/${id}`);
        return;
      }
      setPurchaseId(null);
      setContactId(id);
      pushUrl(id, null);
    },
    [fullPage, pushUrl, router],
  );

  const openPurchase = useCallback(
    (id: string) => {
      if (pathPersonId) {
        router.push(salesDetailUrl(pathPersonId, id));
        return;
      }
      setPurchaseId(id);
      if (fullPage || pathname?.startsWith('/workspaces/crm/agreements')) {
        pushUrl(fullPage ? null : contactId, id);
        return;
      }
      router.push(purchaseCardUrl(id), { scroll: false });
    },
    [contactId, fullPage, pathPersonId, pathname, pushUrl, router],
  );

  const closeContact = useCallback(() => {
    setContactId(null);
    pushUrl(null, purchaseId);
  }, [purchaseId, pushUrl]);

  const closePurchase = useCallback(() => {
    setPurchaseId(null);
    if (fullPage) {
      const params = new URLSearchParams(typeof window === 'undefined' ? '' : window.location.search);
      params.delete('purchase');
      const qs = params.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname || '/workspaces/crm/contacts', { scroll: false });
      return;
    }
    pushUrl(contactId, null);
  }, [contactId, fullPage, pathname, pushUrl, router]);

  const overlayPurchaseId = pathname?.includes('/satin-alma/') || fullPage ? null : purchaseId;

  const value = useMemo(
    () => ({
      contactId: fullPage ? null : contactId,
      purchaseId,
      openContact,
      openPurchase,
      closeContact,
      closePurchase,
    }),
    [closeContact, closePurchase, contactId, fullPage, openContact, openPurchase, purchaseId],
  );

  return (
    <ContactCardContext.Provider value={value}>
      {children}
      {overlayPurchaseId ? (
        <PurchaseCardDrawer agreementId={overlayPurchaseId} onClose={closePurchase} />
      ) : value.contactId ? (
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
    purchaseId: null,
    openContact: (id: string) => {
      router.push(`/workspaces/crm/contacts/${id}`);
    },
    openPurchase: (id: string) => {
      router.push(purchaseCardUrl(id));
    },
    closeContact: () => undefined,
    closePurchase: () => undefined,
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

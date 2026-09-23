'use client';

import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, Input, LoadingState, Select, StatusChip } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { canManageCommunicationAccounts } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  disconnectCommunicationAccount,
  fetchGmailStatus,
  registerCommunicationAccount,
  startGmailAuthorize,
  syncCommunicationAccount,
} from '@/workspaces/crm/api/communication';
import { communicationQueries, communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';

const EMAIL_PROVIDERS = [
  { value: 'm365', label: 'Microsoft 365' },
  { value: 'graph', label: 'Microsoft Graph' },
  { value: 'imap', label: 'IMAP' },
  { value: 'smtp', label: 'SMTP' },
];

const WHATSAPP_PROVIDERS = [
  { value: 'whatsapp_business', label: 'WhatsApp Business' },
  { value: 'meta', label: 'Meta Cloud API' },
  { value: 'wazzup', label: 'Wazzup' },
  { value: 'twilio', label: 'Twilio' },
];

function statusTone(status: string): 'success' | 'warning' | 'danger' | 'info' | 'default' {
  if (status === 'connected') return 'success';
  if (status === 'pending' || status === 'not_connected' || status === 'needs_reauth') return 'warning';
  if (status === 'error' || status === 'disconnected') return 'danger';
  return 'default';
}

function healthTone(health: string): 'success' | 'warning' | 'danger' | 'info' | 'default' {
  if (health === 'healthy') return 'success';
  if (health === 'degraded') return 'warning';
  if (health === 'error') return 'danger';
  return 'default';
}

function formatWhen(value: string | null, locale: string) {
  if (!value) return '—';
  return new Date(value).toLocaleString(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function CommunicationAccountsView() {
  const t = useTranslations('crm.settings.communicationAccounts');
  const tCommon = useTranslations('common');
  const { authLoading, user } = useCrmAccess();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const canManage = canManageCommunicationAccounts(user);
  const [channel, setChannel] = useState<'email' | 'whatsapp'>('email');
  const [provider, setProvider] = useState('m365');
  const [identity, setIdentity] = useState('');
  const [label, setLabel] = useState('');
  const [userId, setUserId] = useState(user?.id ?? '');
  const [banner, setBanner] = useState<string | null>(null);
  const [bannerError, setBannerError] = useState<string | null>(null);

  const accountsQuery = useQuery({
    ...communicationQueries.accounts(),
    enabled: !authLoading && Boolean(user),
  });

  const gmailStatusQuery = useQuery({
    queryKey: [...communicationQueryKeys.accounts, 'gmail-status'],
    queryFn: fetchGmailStatus,
    enabled: !authLoading && Boolean(user),
  });

  const usersQuery = useQuery({
    queryKey: ['crm', 'users', 'communication-accounts'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canManage,
  });

  const providers = channel === 'email' ? EMAIL_PROVIDERS : WHATSAPP_PROVIDERS;
  const ownerNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of usersQuery.data?.items ?? []) {
      map.set(item.id, item.full_name);
    }
    return map;
  }, [usersQuery.data]);

  const registerMutation = useMutation({
    mutationFn: registerCommunicationAccount,
    onSuccess: () => {
      setIdentity('');
      setLabel('');
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.accounts });
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: disconnectCommunicationAccount,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.accounts });
    },
  });

  const syncMutation = useMutation({
    mutationFn: syncCommunicationAccount,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.accounts });
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.unmatched() });
      setBanner(t('syncStarted'));
    },
    onError: () => setBannerError(t('syncFailed')),
  });

  const connectMutation = useMutation({
    mutationFn: startGmailAuthorize,
    onSuccess: (body) => {
      window.location.assign(body.authorize_url);
    },
    onError: () => setBannerError(t('gmailNotConfigured')),
  });

  useEffect(() => {
    const status = searchParams.get('gmail');
    if (status === 'connected') {
      setBanner(t('gmailConnected'));
      const accountId = searchParams.get('account_id');
      if (accountId && canManage) {
        syncMutation.mutate(accountId);
      }
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.accounts });
    } else if (status === 'error') {
      const reason = searchParams.get('reason') || 'oauth_error';
      setBannerError(t('gmailConnectFailed', { reason }));
    }
    // Connect landing should fire once per querystring, not on every mutation identity change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!user) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  const items = accountsQuery.data?.items ?? [];
  const gmailConfigured = gmailStatusQuery.data?.configured ?? false;

  return (
    <div className="crm-communication-subview" data-testid="crm-communication-accounts">
      <header className="crm-communication-subview__header">
        <h2>{t('title')}</h2>
        <p>{t('subtitle')}</p>
      </header>

      {banner ? <p className="crm-live-comm__banner">{banner}</p> : null}
      {bannerError ? <p className="crm-live-comm__error">{bannerError}</p> : null}

      {canManage ? (
        <section className="crm-communication-subview__form crm-gmail-connect">
          <h3>{t('gmailTitle')}</h3>
          <p className="crm-live-comm__hint">{t('gmailHint')}</p>
          <Button
            type="button"
            onClick={() => connectMutation.mutate()}
            disabled={connectMutation.isPending || !gmailConfigured}
          >
            {t('gmailConnect')}
          </Button>
          {!gmailConfigured ? <p className="crm-live-comm__hint">{t('gmailNotConfigured')}</p> : null}
        </section>
      ) : null}

      {canManage ? (
        <form
          className="crm-communication-subview__form"
          onSubmit={(event) => {
            event.preventDefault();
            registerMutation.mutate({
              user_id: userId || user.id,
              channel_type: channel,
              provider,
              identity: identity.trim(),
              account_label: label.trim() || undefined,
            });
          }}
        >
          <h3>{t('registerTitle')}</h3>
          <p className="crm-live-comm__hint">{t('noCredentialsHint')}</p>
          <label className="crm-form-field">
            <span>{t('fields.user')}</span>
            <Select
              value={userId || user.id}
              onChange={(event) => setUserId(event.target.value)}
              aria-label={t('fields.user')}
            >
              {(usersQuery.data?.items ?? [{ id: user.id, full_name: user.full_name }]).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.full_name}
                </option>
              ))}
            </Select>
          </label>
          <label className="crm-form-field">
            <span>{t('fields.channel')}</span>
            <Select
              value={channel}
              onChange={(event) => {
                const next = event.target.value as 'email' | 'whatsapp';
                setChannel(next);
                setProvider(next === 'email' ? 'm365' : 'whatsapp_business');
              }}
            >
              <option value="email">{t('channels.email')}</option>
              <option value="whatsapp">{t('channels.whatsapp')}</option>
            </Select>
          </label>
          <label className="crm-form-field">
            <span>{t('fields.provider')}</span>
            <Select value={provider} onChange={(event) => setProvider(event.target.value)}>
              {providers.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </Select>
          </label>
          <label className="crm-form-field">
            <span>{t('fields.identity')}</span>
            <Input
              value={identity}
              onChange={(event) => setIdentity(event.target.value)}
              placeholder={channel === 'email' ? t('placeholders.email') : t('placeholders.phone')}
              required
            />
          </label>
          <label className="crm-form-field">
            <span>{t('fields.label')}</span>
            <Input value={label} onChange={(event) => setLabel(event.target.value)} />
          </label>
          <Button type="submit" disabled={registerMutation.isPending || !identity.trim()}>
            {t('register')}
          </Button>
          {registerMutation.isError ? <p className="crm-live-comm__error">{t('registerFailed')}</p> : null}
        </form>
      ) : (
        <p className="crm-live-comm__hint">{t('viewOnlyHint')}</p>
      )}

      {accountsQuery.isLoading ? (
        <LoadingState label={t('loading')} />
      ) : items.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <div className="crm-live-comm__table-wrap">
          <table className="crm-live-comm__table">
            <thead>
              <tr>
                <th>{t('columns.user')}</th>
                <th>{t('columns.channel')}</th>
                <th>{t('columns.account')}</th>
                <th>{t('columns.status')}</th>
                <th>{t('columns.health')}</th>
                <th>{t('columns.lastSync')}</th>
                {canManage ? <th>{t('columns.actions')}</th> : null}
              </tr>
            </thead>
            <tbody>
              {items.map((account) => (
                <tr key={account.id}>
                  <td>{account.user_name || ownerNameById.get(account.user_id) || account.user_id}</td>
                  <td>{account.channel_type === 'whatsapp' ? t('channels.whatsapp') : t('channels.email')}</td>
                  <td>
                    <strong>{account.account_label || account.identity}</strong>
                    <div className="crm-live-comm__meta">{account.identity}</div>
                    <div className="crm-live-comm__meta">{account.provider}</div>
                    {account.last_error ? <div className="crm-live-comm__error">{account.last_error}</div> : null}
                  </td>
                  <td>
                    <StatusChip tone={statusTone(account.status)}>{t(`status.${account.status}`)}</StatusChip>
                  </td>
                  <td>
                    <StatusChip tone={healthTone(account.health)}>{t(`health.${account.health}`)}</StatusChip>
                  </td>
                  <td>{formatWhen(account.last_sync_at, 'tr-TR')}</td>
                  {canManage ? (
                    <td>
                      <div className="crm-live-comm__row-actions">
                        {account.provider === 'gmail' && account.status !== 'disconnected' ? (
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            onClick={() => syncMutation.mutate(account.id)}
                            disabled={syncMutation.isPending || account.status === 'needs_reauth'}
                          >
                            {t('syncNow')}
                          </Button>
                        ) : null}
                        {account.status === 'needs_reauth' ? (
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => connectMutation.mutate()}
                            disabled={connectMutation.isPending || !gmailConfigured}
                          >
                            {t('gmailConnect')}
                          </Button>
                        ) : null}
                        {account.status !== 'disconnected' ? (
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            onClick={() => disconnectMutation.mutate(account.id)}
                            disabled={disconnectMutation.isPending}
                          >
                            {t('disconnect')}
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

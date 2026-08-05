'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  Button,
  Input,
  KpiCard,
  ProgressBar,
  Select,
  StatusChip,
  Tabs,
} from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  ADMIN_AI_ACTIONS,
  ADMIN_KPI_ICONS,
  ADMIN_LAST_LOGIN_ORDER,
  ADMIN_ROLE_ORDER,
  ADMIN_STATUS_ORDER,
  ADMIN_TAB_ORDER,
  ADMIN_WORKSPACE_ORDER,
  type AdminAvatarTone,
  type AdminRoleKey,
  type AdminStatusKey,
  type AdminTabKey,
  type AdminUserRow,
  type AdminWorkspacePreview,
} from '../admin-model';

type FilterKey = 'search' | 'role' | 'workspace' | 'status' | 'lastLogin';

const ROLE_TONE: Record<AdminRoleKey, 'success' | 'warning' | 'info' | 'default' | 'danger'> = {
  systemAdmin: 'info',
  admin: 'info',
  salesManager: 'warning',
  salesRep: 'success',
  analyst: 'info',
  support: 'default',
  marketing: 'danger',
};

const STATUS_TONE: Record<AdminStatusKey, 'success' | 'warning' | 'info' | 'default' | 'danger'> = {
  active: 'success',
  inactive: 'danger',
  suspended: 'warning',
};

function UserAvatar({
  initials,
  tone,
  size = 'md',
}: {
  initials: string;
  tone: AdminAvatarTone;
  size?: 'sm' | 'md';
}) {
  return (
    <span className={`admin-ws__avatar is-${tone} is-${size}`} aria-hidden="true">
      {initials}
    </span>
  );
}

function RowActions() {
  const t = useTranslations('crm.admin');

  return (
    <div className="admin-ws__row-actions">
      <button
        type="button"
        className="admin-ws__icon-action"
        aria-label={t('actions.detail')}
        title={t('actions.detail')}
      >
        <IhIcon name="search" size={14} />
      </button>
      <button
        type="button"
        className="admin-ws__icon-action"
        aria-label={t('actions.edit')}
        title={t('actions.edit')}
      >
        <IhIcon name="settings" size={14} />
      </button>
      <button
        type="button"
        className="admin-ws__icon-action"
        aria-label={t('actions.permission')}
        title={t('actions.permission')}
      >
        <IhIcon name="permissions" size={14} />
      </button>
      <button
        type="button"
        className="admin-ws__icon-action is-danger"
        aria-label={t('actions.delete')}
        title={t('actions.delete')}
      >
        <IhIcon name="alert" size={14} />
      </button>
      <button
        type="button"
        className="admin-ws__icon-action"
        aria-label={t('actions.more')}
        title={t('actions.more')}
      >
        <IhIcon name="chevronDown" size={14} />
      </button>
    </div>
  );
}

function ApiSparkline({
  points,
  label,
}: {
  points: number[];
  label: string;
}) {
  const max = Math.max(...points, 1);
  const min = Math.min(...points, 0);
  const range = Math.max(max - min, 1);
  const width = 220;
  const height = 56;
  const pad = 4;
  const coords = points
    .map((value, index) => {
      const x = pad + (index / Math.max(points.length - 1, 1)) * (width - pad * 2);
      const y = height - pad - ((value - min) / range) * (height - pad * 2);
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg
      className="admin-ws__sparkline"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={label}
    >
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={coords}
      />
    </svg>
  );
}

export function AdminWorkspace({
  preview,
  onOpenAi,
}: {
  preview: AdminWorkspacePreview;
  onOpenAi?: (prompt?: string) => void;
}) {
  const t = useTranslations('crm.admin');
  const [aiAction, setAiAction] = useState<string | null>('newUser');
  const [activeTab, setActiveTab] = useState<AdminTabKey>('users');
  const [filters, setFilters] = useState<Record<FilterKey, string>>({
    search: '',
    role: '',
    workspace: '',
    status: '',
    lastLogin: '',
  });
  const [checkedIds, setCheckedIds] = useState<Record<string, boolean>>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const filteredUsers = useMemo(() => {
    return preview.users.filter((row) => {
      if (filters.role && row.role !== filters.role) return false;
      if (filters.workspace && row.workspace !== filters.workspace) return false;
      if (filters.status && row.status !== filters.status) return false;
      if (filters.lastLogin === 'now' && !row.lastLoginOnline) return false;
      if (filters.search) {
        const q = filters.search.trim().toLowerCase();
        if (!row.name.toLowerCase().includes(q) && !row.email.toLowerCase().includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [filters, preview.users]);

  const totalPages = Math.max(1, preview.totalPages);
  const pageItems = filteredUsers.slice(0, Math.min(pageSize, filteredUsers.length));

  const clearFilters = () => {
    setFilters({
      search: '',
      role: '',
      workspace: '',
      status: '',
      lastLogin: '',
    });
    setPage(1);
  };

  const setRowChecked = (id: string, checked: boolean) => {
    setCheckedIds((prev) => ({ ...prev, [id]: checked }));
  };

  const tabs = ADMIN_TAB_ORDER.map((id) => ({
    id,
    label: t(`tabs.${id}`),
  }));

  return (
    <div className="admin-ws" data-testid="admin-workspace">
      <header className="admin-ws__header">
        <div className="admin-ws__title-block">
          <span className="admin-ws__title-icon" aria-hidden="true">
            <IhIcon name="admin" size={22} />
          </span>
          <div>
            <h1>{t('title')}</h1>
            <p>{t('subtitle')}</p>
          </div>
        </div>
      </header>

      <section className="admin-ws__kpi-row" aria-label={t('kpis.aria')}>
        {preview.kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            className={`admin-ws__kpi${kpi.key === 'openAlerts' ? ' is-alert' : ''}`}
            label={t(`kpis.${kpi.key}`)}
            value={kpi.value}
            hint={t(`kpis.hints.${kpi.hintKey}`)}
            delta={kpi.delta}
            deltaTone={kpi.deltaTone}
            icon={<IhIcon name={ADMIN_KPI_ICONS[kpi.key]} size={18} />}
          />
        ))}
      </section>

      <nav className="screenshot-dashboard__intro-ai admin-ws__ai" aria-label={t('ai.aria')}>
        {ADMIN_AI_ACTIONS.map((action) => (
          <button
            key={action.key}
            type="button"
            className={
              action.key === 'newUser'
                ? 'admin-ws__ai-cta'
                : aiAction === action.key
                  ? 'is-featured'
                  : undefined
            }
            onClick={() => {
              if (action.key === 'auditLog') {
                setActiveTab('auditLog');
              }
              setAiAction(action.key);
            }}
          >
            <span className="admin-ws__ai-icon" aria-hidden="true">
              <IhIcon name={action.icon} size={15} />
            </span>
            <span>{t(`ai.actions.${action.key}`)}</span>
          </button>
        ))}
        <button
          type="button"
          className="screenshot-dashboard__intro-ai-primary"
          onClick={() => onOpenAi?.(t('ai.openPrompt'))}
        >
          <IhIcon name="sparkles" size={15} />
          {t('ai.title')}
        </button>
      </nav>

      <section className="admin-ws__filters" aria-label={t('filters.aria')}>
        <Input
          label={t('filters.search')}
          value={filters.search}
          onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
          placeholder={t('filters.searchPlaceholder')}
        />
        <Select
          label={t('filters.role')}
          value={filters.role}
          onChange={(e) => setFilters((prev) => ({ ...prev, role: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {ADMIN_ROLE_ORDER.map((key) => (
            <option key={key} value={key}>
              {t(`role.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.workspace')}
          value={filters.workspace}
          onChange={(e) => setFilters((prev) => ({ ...prev, workspace: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {ADMIN_WORKSPACE_ORDER.map((key) => (
            <option key={key} value={key}>
              {t(`workspace.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.status')}
          value={filters.status}
          onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {ADMIN_STATUS_ORDER.map((key) => (
            <option key={key} value={key}>
              {t(`status.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.lastLogin')}
          value={filters.lastLogin}
          onChange={(e) => setFilters((prev) => ({ ...prev, lastLogin: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {ADMIN_LAST_LOGIN_ORDER.map((key) => (
            <option key={key} value={key}>
              {t(`lastLogin.${key}`)}
            </option>
          ))}
        </Select>
        <Button variant="secondary" size="sm" onClick={clearFilters}>
          <IhIcon name="refresh" size={13} />
          {t('filters.clear')}
        </Button>
      </section>

      <div className="admin-ws__layout">
        <div className="admin-ws__main">
          <div className="admin-ws__tabs-bar">
            <Tabs
              className="admin-ws__tabs"
              tabs={tabs}
              activeId={activeTab}
              onChange={(id) => setActiveTab(id as AdminTabKey)}
              ariaLabel={t('tabs.aria')}
            />
          </div>

          {activeTab === 'users' ? (
            <>
              <div className="admin-ws__table-wrap" role="region" aria-label={t('table.aria')}>
                <table className="admin-ws__table">
                  <thead>
                    <tr>
                      <th scope="col" className="admin-ws__th-check">
                        <span className="sr-only">{t('table.select')}</span>
                      </th>
                      <th scope="col">{t('table.user')}</th>
                      <th scope="col">{t('table.role')}</th>
                      <th scope="col">{t('table.workspace')}</th>
                      <th scope="col">{t('table.lastLogin')}</th>
                      <th scope="col">{t('table.status')}</th>
                      <th scope="col">{t('table.mfa')}</th>
                      <th scope="col">{t('table.aiUsage')}</th>
                      <th scope="col">{t('table.actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageItems.map((row) => (
                      <UserRow
                        key={row.id}
                        row={row}
                        checked={Boolean(checkedIds[row.id])}
                        onCheckedChange={(checked) => setRowChecked(row.id, checked)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              <footer className="admin-ws__pagination" aria-label={t('pagination.aria')}>
                <p>{t('pagination.total', { count: preview.totalUsers })}</p>
                <div className="admin-ws__page-numbers" role="navigation">
                  {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((n) => (
                    <button
                      key={n}
                      type="button"
                      className={page === n ? 'is-active' : undefined}
                      onClick={() => setPage(n)}
                      aria-current={page === n ? 'page' : undefined}
                    >
                      {n}
                    </button>
                  ))}
                  {totalPages > 6 ? <span className="admin-ws__page-ellipsis">…</span> : null}
                  {totalPages > 5 ? (
                    <button
                      type="button"
                      className={page === totalPages ? 'is-active' : undefined}
                      onClick={() => setPage(totalPages)}
                      aria-current={page === totalPages ? 'page' : undefined}
                    >
                      {totalPages}
                    </button>
                  ) : null}
                </div>
                <label className="ih-field admin-ws__page-size">
                  <span className="ih-field__label">{t('pagination.perPage')}</span>
                  <select
                    className="ih-select"
                    value={String(pageSize)}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setPage(1);
                    }}
                    aria-label={t('pagination.perPage')}
                  >
                    <option value="10">10 / {t('pagination.pageUnit')}</option>
                    <option value="20">20 / {t('pagination.pageUnit')}</option>
                    <option value="40">40 / {t('pagination.pageUnit')}</option>
                  </select>
                </label>
              </footer>
            </>
          ) : null}

          {activeTab === 'roles' ? (
            <div className="admin-ws__table-wrap" role="region" aria-label={t('stub.rolesAria')}>
              <table className="admin-ws__table admin-ws__table--stub">
                <thead>
                  <tr>
                    <th scope="col">{t('table.role')}</th>
                    <th scope="col">{t('stub.usersCol')}</th>
                    <th scope="col">{t('stub.descriptionCol')}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.roles.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <StatusChip
                          tone={ROLE_TONE[row.role]}
                          className={`admin-ws__badge admin-ws__role--${row.role}`}
                        >
                          {t(`role.${row.role}`)}
                        </StatusChip>
                      </td>
                      <td>{row.users}</td>
                      <td>{t(`roleDescriptions.${row.descriptionKey}`)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {activeTab === 'workspacePermissions' ? (
            <div className="admin-ws__table-wrap" role="region" aria-label={t('stub.permissionsAria')}>
              <table className="admin-ws__table admin-ws__table--stub">
                <thead>
                  <tr>
                    <th scope="col">{t('table.workspace')}</th>
                    <th scope="col">{t('table.role')}</th>
                    <th scope="col">{t('stub.accessCol')}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.permissions.map((row) => (
                    <tr key={row.id}>
                      <td>{t(`workspace.${row.workspace}`)}</td>
                      <td>
                        <StatusChip
                          tone={ROLE_TONE[row.role]}
                          className={`admin-ws__badge admin-ws__role--${row.role}`}
                        >
                          {t(`role.${row.role}`)}
                        </StatusChip>
                      </td>
                      <td>{t(`access.${row.accessKey}`)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {activeTab === 'auditLog' ? (
            <div className="admin-ws__table-wrap" role="region" aria-label={t('stub.auditAria')}>
              <table className="admin-ws__table admin-ws__table--stub">
                <thead>
                  <tr>
                    <th scope="col">{t('stub.eventCol')}</th>
                    <th scope="col">{t('stub.actorCol')}</th>
                    <th scope="col">{t('stub.timeCol')}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.auditRows.map((row) => (
                    <tr key={row.id}>
                      <td>{t(`audit.${row.eventKey}`)}</td>
                      <td>{row.actor}</td>
                      <td>{row.timeLabel}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {activeTab === 'services' ? (
            <div className="admin-ws__table-wrap" role="region" aria-label={t('stub.servicesAria')}>
              <table className="admin-ws__table admin-ws__table--stub">
                <thead>
                  <tr>
                    <th scope="col">{t('stub.serviceCol')}</th>
                    <th scope="col">{t('table.status')}</th>
                    <th scope="col">{t('stub.detailCol')}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.services.map((row) => (
                    <tr key={row.id}>
                      <td>{t(`health.${row.service}`)}</td>
                      <td>
                        <StatusChip
                          tone={row.statusKey === 'running' ? 'success' : 'warning'}
                          className="admin-ws__badge"
                        >
                          {t(`healthStatus.${row.statusKey}`)}
                        </StatusChip>
                      </td>
                      <td>{row.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>

        <aside className="admin-ws__rail" aria-label={t('rail.aria')}>
          <section className="admin-ws__rail-card">
            <h3>{t('rail.systemHealth')}</h3>
            <ul className="admin-ws__health">
              {preview.health.map((item) => (
                <li key={item.key}>
                  <span>{t(`health.${item.key}`)}</span>
                  <StatusChip tone="success" className="admin-ws__badge admin-ws__health-chip">
                    {t(`healthStatus.${item.statusKey}`)}
                  </StatusChip>
                </li>
              ))}
            </ul>
          </section>

          <section className="admin-ws__rail-card">
            <h3>{t('rail.recentAudit')}</h3>
            <ul className="admin-ws__audit">
              {preview.recentAudit.map((item) => (
                <li key={item.id}>
                  <span className="admin-ws__audit-dot" aria-hidden="true" />
                  <div>
                    <strong>{t(`audit.${item.eventKey}`)}</strong>
                    <span>{item.actor}</span>
                    <time>{item.timeLabel}</time>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="admin-ws__rail-card">
            <h3>{t('rail.workerStatus')}</h3>
            <ul className="admin-ws__workers">
              {preview.workers.map((worker) => (
                <li key={worker.id}>
                  <span
                    className={`admin-ws__worker-dot is-${worker.statusKey}`}
                    aria-hidden="true"
                  />
                  <div>
                    <strong>{worker.name}</strong>
                    <span>
                      {t(`workerStatus.${worker.statusKey}`)} · {t('rail.heartbeat', { time: worker.heartbeat })}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="admin-ws__rail-card">
            <h3>{t('rail.queueStatus')}</h3>
            <ul className="admin-ws__queues">
              {preview.queues.map((queue) => (
                <li key={queue.key}>
                  <span>{t(`queue.${queue.key}`)}</span>
                  <strong>{queue.pending}</strong>
                </li>
              ))}
            </ul>
          </section>

          <section className="admin-ws__rail-card">
            <h3>{t('rail.apiPerformance')}</h3>
            <ApiSparkline
              points={preview.apiPerformance.points}
              label={t('rail.apiChartAria')}
            />
            <dl className="admin-ws__api-metrics">
              <div>
                <dt>{t('rail.requests24h')}</dt>
                <dd>{preview.apiPerformance.requestsLabel}</dd>
              </div>
              <div>
                <dt>{t('rail.avgResponse')}</dt>
                <dd>{preview.apiPerformance.avgResponse}</dd>
              </div>
              <div>
                <dt>{t('rail.errorRate')}</dt>
                <dd>{preview.apiPerformance.errorRate}</dd>
              </div>
            </dl>
          </section>
        </aside>
      </div>
    </div>
  );
}

function UserRow({
  row,
  checked,
  onCheckedChange,
}: {
  row: AdminUserRow;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  const t = useTranslations('crm.admin');

  return (
    <tr data-testid={`admin-user-row-${row.id}`} tabIndex={0}>
      <td>
        <label className="admin-ws__checkbox">
          <input
            type="checkbox"
            checked={checked}
            aria-label={t('actions.selectUser', { name: row.name })}
            onChange={(e) => onCheckedChange(e.target.checked)}
          />
        </label>
      </td>
      <td>
        <div className="admin-ws__user-cell">
          <UserAvatar initials={row.initials} tone={row.avatarTone} />
          <div className="admin-ws__user-text">
            <strong title={row.name}>{row.name}</strong>
            <span title={row.email}>{row.email}</span>
          </div>
        </div>
      </td>
      <td>
        <StatusChip
          tone={ROLE_TONE[row.role]}
          className={`admin-ws__badge admin-ws__role--${row.role}`}
        >
          {t(`role.${row.role}`)}
        </StatusChip>
      </td>
      <td>
        <span className="admin-ws__workspace">{t(`workspace.${row.workspace}`)}</span>
      </td>
      <td>
        <div className="admin-ws__last-login">
          <strong>{row.lastLoginLabel}</strong>
          {row.lastLoginOnline ? (
            <span className="admin-ws__online">{t('lastLogin.onlineNow')}</span>
          ) : null}
        </div>
      </td>
      <td>
        <StatusChip
          tone={STATUS_TONE[row.status]}
          className={`admin-ws__badge admin-ws__status--${row.status}`}
        >
          {t(`status.${row.status}`)}
        </StatusChip>
      </td>
      <td>
        <span
          className={`admin-ws__mfa ${row.mfaEnabled ? 'is-on' : 'is-off'}`}
          title={row.mfaEnabled ? t('mfa.on') : t('mfa.off')}
        >
          <IhIcon name={row.mfaEnabled ? 'check' : 'alert'} size={13} />
          <span>{row.mfaEnabled ? t('mfa.on') : t('mfa.off')}</span>
        </span>
      </td>
      <td>
        <div className="admin-ws__ai-usage" aria-label={t('table.aiUsage')}>
          <span>
            {row.aiUsedLabel} / {row.aiLimitLabel}
          </span>
          <ProgressBar
            className="admin-ws__progress"
            value={row.aiUsed}
            max={row.aiLimit}
            tone="default"
          />
        </div>
      </td>
      <td>
        <RowActions />
      </td>
    </tr>
  );
}

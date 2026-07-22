'use client';

import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  DESIGN_ASSET_REGISTRY,
  Dialog,
  Drawer,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterButton,
  getCanonicalDesignAssets,
  getDeprecatedCandidateAssets,
  IconButton,
  Input,
  LoadingState,
  MetricCard,
  Pagination,
  PipelineColumn,
  ProgressPair,
  RightRailCard,
  SearchInput,
  SegmentedControl,
  DateRangeControl,
  Select,
  SkeletonState,
  StatusBadge,
  Table,
  TableToolbar,
  Tabs,
  TrendIndicator,
  UnitCard,
  WidgetMenu,
  WidgetShell,
  type DesignAssetStatus,
} from '@investhome/ui';
import type { Route } from 'next';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';
import { useMemo, useState } from 'react';

import {
  AreaChart,
  BarChart,
  LineChart,
  ProgressChart,
  Sparkline,
} from '@/components/design-system/charts';
import {
  AppPage,
  ContentContainer,
  DashboardGrid,
  PageHeader,
  PageSection,
  RightRail,
  WidgetColumn,
} from '@/components/design-system/layout';
import { IhIcon } from '@/components/icons/ih-icons';

import { ComponentDoc } from './component-doc';

const SPACING = [2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64] as const;

const SECTION_IDS = [
  'foundations',
  'colors',
  'typography',
  'spacing',
  'buttons',
  'forms',
  'tables',
  'filters',
  'cards',
  'uxr1-v2',
  'drawers',
  'modals',
  'tabs',
  'navigation',
  'badges',
  'alerts',
  'empty',
  'loading',
  'errors',
  'charts',
  'icons',
  'responsive',
  'a11y',
  'i18n',
  'deprecated',
] as const;

export function DesignSystemShowcase() {
  const t = useTranslations('designSystem');
  const locale = useLocale();
  const [period, setPeriod] = useState<'week' | 'month' | 'quarter'>('month');
  const [range, setRange] = useState({ from: '2026-01-01', to: '2026-07-20' });
  const [filterOn, setFilterOn] = useState(true);
  const [tab, setTab] = useState('overview');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerSize, setDrawerSize] = useState<'sm' | 'md' | 'lg' | 'full'>('md');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const canonicalAssets = useMemo(() => getCanonicalDesignAssets(), []);
  const deprecatedAssets = useMemo(() => getDeprecatedCandidateAssets(), []);

  const statusLabel = (status: DesignAssetStatus) => t(`registryStatus.${status}`);

  const lineData = useMemo(
    () => [
      { label: 'Oca', value: 12 },
      { label: 'Şub', value: 18 },
      { label: 'Mar', value: 15 },
      { label: 'Nis', value: 22 },
      { label: 'May', value: 28 },
      { label: 'Haz', value: 24 },
    ],
    [],
  );

  const barData = useMemo(
    () => [
      { label: 'Yeni', value: 40 },
      { label: 'Nitelikli', value: 28 },
      { label: 'Teklif', value: 16 },
      { label: 'Kazanıldı', value: 9 },
    ],
    [],
  );

  return (
    <ContentContainer>
      <AppPage data-testid="design-system-showcase">
        <PageHeader
          eyebrow={t('eyebrow')}
          title={t('title')}
          subtitle={t('subtitle')}
          actions={
            <>
              <StatusBadge tone="info">{t('demoOnly')}</StatusBadge>
              <Link
                href={'/dashboard/admin/design-system/executive-dashboard' as Route}
                className="ds-type-caption"
                data-testid="ds-exec-prototype-link"
              >
                {t('executivePrototypeLink')}
              </Link>
            </>
          }
        />

        <nav aria-label={t('navLabel')} className="ds-showcase__row" data-testid="ds-section-nav">
          {SECTION_IDS.map((key) => (
            <a key={key} href={`#ds-${key}`} className="ds-type-caption">
              {key === 'uxr1-v2' ? 'UXR1 V2' : t(`g95Sections.${key}`)}
            </a>
          ))}
        </nav>

        <div className="ds-showcase">
          {/* 1 Foundations */}
          <PageSection id="ds-foundations" title={t('g95Sections.foundations')}>
            <p className="ds-type-body">{t('g95.foundationsBody')}</p>
            <div className="ds-showcase__row">
              <StatusBadge tone="success">{t('g95.tokenCanonical')}</StatusBadge>
              <code className="ds-type-caption">@investhome/ui · theme-tokens.css</code>
            </div>
          </PageSection>

          {/* 2 Colors */}
          <PageSection id="ds-colors" title={t('g95Sections.colors')}>
            <div className="ds-showcase__swatches" data-testid="ds-color-swatches">
              {(
                [
                  ['var(--background-canvas)', t('tokenCanvas')],
                  ['var(--background-elevated)', t('tokenElevated')],
                  ['var(--brand-primary)', t('tokenBrand')],
                  ['var(--status-success)', t('tokenSuccess')],
                  ['var(--status-warning)', t('tokenWarning')],
                  ['var(--status-danger)', t('tokenDanger')],
                  ['var(--status-info)', t('tokenInfo')],
                  ['var(--status-ai)', t('tokenAi')],
                  ['var(--chart-series-1)', t('g95.chartSeries')],
                  ['var(--state-disabled-bg)', t('g95.disabled')],
                ] as const
              ).map(([color, label]) => (
                <div key={label} className="ds-showcase__swatch">
                  <div className="ds-showcase__swatch-chip" style={{ background: color }} />
                  <div className="ds-showcase__swatch-meta">{label}</div>
                </div>
              ))}
            </div>
            <p className="ds-type-caption">{t('g95.colorRules')}</p>
          </PageSection>

          {/* 3 Typography */}
          <PageSection id="ds-typography" title={t('g95Sections.typography')}>
            <div className="ds-showcase__stack">
              <p className="ds-type-display">Display — Yatırım özeti</p>
              <p className="ds-type-page-title">Page title</p>
              <p className="ds-type-section-title">Section title</p>
              <p className="ds-type-card-title">Card title</p>
              <p className="ds-type-body">Body — calm professional default for INVESTHOME OS.</p>
              <p className="ds-type-body-small">Body small / table text</p>
              <p className="ds-type-label">Label</p>
              <p className="ds-type-caption">Caption</p>
              <p className="ds-type-metric-large">12.4M</p>
              <p className="ds-type-metric-medium">842</p>
            </div>
          </PageSection>

          {/* 4 Spacing (+ radius/shadows) */}
          <PageSection id="ds-spacing" title={t('g95Sections.spacing')}>
            <div className="ds-space-demo">
              {SPACING.map((n) => (
                <div key={n} className="ds-space-demo__item">
                  <div className="ds-space-demo__box" style={{ width: n, height: n }} />
                  {n}px
                </div>
              ))}
            </div>
            <div className="ds-radius-demo" style={{ marginTop: 16 }}>
              {(
                [
                  ['var(--radius-small)', 'small'],
                  ['var(--radius-medium)', 'medium'],
                  ['var(--radius-large)', 'large'],
                  ['var(--radius-full)', 'full'],
                ] as const
              ).map(([radius, label]) => (
                <div key={label} className="ds-radius-demo__item" style={{ borderRadius: radius }}>
                  {label}
                </div>
              ))}
            </div>
            <div className="ds-shadow-demo" style={{ marginTop: 16 }}>
              {(
                [
                  ['var(--shadow-none)', 'none'],
                  ['var(--shadow-subtle)', 'subtle'],
                  ['var(--shadow-medium)', 'medium'],
                  ['var(--shadow-elevated)', 'elevated'],
                ] as const
              ).map(([shadow, label]) => (
                <div key={label} className="ds-shadow-demo__item" style={{ boxShadow: shadow }}>
                  {label}
                </div>
              ))}
            </div>
          </PageSection>

          {/* 5 Buttons */}
          <PageSection id="ds-buttons" title={t('g95Sections.buttons')}>
            <ComponentDoc
              name="Button"
              importPath="@investhome/ui"
              props="variant · size · loading · success · disabled"
              usage={t('g95.buttonUsage')}
              doExample={t('g95.buttonDo')}
              dontExample={t('g95.buttonDont')}
              migrationStatus={t('g95.statusCanonical')}
            >
              <div className="ds-showcase__row">
                <Button variant="primary">Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="tertiary">Tertiary</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="danger">Destructive</Button>
                <Button variant="link">Link</Button>
                <Button size="sm">Small</Button>
                <Button size="lg">Large</Button>
                <Button loading>Loading</Button>
                <Button disabled>Disabled</Button>
                <IconButton label={t('g95.iconButtonLabel')}>
                  <IhIcon name="settings" size="sm" />
                </IconButton>
              </div>
            </ComponentDoc>
          </PageSection>

          {/* 6 Forms */}
          <PageSection id="ds-forms" title={t('g95Sections.forms')}>
            <ComponentDoc
              name="Input / Select / SearchInput / DateRangeControl"
              importPath="@investhome/ui"
              props="label · disabled · placeholder"
              usage={t('g95.formUsage')}
              doExample={t('g95.formDo')}
              dontExample={t('g95.formDont')}
              migrationStatus={t('g95.statusCanonical')}
            >
              <div className="ds-showcase__row">
                <Input label={t('g95.inputLabel')} placeholder="…" />
                <Select label={t('g95.selectLabel')} defaultValue="a">
                  <option value="a">A</option>
                  <option value="b">B</option>
                </Select>
                <SearchInput
                  label={t('g95.searchLabel')}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onClear={() => setSearch('')}
                  clearLabel={t('g95.clear')}
                />
                <DateRangeControl
                  value={range}
                  onChange={setRange}
                  fromLabel={t('from')}
                  toLabel={t('to')}
                />
              </div>
            </ComponentDoc>
          </PageSection>

          {/* 7 Tables */}
          <PageSection id="ds-tables" title={t('g95Sections.tables')}>
            <ComponentDoc
              name="Table + TableToolbar + Pagination"
              importPath="@investhome/ui"
              usage={t('g95.tableUsage')}
              doExample={t('g95.tableDo')}
              dontExample={t('g95.tableDont')}
              migrationStatus={t('g95.statusCanonical')}
            >
              <TableToolbar actions={<Button size="sm" variant="secondary">{t('g95.export')}</Button>}>
                <SearchInput
                  aria-label={t('g95.searchLabel')}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={t('g95.searchLabel')}
                />
              </TableToolbar>
              <Table>
                <thead>
                  <tr>
                    <th scope="col">{t('g95.colName')}</th>
                    <th scope="col">{t('g95.colStatus')}</th>
                    <th scope="col">{t('g95.colAmount')}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Acme Yatırım</td>
                    <td>
                      <StatusBadge tone="success">{t('g95.statusActive')}</StatusBadge>
                    </td>
                    <td style={{ textAlign: 'right' }}>₺1.240.000</td>
                  </tr>
                  <tr>
                    <td>Delta Proje</td>
                    <td>
                      <StatusBadge tone="warning">{t('g95.statusPending')}</StatusBadge>
                    </td>
                    <td style={{ textAlign: 'right' }}>₺420.000</td>
                  </tr>
                </tbody>
              </Table>
              <Pagination
                page={page}
                pageSize={10}
                total={24}
                onPrevious={() => setPage((p) => Math.max(1, p - 1))}
                onNext={() => setPage((p) => p + 1)}
                previousLabel={t('g95.prev')}
                nextLabel={t('g95.next')}
              />
            </ComponentDoc>
          </PageSection>

          {/* 8 Filters */}
          <PageSection id="ds-filters" title={t('g95Sections.filters')}>
            <ComponentDoc
              name="FilterBar / FilterButton"
              importPath="@investhome/ui"
              usage={t('g95.filterUsage')}
              doExample={t('g95.filterDo')}
              dontExample={t('g95.filterDont')}
              migrationStatus={t('g95.statusCanonical')}
            >
              <FilterBar
                actions={
                  <Button size="sm" variant="ghost" onClick={() => setFilterOn(false)}>
                    {t('g95.clearAll')}
                  </Button>
                }
              >
                <FilterButton active={filterOn} count={2} onClick={() => setFilterOn((v) => !v)}>
                  {t('filterActive')}
                </FilterButton>
                <Select aria-label={t('g95.stage')} defaultValue="all">
                  <option value="all">{t('g95.allStages')}</option>
                  <option value="qualified">Qualified</option>
                </Select>
                <SegmentedControl
                  ariaLabel={t('segmentLabel')}
                  value={period}
                  onChange={setPeriod}
                  options={[
                    { value: 'week', label: t('segmentWeek') },
                    { value: 'month', label: t('segmentMonth') },
                    { value: 'quarter', label: t('segmentQuarter') },
                  ]}
                />
              </FilterBar>
            </ComponentDoc>
          </PageSection>

          {/* 9 Cards */}
          <PageSection id="ds-cards" title={t('g95Sections.cards')}>
            <DashboardGrid>
              <WidgetColumn span={4}>
                <ComponentDoc
                  name="MetricCard"
                  importPath="@investhome/ui"
                  migrationStatus={t('g95.statusCanonical')}
                  doExample={t('g95.cardDo')}
                  dontExample={t('g95.cardDont')}
                >
                  <MetricCard
                    label={t('metricPipeline')}
                    value="128"
                    trend="up"
                    trendLabel={t('metricTrendUp')}
                    icon={<IhIcon name="trendingUp" size="sm" />}
                  />
                </ComponentDoc>
              </WidgetColumn>
              <WidgetColumn span={4}>
                <Card>
                  <CardHeader title={t('g95.summaryCard')} description={t('g95.summaryCardDesc')} />
                  <CardContent>
                    <p className="ds-type-body-small">{t('g95.cardBody')}</p>
                  </CardContent>
                  <CardFooter>
                    <Button size="sm" variant="secondary">
                      {t('menuRefresh')}
                    </Button>
                  </CardFooter>
                </Card>
              </WidgetColumn>
              <WidgetColumn span={4}>
                <WidgetShell title={t('widgetSales')} description={t('widgetSalesDesc')} span={4}>
                  <Sparkline values={[4, 6, 5, 9, 8, 12]} ariaLabel={t('chartSparkline')} locale={locale} />
                </WidgetShell>
              </WidgetColumn>
            </DashboardGrid>
          </PageSection>

          {/* UXR1 V2 primitives (additive showcase — opt-in theme) */}
          <PageSection id="ds-uxr1-v2" title="UXR1 V2 primitives">
            <p className="ds-type-body-small" style={{ marginBottom: 16 }}>
              White / navy / blue / gray card system. Opt-in via <code>data-ds-version=&quot;v2&quot;</code>.
              Production workspace migration is Phase 2 — this section is foundation only.
            </p>
            <div data-ds-version="v2">
              <DashboardGrid>
                <WidgetColumn span={3}>
                  <UnitCard
                    unitCode="A-1204"
                    beds={2}
                    baths={2}
                    sqft="1,140"
                    price="$428,000"
                    estimatedRent="$2,150"
                    badges={[{ label: '-4%', tone: 'discount' }]}
                  />
                </WidgetColumn>
                <WidgetColumn span={5}>
                  <div style={{ display: 'flex', gap: 12, overflow: 'auto' }}>
                    <PipelineColumn title="Lead" count={2} tone="lead">
                      <Card title="Ada Yılmaz">Proposal · $428k</Card>
                    </PipelineColumn>
                    <PipelineColumn title="Qualify" count={1} tone="qualify">
                      <Card title="Nova LLC">Site visit</Card>
                    </PipelineColumn>
                  </div>
                </WidgetColumn>
                <WidgetColumn span={4}>
                  <Card>
                    <CardHeader title="Project progress" description="Construction + Sales" />
                    <CardContent>
                      <ProgressPair
                        construction={{ label: 'Construction', value: 72 }}
                        sales={{ label: 'Sales', value: 58, tone: 'success' }}
                      />
                    </CardContent>
                  </Card>
                </WidgetColumn>
              </DashboardGrid>
            </div>
          </PageSection>

          {/* 10 Drawers */}
          <PageSection id="ds-drawers" title={t('g95Sections.drawers')}>
            <ComponentDoc
              name="Drawer"
              importPath="@investhome/ui"
              props="open · onClose · title · subtitle · size · footer"
              usage={t('g95.drawerUsage')}
              doExample={t('g95.drawerDo')}
              dontExample={t('g95.drawerDont')}
              migrationStatus={t('g95.statusCanonical')}
            >
              <div className="ds-showcase__row">
                {(['sm', 'md', 'lg', 'full'] as const).map((s) => (
                  <Button
                    key={s}
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setDrawerSize(s);
                      setDrawerOpen(true);
                    }}
                  >
                    {t('g95.openDrawer')} ({s})
                  </Button>
                ))}
              </div>
              <Drawer
                open={drawerOpen}
                onClose={() => setDrawerOpen(false)}
                title={t('g95.drawerTitle')}
                subtitle={t('g95.drawerSubtitle')}
                size={drawerSize}
                footer={
                  <Button size="sm" onClick={() => setDrawerOpen(false)}>
                    {t('g95.close')}
                  </Button>
                }
              >
                <p className="ds-type-body-small">{t('g95.drawerBody')}</p>
              </Drawer>
            </ComponentDoc>
          </PageSection>

          {/* 11 Modals */}
          <PageSection id="ds-modals" title={t('g95Sections.modals')}>
            <ComponentDoc
              name="Dialog"
              importPath="@investhome/ui"
              props="open · onClose · title · footer"
              usage={t('g95.modalUsage')}
              doExample={t('g95.modalDo')}
              dontExample={t('g95.modalDont')}
              migrationStatus={t('g95.statusCanonical')}
            >
              <Button variant="secondary" onClick={() => setDialogOpen(true)}>
                {t('g95.openModal')}
              </Button>
              <Dialog
                open={dialogOpen}
                onClose={() => setDialogOpen(false)}
                title={t('g95.modalTitle')}
                footer={
                  <>
                    <Button variant="ghost" size="sm" onClick={() => setDialogOpen(false)}>
                      {t('g95.cancel')}
                    </Button>
                    <Button size="sm" onClick={() => setDialogOpen(false)}>
                      {t('g95.confirm')}
                    </Button>
                  </>
                }
              >
                <p className="ds-type-body-small">{t('g95.modalBody')}</p>
              </Dialog>
            </ComponentDoc>
          </PageSection>

          {/* 12 Tabs */}
          <PageSection id="ds-tabs" title={t('g95Sections.tabs')}>
            <div className="ds-showcase__stack">
              <Tabs
                tabs={[
                  { id: 'overview', label: t('g95.tabOverview') },
                  { id: 'detail', label: t('g95.tabDetail') },
                ]}
                activeId={tab}
                onChange={setTab}
              />
              <SegmentedControl
                ariaLabel={t('segmentLabel')}
                value={period}
                onChange={setPeriod}
                options={[
                  { value: 'week', label: t('segmentWeek') },
                  { value: 'month', label: t('segmentMonth') },
                  { value: 'quarter', label: t('segmentQuarter') },
                ]}
              />
            </div>
          </PageSection>

          {/* 13 Navigation */}
          <PageSection id="ds-navigation" title={t('g95Sections.navigation')}>
            <p className="ds-type-body">{t('g95.navBody')}</p>
            <div className="ds-showcase__row">
              <Link href={'/dashboard/executive' as Route} className="ds-type-caption">
                Executive
              </Link>
              <Link href={'/workspaces/crm/leads' as Route} className="ds-type-caption">
                CRM
              </Link>
              <Link href={'/dashboard/admin' as Route} className="ds-type-caption">
                Admin
              </Link>
              <WidgetMenu
                triggerLabel={t('menuOpen')}
                items={[
                  { id: 'export', label: t('menuExport'), onSelect: () => undefined },
                  { id: 'refresh', label: t('menuRefresh'), onSelect: () => undefined },
                ]}
              />
            </div>
          </PageSection>

          {/* 14 Badges */}
          <PageSection id="ds-badges" title={t('g95Sections.badges')}>
            <div className="ds-showcase__row">
              <StatusBadge tone="neutral">Neutral</StatusBadge>
              <StatusBadge tone="info">Info</StatusBadge>
              <StatusBadge tone="success">Success</StatusBadge>
              <StatusBadge tone="warning">Warning</StatusBadge>
              <StatusBadge tone="danger">Danger</StatusBadge>
              <StatusBadge tone="ai">AI</StatusBadge>
              <Badge tone="success">Badge</Badge>
              <TrendIndicator direction="up" label={t('metricTrendUp')} />
              <TrendIndicator direction="down" label="-3.1%" />
            </div>
            <p className="ds-type-caption">{t('g95.badgeRules')}</p>
          </PageSection>

          {/* 15 Alerts */}
          <PageSection id="ds-alerts" title={t('g95Sections.alerts')}>
            <div className="ds-showcase__stack">
              <Alert tone="info">{t('g95.alertInfo')}</Alert>
              <Alert tone="success">{t('g95.alertSuccess')}</Alert>
              <Alert tone="warning">{t('g95.alertWarning')}</Alert>
              <Alert tone="error" role="alert">
                {t('g95.alertError')}
              </Alert>
            </div>
          </PageSection>

          {/* 16 Empty */}
          <PageSection id="ds-empty" title={t('g95Sections.empty')}>
            <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} compact />
          </PageSection>

          {/* 17 Loading */}
          <PageSection id="ds-loading" title={t('g95Sections.loading')}>
            <DashboardGrid>
              <WidgetColumn span={4}>
                <LoadingState label={t('loadingLabel')} />
              </WidgetColumn>
              <WidgetColumn span={4}>
                <SkeletonState label={t('loadingLabel')} lines={3} />
              </WidgetColumn>
              <WidgetColumn span={4}>
                <MetricCard label={t('metricLoading')} loading />
              </WidgetColumn>
            </DashboardGrid>
          </PageSection>

          {/* 18 Errors */}
          <PageSection id="ds-errors" title={t('g95Sections.errors')}>
            <DashboardGrid>
              <WidgetColumn span={6}>
                <ErrorState
                  message={t('errorMessage')}
                  action={<Button size="sm">{t('retry')}</Button>}
                  compact
                />
              </WidgetColumn>
              <WidgetColumn span={6}>
                <MetricCard label={t('metricError')} error errorLabel={t('metricError')} />
              </WidgetColumn>
            </DashboardGrid>
          </PageSection>

          {/* 19 Charts */}
          <PageSection id="ds-charts" title={t('g95Sections.charts')}>
            <p className="ds-type-caption">{t('g95.chartRules')}</p>
            <DashboardGrid>
              <WidgetColumn span={6}>
                <LineChart data={lineData} ariaLabel={t('chartLine')} locale={locale} title={t('chartLine')} />
              </WidgetColumn>
              <WidgetColumn span={6}>
                <AreaChart
                  data={lineData}
                  ariaLabel={t('chartArea')}
                  locale={locale}
                  format="currency"
                  title={t('chartArea')}
                />
              </WidgetColumn>
              <WidgetColumn span={6}>
                <BarChart data={barData} ariaLabel={t('chartBar')} locale={locale} title={t('chartBar')} />
              </WidgetColumn>
              <WidgetColumn span={3}>
                <ProgressChart value={72} ariaLabel={t('chartProgress')} locale={locale} title={t('chartProgress')} />
              </WidgetColumn>
              <WidgetColumn span={3}>
                <Sparkline values={[4, 6, 5, 9, 8, 12]} ariaLabel={t('chartSparkline')} locale={locale} />
              </WidgetColumn>
            </DashboardGrid>
          </PageSection>

          {/* 20 Icons */}
          <PageSection id="ds-icons" title={t('g95Sections.icons')}>
            <div className="ds-showcase__row">
              {([12, 14, 16, 18, 20, 24] as const).map((size) => (
                <span key={size} className="ds-showcase__stack" style={{ alignItems: 'center' }}>
                  <IhIcon name="home" size={size} />
                  <span className="ds-type-caption">{size}</span>
                </span>
              ))}
            </div>
            <p className="ds-type-caption">{t('g95.iconRules')}</p>
          </PageSection>

          {/* 21 Responsive */}
          <PageSection id="ds-responsive" title={t('g95Sections.responsive')}>
            <p className="ds-type-body">{t('responsiveNote')}</p>
            <p className="ds-type-caption">{t('g95.responsiveBreakpoints')}</p>
            <DashboardGrid data-testid="ds-responsive-grid">
              <WidgetColumn span={4}>
                <MetricCard label="1920" value="Desktop" size="medium" />
              </WidgetColumn>
              <WidgetColumn span={4}>
                <MetricCard label="1280" value="Laptop" size="medium" />
              </WidgetColumn>
              <WidgetColumn span={4}>
                <MetricCard label="768" value="Tablet" size="medium" />
              </WidgetColumn>
            </DashboardGrid>
          </PageSection>

          {/* 22 Accessibility */}
          <PageSection id="ds-a11y" title={t('g95Sections.a11y')}>
            <p className="ds-type-body">{t('g95.a11yBody')}</p>
            <ul className="ds-showcase__stack">
              <li className="ds-type-body-small">{t('g95.a11yFocus')}</li>
              <li className="ds-type-body-small">{t('g95.a11yKeyboard')}</li>
              <li className="ds-type-body-small">{t('g95.a11yContrast')}</li>
              <li className="ds-type-body-small">{t('g95.a11yStatus')}</li>
            </ul>
          </PageSection>

          {/* 23 Localization */}
          <PageSection id="ds-i18n" title={t('g95Sections.i18n')}>
            <p className="ds-type-body">{t('g95.i18nBody')}</p>
            <StatusBadge tone="info">{locale.toUpperCase()}</StatusBadge>
          </PageSection>

          {/* 24 Deprecated */}
          <PageSection id="ds-deprecated" title={t('g95Sections.deprecated')}>
            <p className="ds-registry-note" data-testid="ds-registry-intro">
              {t('registryIntro')}
            </p>
            <p className="ds-registry-note">
              {t('registryCount', {
                total: DESIGN_ASSET_REGISTRY.length,
                canonical: canonicalAssets.length,
              })}
            </p>
            <div className="ih-table-wrap admin-table-wrap">
              <table className="ds-registry-table ih-table--density-compact" data-testid="ds-registry-table">
                <thead>
                  <tr>
                    <th scope="col">{t('registryColComponent')}</th>
                    <th scope="col">{t('registryColFigma')}</th>
                    <th scope="col">{t('registryColCategory')}</th>
                    <th scope="col">{t('registryColStatus')}</th>
                  </tr>
                </thead>
                <tbody>
                  {canonicalAssets.slice(0, 12).map((asset) => (
                    <tr key={asset.id} data-registry-id={asset.id}>
                      <td>{asset.codeName}</td>
                      <td className="ds-registry-table__figma">{asset.figmaName}</td>
                      <td>{asset.category}</td>
                      <td>
                        <StatusBadge tone="info">{statusLabel(asset.status)}</StatusBadge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {deprecatedAssets.length > 0 ? (
              <>
                <h3 className="ds-type-section-title" style={{ marginTop: 24 }}>
                  {t('registryDeprecatedTitle')}
                </h3>
                <div className="ih-table-wrap admin-table-wrap">
                  <table
                    className="ds-registry-table ih-table--density-compact"
                    data-testid="ds-registry-deprecated"
                  >
                    <thead>
                      <tr>
                        <th scope="col">{t('registryColComponent')}</th>
                        <th scope="col">{t('registryColFigma')}</th>
                        <th scope="col">{t('registryColStatus')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {deprecatedAssets.map((asset) => (
                        <tr key={asset.id} data-registry-id={asset.id}>
                          <td>{asset.codeName}</td>
                          <td className="ds-registry-table__figma">{asset.figmaName}</td>
                          <td>
                            <StatusBadge tone="warning">{statusLabel(asset.status)}</StatusBadge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : null}
            <p className="ds-type-caption" style={{ marginTop: 16 }}>
              {t('g95.deprecationDoc')}
            </p>
            <DashboardGrid style={{ marginTop: 16 }}>
              <WidgetColumn span={8}>
                <RightRailCard title={t('railInsights')}>
                  <p>{t('railInsightsBody')}</p>
                </RightRailCard>
              </WidgetColumn>
              <RightRail>
                <RightRailCard title={t('railActions')}>
                  <p>{t('railActionsBody')}</p>
                </RightRailCard>
              </RightRail>
            </DashboardGrid>
          </PageSection>
        </div>
      </AppPage>
    </ContentContainer>
  );
}

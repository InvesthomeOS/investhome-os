import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type CampaignStatus = 'draft' | 'ready' | 'exported' | 'archived';

export type LeftSectionKey =
  | 'brief'
  | 'sources'
  | 'brand'
  | 'financial'
  | 'advanced';

/** Left Focus rail panels — each id maps to a unique drawer. */
export type PrbLeftRailId =
  | 'content'
  | 'pages'
  | 'design'
  | 'components'
  | 'data'
  | 'media'
  | 'brand'
  | 'settings';

/** Right Focus rail panels — each id maps to a unique drawer. */
export type PrbRightRailId =
  | 'page'
  | 'score'
  | 'suggestions'
  | 'signature'
  | 'export'
  | 'history';

export type PageOrientation = 'portrait' | 'landscape';

export type PageMargins = {
  top: number;
  bottom: number;
  left: number;
  right: number;
  linked: boolean;
};

export type DevicePreview = 'desktop' | 'mobile';

export type BottomActionKey =
  | 'addSection'
  | 'text'
  | 'table'
  | 'chart'
  | 'image'
  | 'icon'
  | 'schedule'
  | 'other';

export type FloatingActionKey = 'edit' | 'duplicate' | 'delete' | 'pageSettings';

export type ProposalType =
  | 'investor'
  | 'project'
  | 'partnership'
  | 'broker'
  | 'bankFinancing'
  | 'corporate'
  | 'sales'
  | 'construction'
  | 'propertyAcquisition'
  | 'jointVenture'
  | 'custom';

export type DeliveryFormat = 'pdf' | 'pptx' | 'web';

export type DocumentRatio = 'a4' | 'letter';

export type ViewMode = 'document' | 'outline';

export type PreviewFitMode = 'fit' | 'fill' | 'actual';

export type AiStatusKey =
  | 'idle'
  | 'thinking'
  | 'readingBrief'
  | 'gatheringSources'
  | 'buildingStructure'
  | 'writingContent'
  | 'buildingFinancials'
  | 'optimizing'
  | 'completed';

export type AiProgressStepKey =
  | 'readingBrief'
  | 'gatheringSources'
  | 'buildingStructure'
  | 'writingContent'
  | 'buildingFinancials'
  | 'scoringQuality'
  | 'readyToExport';

export type SuggestionKey =
  | 'strengthenCover'
  | 'expandFinancials'
  | 'clarifyRisk'
  | 'improveCta'
  | 'addComparables'
  | 'shortenTerms'
  | 'addCashFlow';

export type QuickActionKey =
  | 'financialTable'
  | 'roiChart'
  | 'projectImages'
  | 'timeline'
  | 'comparison'
  | 'faq'
  | 'marketMap'
  | 'risk'
  | 'signature'
  | 'paymentSchedule'
  | 'qrVideo'
  | 'rewriteAll'
  | 'shorten'
  | 'expand';

export type ToolbarActionKey =
  | 'addPage'
  | 'edit'
  | 'rewrite'
  | 'replaceImage'
  | 'changeStyle'
  | 'duplicate'
  | 'delete';

export type ExportOptionKey =
  | 'webShare'
  | 'secureLink'
  | 'password'
  | 'expiry'
  | 'tracking'
  | 'pdf'
  | 'hiresPdf'
  | 'printReady'
  | 'pptx'
  | 'slides'
  | 'docx';

export type PageKind =
  | 'cover'
  | 'toc'
  | 'execSummary'
  | 'projectOverview'
  | 'market'
  | 'location'
  | 'investmentOpportunity'
  | 'investmentStructure'
  | 'financialSummary'
  | 'roiIrr'
  | 'cashFlow'
  | 'sourcesUses'
  | 'paymentSchedule'
  | 'risk'
  | 'timeline'
  | 'exit'
  | 'whyUs'
  | 'terms'
  | 'cta'
  | 'contact'
  | 'attachments'
  | 'bankTerms'
  | 'collateral'
  | 'repayment';

export type BrandKitKey = 'logo' | 'primaryColors' | 'typography' | 'documentMaster' | 'watermark';

export type ScoreFactorKey =
  | 'structure'
  | 'clarity'
  | 'persuasiveness'
  | 'financialCompleteness'
  | 'brand'
  | 'cta'
  | 'risk'
  | 'readability';

export type ScoreFactorTone = 'good' | 'warn';

export type AiSourceKey =
  | 'crm'
  | 'projects'
  | 'investors'
  | 'companies'
  | 'documents'
  | 'media'
  | 'imageBuilder'
  | 'videoBuilder'
  | 'presentationBuilder'
  | 'websiteBuilder'
  | 'brandKit'
  | 'floorPlans'
  | 'financialData'
  | 'constructionProgress'
  | 'maps'
  | 'projectImages'
  | 'brochures'
  | 'templates';

export type MergeFieldKey =
  | 'recipient'
  | 'company'
  | 'investorType'
  | 'amount'
  | 'country'
  | 'project'
  | 'meetingLink'
  | 'advisor'
  | 'expiration';

export type SignatureState =
  | 'draft'
  | 'sent'
  | 'viewed'
  | 'accepted'
  | 'rejected'
  | 'revisionRequested'
  | 'expired';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type ProposalBrief = {
  proposalType: ProposalType;
  audience: string;
  language: string;
  style: string;
  goal: string;
  cta: string;
  topic: string;
  deliveryFormat: DeliveryFormat;
  deadline: string;
  validity: string;
};

export type FinancialSettings = {
  currency: string;
  amount: string;
  roi: string;
  irr: string;
  cashFlow: string;
  paymentSchedule: string;
  scenario: string;
};

export type ProposalScores = {
  overall: number;
};

export type PrbPage = {
  id: string;
  kind: PageKind;
  thumbUrl: string;
  status: 'ready' | 'draft' | 'review';
  titleOverride?: string;
};

export type PrbProject = {
  id: ProjectId;
  name: string;
  campaignName: string;
  featuredLabel: string;
  coverUrl: string;
};

export const PRB_HOME = '/workspaces/creative-studio';
export const PRB_ROUTE = '/workspaces/creative-studio/proposal-builder';

export const CAMPAIGN_STATUS_TONE: Record<CampaignStatus, StatusChipTone> = {
  draft: 'default',
  ready: 'success',
  exported: 'info',
  archived: 'warning',
};

export const WORKFLOW_STEPS = ['brief', 'content', 'design', 'review', 'preview'] as const;

export const LEFT_SECTIONS: LeftSectionKey[] = [
  'brief',
  'sources',
  'brand',
  'financial',
  'advanced',
];

export const PRB_LEFT_RAIL_IDS: PrbLeftRailId[] = [
  'content',
  'pages',
  'design',
  'components',
  'data',
  'media',
  'brand',
  'settings',
];

export const PRB_LEFT_RAIL_ICONS: Record<PrbLeftRailId, IhIconName> = {
  content: 'documents',
  pages: 'executive',
  design: 'design',
  components: 'inventory',
  data: 'finance',
  media: 'theme',
  brand: 'sparkles',
  settings: 'settings',
};

export const PRB_RIGHT_RAIL_IDS: PrbRightRailId[] = [
  'page',
  'score',
  'suggestions',
  'signature',
  'export',
  'history',
];

export const PRB_RIGHT_RAIL_ICONS: Record<PrbRightRailId, IhIconName> = {
  page: 'marketing',
  score: 'trendingUp',
  suggestions: 'target',
  signature: 'check',
  export: 'inbox',
  history: 'clock',
};

export const BOTTOM_ACTIONS: { key: BottomActionKey; icon: IhIconName }[] = [
  { key: 'addSection', icon: 'plus' },
  { key: 'text', icon: 'documents' },
  { key: 'table', icon: 'projects' },
  { key: 'chart', icon: 'barChart' },
  { key: 'image', icon: 'inventory' },
  { key: 'icon', icon: 'activity' },
  { key: 'schedule', icon: 'calendar' },
  { key: 'other', icon: 'quickAction' },
];

export const CONTENT_SECTION_SUGGESTIONS: {
  kind: PageKind;
  icon: IhIconName;
}[] = [
  { kind: 'cover', icon: 'documents' },
  { kind: 'execSummary', icon: 'sparkles' },
  { kind: 'projectOverview', icon: 'projects' },
  { kind: 'investmentOpportunity', icon: 'trendingUp' },
  { kind: 'financialSummary', icon: 'barChart' },
  { kind: 'risk', icon: 'alert' },
  { kind: 'timeline', icon: 'clock' },
  { kind: 'cta', icon: 'target' },
];

export const COMPONENT_LIBRARY: { key: string; icon: IhIconName }[] = [
  { key: 'heading', icon: 'documents' },
  { key: 'paragraph', icon: 'marketing' },
  { key: 'metricRow', icon: 'trendingUp' },
  { key: 'dataTable', icon: 'executive' },
  { key: 'chartBlock', icon: 'barChart' },
  { key: 'imageBlock', icon: 'inventory' },
  { key: 'quote', icon: 'sparkles' },
  { key: 'ctaBlock', icon: 'target' },
];

export const DEFAULT_MARGINS: PageMargins = {
  top: 20,
  bottom: 20,
  left: 20,
  right: 20,
  linked: true,
};

export const HISTORY_ITEMS = [
  { id: 'v3', labelKey: 'current', time: '2m' },
  { id: 'v2', labelKey: 'aiPass', time: '18m' },
  { id: 'v1', labelKey: 'briefLocked', time: '1h' },
] as const;

export const PRB_ZOOM_PRESETS = [25, 50, 75, 100, 125, 150, 200] as const;

export const PROPOSAL_TYPES: { key: ProposalType; icon: IhIconName }[] = [
  { key: 'investor', icon: 'trendingUp' },
  { key: 'project', icon: 'projects' },
  { key: 'partnership', icon: 'users' },
  { key: 'broker', icon: 'users' },
  { key: 'bankFinancing', icon: 'documents' },
  { key: 'corporate', icon: 'users' },
];

export const PROPOSAL_TYPES_MORE: { key: ProposalType; icon: IhIconName }[] = [
  { key: 'sales', icon: 'target' },
  { key: 'construction', icon: 'activity' },
  { key: 'propertyAcquisition', icon: 'projects' },
  { key: 'jointVenture', icon: 'users' },
  { key: 'custom', icon: 'sparkles' },
];

export const DELIVERY_FORMATS: DeliveryFormat[] = ['pdf', 'pptx', 'web'];

export const DOCUMENT_RATIOS: DocumentRatio[] = ['a4', 'letter'];

export const AI_STATUS_SEQUENCE: AiStatusKey[] = [
  'thinking',
  'readingBrief',
  'gatheringSources',
  'buildingStructure',
  'writingContent',
  'buildingFinancials',
  'optimizing',
  'completed',
];

export const AI_PROGRESS_STEPS: AiProgressStepKey[] = [
  'readingBrief',
  'gatheringSources',
  'buildingStructure',
  'writingContent',
  'buildingFinancials',
  'scoringQuality',
  'readyToExport',
];

export const AI_SUGGESTIONS: SuggestionKey[] = [
  'strengthenCover',
  'expandFinancials',
  'clarifyRisk',
  'improveCta',
  'addCashFlow',
];

export const QUICK_ACTIONS: { key: QuickActionKey; icon: IhIconName }[] = [
  { key: 'financialTable', icon: 'barChart' },
  { key: 'roiChart', icon: 'trendingUp' },
  { key: 'projectImages', icon: 'inventory' },
  { key: 'timeline', icon: 'clock' },
  { key: 'comparison', icon: 'activity' },
  { key: 'faq', icon: 'documents' },
  { key: 'marketMap', icon: 'projects' },
  { key: 'risk', icon: 'alert' },
  { key: 'signature', icon: 'check' },
  { key: 'paymentSchedule', icon: 'calendar' },
  { key: 'qrVideo', icon: 'meeting' },
  { key: 'rewriteAll', icon: 'refresh' },
  { key: 'shorten', icon: 'activity' },
  { key: 'expand', icon: 'documents' },
];

export const TOOLBAR_ACTIONS: { key: ToolbarActionKey; icon: IhIconName }[] = [
  { key: 'addPage', icon: 'sparkles' },
  { key: 'edit', icon: 'design' },
  { key: 'rewrite', icon: 'refresh' },
  { key: 'replaceImage', icon: 'inventory' },
  { key: 'changeStyle', icon: 'theme' },
  { key: 'duplicate', icon: 'documents' },
  { key: 'delete', icon: 'alert' },
];

export const DIGITAL_EXPORTS: ExportOptionKey[] = [
  'webShare',
  'secureLink',
  'password',
  'expiry',
  'tracking',
];

export const DOCUMENT_EXPORTS: ExportOptionKey[] = [
  'pdf',
  'hiresPdf',
  'printReady',
  'pptx',
  'slides',
  'docx',
];

export const PREVIEW_FIT_MODES: PreviewFitMode[] = ['fit', 'fill', 'actual'];

export const AI_SOURCES: AiSourceKey[] = [
  'crm',
  'projects',
  'investors',
  'companies',
  'documents',
  'media',
  'imageBuilder',
  'videoBuilder',
  'presentationBuilder',
  'websiteBuilder',
  'brandKit',
  'floorPlans',
  'financialData',
  'constructionProgress',
  'maps',
  'projectImages',
  'brochures',
  'templates',
];

export const BRAND_KIT: BrandKitKey[] = [
  'logo',
  'primaryColors',
  'typography',
  'documentMaster',
  'watermark',
];

export const SCORE_FACTORS: { key: ScoreFactorKey; tone: ScoreFactorTone }[] = [
  { key: 'structure', tone: 'good' },
  { key: 'clarity', tone: 'good' },
  { key: 'persuasiveness', tone: 'good' },
  { key: 'financialCompleteness', tone: 'good' },
  { key: 'brand', tone: 'good' },
  { key: 'cta', tone: 'warn' },
  { key: 'risk', tone: 'good' },
  { key: 'readability', tone: 'good' },
];

export const MERGE_FIELDS: MergeFieldKey[] = [
  'recipient',
  'company',
  'investorType',
  'amount',
  'country',
  'project',
  'meetingLink',
  'advisor',
  'expiration',
];

export const SIGNATURE_STATES: SignatureState[] = [
  'draft',
  'sent',
  'viewed',
  'accepted',
  'rejected',
  'revisionRequested',
  'expired',
];

export const STYLE_OPTIONS = [
  'luxuryModern',
  'corporate',
  'minimal',
  'investor',
  'editorial',
] as const;

export const LANGUAGE_OPTIONS = ['en', 'tr', 'bilingual'] as const;

export const EXPORT_QUALITY_OPTIONS = ['standard', 'high', 'print'] as const;

export type ExportQuality = (typeof EXPORT_QUALITY_OPTIONS)[number];

export const DEFAULT_BRIEF: ProposalBrief = {
  proposalType: 'investor',
  audience: 'Institutional investors & family offices',
  language: 'en',
  style: 'luxuryModern',
  goal: 'Secure soft commitments for THE TEMPLE Residences',
  cta: 'Schedule a private investor briefing',
  topic: 'THE TEMPLE Residences — Investor Proposal',
  deliveryFormat: 'pdf',
  deadline: '2026-08-15',
  validity: '30 days',
};

export const DEFAULT_FINANCIALS: FinancialSettings = {
  currency: 'USD',
  amount: '$48,500,000',
  roi: '18.4%',
  irr: '16.2%',
  cashFlow: 'Stabilized Year 3',
  paymentSchedule: 'Quarterly distributions',
  scenario: 'Base case',
};

export const DEFAULT_SCORES: ProposalScores = {
  overall: 93,
};

export const PRB_PROJECTS: PrbProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    campaignName: 'THE TEMPLE Investor Proposal',
    featuredLabel: 'THE TEMPLE',
    coverUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1200&h=1600&q=85',
  },
  {
    id: '309h',
    name: '309 H ST NE',
    campaignName: '309 H ST Sales Proposal',
    featuredLabel: '309 H ST NE',
    coverUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&h=1600&q=85',
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    campaignName: 'UNILOFT Partnership Proposal',
    featuredLabel: 'UNILOFT',
    coverUrl:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1200&h=1600&q=85',
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    campaignName: 'Campus 3224 Construction Proposal',
    featuredLabel: 'CAMPUS 3224',
    coverUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&h=1600&q=85',
  },
];

const PAGE_THUMBS = [
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=360&h=480&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=360&h=480&q=80',
  'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=360&h=480&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=360&h=480&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=360&h=480&q=80',
  'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=360&h=480&q=80',
];

/** Investor proposal structure (~16–18 pages) */
export const INVESTOR_PAGE_KINDS: PageKind[] = [
  'cover',
  'toc',
  'execSummary',
  'projectOverview',
  'market',
  'location',
  'investmentOpportunity',
  'investmentStructure',
  'financialSummary',
  'roiIrr',
  'cashFlow',
  'risk',
  'timeline',
  'exit',
  'whyUs',
  'terms',
  'cta',
  'contact',
  'attachments',
];

/** Bank financing alternate structure */
export const BANK_PAGE_KINDS: PageKind[] = [
  'cover',
  'toc',
  'execSummary',
  'projectOverview',
  'investmentOpportunity',
  'financialSummary',
  'sourcesUses',
  'collateral',
  'repayment',
  'bankTerms',
  'risk',
  'timeline',
  'whyUs',
  'attachments',
  'contact',
];

/** Compact section tabs shown above the document preview */
export const SECTION_TABS: PageKind[] = [
  'cover',
  'toc',
  'projectOverview',
  'investmentOpportunity',
  'financialSummary',
  'whyUs',
  'timeline',
  'terms',
  'attachments',
];

/** Primary tabs kept visible; remainder live under “Daha Fazla” */
export const PRIMARY_SECTION_TABS: PageKind[] = [
  'cover',
  'toc',
  'projectOverview',
  'investmentOpportunity',
  'financialSummary',
];

export const MORE_SECTION_TABS: PageKind[] = SECTION_TABS.filter(
  (kind) => !PRIMARY_SECTION_TABS.includes(kind),
);

export const ROI_TABLE_ROWS = [
  { label: 'Equity multiple', value: '1.84x' },
  { label: 'Target ROI', value: '18.4%' },
  { label: 'Project IRR', value: '16.2%' },
  { label: 'Hold period', value: '5 years' },
  { label: 'Stabilized NOI', value: '$4.2M' },
] as const;

export const CASH_FLOW_ROWS = [
  { year: 'Y1', noi: '$2.1M', distribution: '$0.8M' },
  { year: 'Y2', noi: '$3.4M', distribution: '$1.6M' },
  { year: 'Y3', noi: '$4.2M', distribution: '$2.4M' },
  { year: 'Y4', noi: '$4.5M', distribution: '$2.6M' },
  { year: 'Y5', noi: '$4.8M', distribution: '$2.9M' },
] as const;

export const SOURCES_USES_ROWS = [
  { item: 'Senior debt', sources: '$28.0M', uses: '—' },
  { item: 'Preferred equity', sources: '$12.5M', uses: '—' },
  { item: 'Sponsor equity', sources: '$8.0M', uses: '—' },
  { item: 'Land & soft costs', sources: '—', uses: '$18.4M' },
  { item: 'Hard construction', sources: '—', uses: '$24.6M' },
  { item: 'Reserves & fees', sources: '—', uses: '$5.5M' },
] as const;

export function pagesForType(type: ProposalType): PageKind[] {
  if (type === 'bankFinancing') return BANK_PAGE_KINDS;
  return INVESTOR_PAGE_KINDS;
}

export function buildPages(type: ProposalType): PrbPage[] {
  return pagesForType(type).map((kind, index) => ({
    id: `pg-${index + 1}`,
    kind,
    thumbUrl: PAGE_THUMBS[index % PAGE_THUMBS.length]!,
    status: index < Math.max(8, Math.floor(pagesForType(type).length * 0.7)) ? 'ready' : 'draft',
  }));
}

export const DEFAULT_PAGES: PrbPage[] = buildPages('investor');

export function getProject(id: ProjectId): PrbProject {
  return PRB_PROJECTS.find((p) => p.id === id) ?? PRB_PROJECTS[0]!;
}

export function scoreTone(score: number): StatusChipTone {
  if (score >= 90) return 'success';
  if (score >= 75) return 'info';
  if (score >= 60) return 'warning';
  return 'danger';
}

export function reorderPages(pages: PrbPage[], fromId: string, toId: string): PrbPage[] {
  if (fromId === toId) return pages;
  const fromIndex = pages.findIndex((s) => s.id === fromId);
  const toIndex = pages.findIndex((s) => s.id === toId);
  if (fromIndex < 0 || toIndex < 0) return pages;
  const next = [...pages];
  const [moved] = next.splice(fromIndex, 1);
  if (!moved) return pages;
  next.splice(toIndex, 0, moved);
  return next;
}

export function ratioClass(ratio: DocumentRatio): string {
  return ratio === 'letter' ? 'is-letter' : 'is-a4';
}

export function documentRatioForFormat(format: DeliveryFormat): DocumentRatio {
  return format === 'pptx' ? 'letter' : 'a4';
}

export function readingMinutes(pageCount: number): number {
  return Math.max(4, Math.round(pageCount * 0.5));
}

import type { IhIconName } from '@/components/icons/ih-icons';

export const AS_HOME = '/workspaces/creative-studio';
export const ARCHITECTURAL_STUDIO_ROUTE = '/workspaces/creative-studio/architectural-studio';

export type FlowStepId = 'uploadPlan' | 'analyze' | 'model3d' | 'render' | 'video';

export type CenterTabId = 'planAnalysis' | 'model3d' | 'renderPreview' | 'videoPreview';

export type ViewMode3d = 'isometric' | 'plan' | 'tour';

export type RenderStyleId = 'modern' | 'minimal' | 'classic' | 'industrial';

export type OutputTypeId = 'image' | 'panorama' | 'video';

export type RailActionId =
  | 'home'
  | 'gallery'
  | 'layers'
  | 'workspace'
  | 'settings'
  | 'analytics'
  | 'chat'
  | 'help';

export type BottomActionKey =
  | 'addComponent'
  | 'wall'
  | 'door'
  | 'window'
  | 'stairs'
  | 'furniture'
  | 'material'
  | 'plant'
  | 'light'
  | 'camera'
  | 'note'
  | 'aiAssistant';

export type DetectedSpace = {
  id: string;
  label: string;
  areaM2: number;
  color: string;
};

export type ReferenceImage = {
  id: string;
  label: string;
  url: string;
};

export type UploadedFile = {
  id: string;
  name: string;
  sizeLabel: string;
  ext: 'PDF' | 'DWG' | 'PNG';
  icon: IhIconName;
};

export type QuickRender = {
  id: string;
  label: string;
  url: string;
};

export type AnalysisMetric = {
  id: 'totalArea' | 'netUsable' | 'roomCount' | 'estValue';
  value: string;
  icon: IhIconName;
};

export const FLOW_STEPS: {
  id: FlowStepId;
  titleKey: string;
  hintKey: string;
}[] = [
  { id: 'uploadPlan', titleKey: 'uploadPlan', hintKey: 'uploadPlan' },
  { id: 'analyze', titleKey: 'analyze', hintKey: 'analyze' },
  { id: 'model3d', titleKey: 'model3d', hintKey: 'model3d' },
  { id: 'render', titleKey: 'render', hintKey: 'render' },
  { id: 'video', titleKey: 'video', hintKey: 'video' },
];

export const CENTER_TABS: CenterTabId[] = [
  'planAnalysis',
  'model3d',
  'renderPreview',
  'videoPreview',
];

export const RENDER_STYLES: RenderStyleId[] = ['modern', 'minimal', 'classic', 'industrial'];

export const OUTPUT_TYPES: { id: OutputTypeId; icon: IhIconName }[] = [
  { id: 'image', icon: 'design' },
  { id: 'panorama', icon: 'projects' },
  { id: 'video', icon: 'meeting' },
];

export const RAIL_ACTIONS: { id: RailActionId; icon: IhIconName }[] = [
  { id: 'home', icon: 'home' },
  { id: 'gallery', icon: 'inventory' },
  { id: 'layers', icon: 'executive' },
  { id: 'workspace', icon: 'projects' },
  { id: 'settings', icon: 'settings' },
  { id: 'analytics', icon: 'barChart' },
  { id: 'chat', icon: 'sparkles' },
  { id: 'help', icon: 'alert' },
];

export const BOTTOM_ACTIONS: { key: BottomActionKey; icon: IhIconName }[] = [
  { key: 'addComponent', icon: 'plus' },
  { key: 'wall', icon: 'projects' },
  { key: 'door', icon: 'home' },
  { key: 'window', icon: 'design' },
  { key: 'stairs', icon: 'trendingUp' },
  { key: 'furniture', icon: 'inventory' },
  { key: 'material', icon: 'documents' },
  { key: 'plant', icon: 'activity' },
  { key: 'light', icon: 'sparkles' },
  { key: 'camera', icon: 'meeting' },
  { key: 'note', icon: 'documents' },
  { key: 'aiAssistant', icon: 'sparkles' },
];

export const DEMO_BRIEF =
  'Modern, premium ve yatırım odaklı bir konut projesi oluştur.';

export const BRIEF_MAX = 500;

export const DEMO_SPACES: DetectedSpace[] = [
  { id: 'salon', label: 'Salon', areaM2: 32.5, color: '#a8d4e8' },
  { id: 'mutfak', label: 'Mutfak', areaM2: 14.2, color: '#b8e0c8' },
  { id: 'yatak1', label: 'Yatak Odası 1', areaM2: 18.7, color: '#f0c4d4' },
  { id: 'yatak2', label: 'Yatak Odası 2', areaM2: 16.4, color: '#f5d4a8' },
  { id: 'suite', label: 'Ebeveyn Süiti', areaM2: 21.3, color: '#c8b8e0' },
  { id: 'banyo1', label: 'Banyo 1', areaM2: 6.2, color: '#b8d4f0' },
  { id: 'banyo2', label: 'Banyo 2', areaM2: 5.8, color: '#d4e8b8' },
  { id: 'wc', label: 'Misafir WC', areaM2: 2.4, color: '#e8d4b8' },
  { id: 'hol', label: 'Hol', areaM2: 8.1, color: '#d8d8e0' },
  { id: 'balkon', label: 'Balkon', areaM2: 7.5, color: '#c8e8d8' },
  { id: 'depo', label: 'Depo', areaM2: 3.2, color: '#e0d0c0' },
  { id: 'teras', label: 'Teras', areaM2: 6.1, color: '#c0d8e8' },
];

export const DEMO_REFERENCES: ReferenceImage[] = [
  {
    id: 'r1',
    label: 'Salon referans',
    url: 'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=240&h=180&q=80',
  },
  {
    id: 'r2',
    label: 'Mutfak referans',
    url: 'https://images.unsplash.com/photo-1556912173-46c336c7fd55?auto=format&fit=crop&w=240&h=180&q=80',
  },
  {
    id: 'r3',
    label: 'Cephe referans',
    url: 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=240&h=180&q=80',
  },
  {
    id: 'r4',
    label: 'Yatak odası',
    url: 'https://images.unsplash.com/photo-1616594039964-ae9021a400a0?auto=format&fit=crop&w=240&h=180&q=80',
  },
  {
    id: 'r5',
    label: 'Banyo',
    url: 'https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&w=240&h=180&q=80',
  },
  {
    id: 'r6',
    label: 'Teras',
    url: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=240&h=180&q=80',
  },
];

export const DEMO_FILES: UploadedFile[] = [
  {
    id: 'f1',
    name: 'The_Temple_Plan_v2.pdf',
    sizeLabel: '2.4 MB',
    ext: 'PDF',
    icon: 'documents',
  },
  {
    id: 'f2',
    name: 'Temple_Floor_A1.dwg',
    sizeLabel: '1.1 MB',
    ext: 'DWG',
    icon: 'projects',
  },
  {
    id: 'f3',
    name: 'Site_Context.png',
    sizeLabel: '860 KB',
    ext: 'PNG',
    icon: 'design',
  },
];

export const DEMO_RENDERS: QuickRender[] = [
  {
    id: 'q1',
    label: 'Salon',
    url: 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=200&h=140&q=80',
  },
  {
    id: 'q2',
    label: 'Cephe',
    url: 'https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=200&h=140&q=80',
  },
  {
    id: 'q3',
    label: 'Mutfak',
    url: 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?auto=format&fit=crop&w=200&h=140&q=80',
  },
];

export const DEMO_METRICS: AnalysisMetric[] = [
  { id: 'totalArea', value: '142.4 m²', icon: 'projects' },
  { id: 'netUsable', value: '118.6 m²', icon: 'home' },
  { id: 'roomCount', value: '12', icon: 'inventory' },
  { id: 'estValue', value: '$1,245,000', icon: 'trendingUp' },
];

/** Premium temple / CS project covers used across Image & Presentation builders. */
export const PREVIEW_3D_BY_VIEW: Record<ViewMode3d, string> = {
  isometric:
    'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&h=560&q=85',
  plan: 'https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=800&h=560&q=85',
  tour: 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&h=560&q=85',
};

/**
 * Soft translucent highlight regions over the floor-plan plate
 * (Salon, Mutfak, Yatak Odası, Banyo, Koridor) — viewBox 0 0 420 320.
 */
export const FLOOR_PLAN_HIGHLIGHTS: {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  color: string;
}[] = [
  { id: 'salon', label: 'Salon', x: 36, y: 36, w: 168, h: 118, color: 'rgba(7, 91, 117, 0.12)' },
  { id: 'mutfak', label: 'Mutfak', x: 204, y: 36, w: 96, h: 70, color: 'rgba(31, 122, 77, 0.1)' },
  { id: 'yatak1', label: 'Yatak Odası', x: 36, y: 154, w: 110, h: 100, color: 'rgba(117, 75, 107, 0.1)' },
  { id: 'banyo1', label: 'Banyo', x: 204, y: 154, w: 56, h: 58, color: 'rgba(39, 148, 173, 0.12)' },
  { id: 'hol', label: 'Koridor', x: 204, y: 106, w: 56, h: 48, color: 'rgba(113, 128, 135, 0.1)' },
];

export const PROJECTS = [
  { id: 'temple', name: 'THE TEMPLE Residences' },
  { id: '309h', name: '309 H ST NE' },
  { id: 'uniloft', name: 'UNILOFT DC' },
  { id: 'campus', name: 'The Campus 3224' },
] as const;

export const STYLE_THUMBS: Record<RenderStyleId, string> = {
  modern:
    'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=160&h=110&q=80',
  minimal:
    'https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=160&h=110&q=80',
  classic:
    'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=160&h=110&q=80',
  industrial:
    'https://images.unsplash.com/photo-1600607687644-c7171b42498f?auto=format&fit=crop&w=160&h=110&q=80',
};
